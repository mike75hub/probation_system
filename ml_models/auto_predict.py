"""
Automatic prediction helpers.

These utilities are intentionally conservative: if a deployed model is available and
enough features can be derived from the offender/assessment context, a prediction is
made and recorded, and an aggregate numeric value is written back to
`Offender.ml_risk_score` when possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from django.db import transaction
from django.db.models import Q

from offenders.models import Assessment, Offender

from .models import MLModel
from .predictors import PredictionService


@dataclass(frozen=True)
class AutoPredictionOutcome:
    attempted: bool
    success: bool
    reason: str = ""
    ml_model_id: Optional[int] = None
    prediction_id: Optional[int] = None
    ml_risk_score: Optional[float] = None


def _best_deployed_model() -> Optional[MLModel]:
    """
    Pick the best deployed model for supervision risk signal.

    Preference order:
    - models whose name/purpose indicate risk or recidivism
    - higher accuracy when available
    - most recently created
    """

    deployed = MLModel.objects.filter(is_active=True, status=MLModel.Status.DEPLOYED).filter(
        Q(name__icontains="risk")
        | Q(purpose__icontains="risk")
        | Q(name__icontains="recidivism")
        | Q(purpose__icontains="recidivism")
    )
    deployed = deployed.exclude(model_file="").exclude(model_file__isnull=True)

    candidates = list(deployed.order_by("-accuracy", "-created_at")[:25])
    if candidates:
        for m in candidates:
            try:
                if m.model_file and m.model_file.storage.exists(m.model_file.name):
                    return m
            except Exception:
                continue

    # Fallback: any deployed model.
    fallback = (
        MLModel.objects.filter(is_active=True, status=MLModel.Status.DEPLOYED)
        .exclude(model_file="")
        .exclude(model_file__isnull=True)
        .order_by("-accuracy", "-created_at")[:25]
    )
    for m in fallback:
        try:
            if m.model_file and m.model_file.storage.exists(m.model_file.name):
                return m
        except Exception:
            continue
    return None


def _feature_dict(offender: Offender, assessment: Optional[Assessment]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    # Offender demographics / profile
    data["age"] = offender.age() if hasattr(offender, "age") else None
    data["gender"] = getattr(offender, "gender", None)
    data["nationality"] = getattr(offender, "nationality", None)
    data["county"] = getattr(offender, "county", None)
    data["sub_county"] = getattr(offender, "sub_county", None)
    data["risk_level"] = getattr(offender, "risk_level", None)
    data["is_active"] = 1 if getattr(offender, "is_active", False) else 0

    # Assessment-derived (best signal for many models)
    if assessment is not None:
        data.update(
            {
                "criminal_history": assessment.criminal_history,
                "education_level": assessment.education_level,
                "employment_status": assessment.employment_status,
                "employment_duration": assessment.employment_duration,
                "substance_abuse": 1 if assessment.substance_abuse else 0,
                "mental_health_issues": 1 if assessment.mental_health_issues else 0,
                "anger_issues": 1 if assessment.anger_issues else 0,
                "family_support": assessment.family_support,
                "peer_support": assessment.peer_support,
                "community_ties": assessment.community_ties,
                "financial_stability": assessment.financial_stability,
                "housing_stability": assessment.housing_stability,
                "overall_risk_score": assessment.overall_risk_score,
            }
        )

    return data


def _adapt_features_for_model(
    ml_model: MLModel, raw: Dict[str, Any]
) -> Tuple[Dict[str, Any], float]:
    """
    Return a features dict suitable for the model and a coverage ratio [0..1].

    If model has explicit `feature_columns`, restrict to those and fill missing with 0.
    """

    columns = list(ml_model.feature_columns or [])
    if not columns:
        # No declared columns: send what we have; coverage is trivially 1.0.
        return raw, 1.0

    present = 0
    features: Dict[str, Any] = {}
    dummy_sources = {"gender", "employment_status", "risk_level", "county", "sub_county", "nationality"}

    def coerce_numeric(v: Any) -> float:
        if v is None or v == "":
            return 0.0
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(v)
        except Exception:
            return 0.0

    def dummy_from_raw(col: str) -> Optional[float]:
        for src in dummy_sources:
            prefix = f"{src}_"
            if not col.startswith(prefix):
                continue
            wanted = col[len(prefix) :]
            current = raw.get(src)
            if current is None:
                return 0.0
            return 1.0 if str(current) == wanted else 0.0
        return None

    for c in columns:
        if c in raw and raw[c] is not None and raw[c] != "":
            present += 1
            features[c] = coerce_numeric(raw[c])
            continue

        dummy_val = dummy_from_raw(c)
        if dummy_val is not None:
            if raw.get(c.split("_", 1)[0]) is not None:
                present += 1
            features[c] = float(dummy_val)
            continue

        # Conservative default for missing numeric/categorical fields.
        features[c] = 0.0

    coverage = present / max(1, len(columns))
    return features, coverage


def _extract_numeric_risk_score(result: Dict[str, Any]) -> Optional[float]:
    """
    Normalize different predictor result shapes into a 0..1 numeric score.
    """

    if not result:
        return None

    # Recidivism predictor: probability of class 1.
    if "probability" in result and isinstance(result["probability"], (int, float)):
        p = float(result["probability"])
        if 0.0 <= p <= 1.0:
            return p

    # Risk predictor: probabilities for [low, medium, high]
    probs = result.get("probabilities")
    if isinstance(probs, list) and probs:
        try:
            high = float(probs[-1])
            if 0.0 <= high <= 1.0:
                return high
        except Exception:
            return None

    # Fallback: confidence
    conf = result.get("confidence")
    if isinstance(conf, (int, float)):
        c = float(conf)
        if 0.0 <= c <= 1.0:
            return c

    return None


def auto_predict_offender(
    *,
    offender: Offender,
    assessment: Optional[Assessment] = None,
    made_by=None,
    min_feature_coverage: float = 0.5,
) -> AutoPredictionOutcome:
    """
    Attempt a prediction for an offender and persist a numeric score to ml_risk_score.
    """

    ml_model = _best_deployed_model()
    if not ml_model:
        return AutoPredictionOutcome(attempted=False, success=False, reason="no_deployed_model")

    raw = _feature_dict(offender, assessment)
    features, coverage = _adapt_features_for_model(ml_model, raw)
    if coverage < min_feature_coverage:
        return AutoPredictionOutcome(
            attempted=False,
            success=False,
            reason=f"insufficient_feature_coverage:{coverage:.2f}",
            ml_model_id=ml_model.id,
        )

    with transaction.atomic():
        result = PredictionService.make_prediction(
            ml_model,
            offender=offender,
            features=features,
            made_by=made_by,
        )
        if not result.get("success"):
            return AutoPredictionOutcome(
                attempted=True,
                success=False,
                reason=result.get("error", "prediction_failed"),
                ml_model_id=ml_model.id,
            )

        numeric = _extract_numeric_risk_score(result.get("result") or {})
        if numeric is not None:
            offender.ml_risk_score = numeric
            offender.save(update_fields=["ml_risk_score"])

        prediction = result.get("prediction")
        return AutoPredictionOutcome(
            attempted=True,
            success=True,
            reason="ok",
            ml_model_id=ml_model.id,
            prediction_id=getattr(prediction, "id", None),
            ml_risk_score=numeric,
        )
