"""
Service helpers for offender management.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q

from .models import Case

User = get_user_model()


@dataclass(frozen=True)
class OfficerAssignmentResult:
    assigned: int
    skipped_already_assigned: int
    skipped_no_officers: int


def assign_cases_to_officers(
    *,
    cases: Iterable[Case],
    officers_qs=None,
    only_status: Optional[str] = Case.Status.ACTIVE,
    force: bool = False,
    dry_run: bool = False,
) -> OfficerAssignmentResult:
    """
    Assign probation officers to cases.

    Strategy: least-loaded (by active-case count), tie-break by officer id.
    """

    officers = list(
        (officers_qs or User.objects.filter(role=User.Role.OFFICER, is_active=True)).order_by(
            "id"
        )
    )
    if not officers:
        return OfficerAssignmentResult(assigned=0, skipped_already_assigned=0, skipped_no_officers=1)

    if hasattr(cases, "values_list"):
        case_ids = list(cases.values_list("id", flat=True))
    else:
        case_ids = [c.id for c in cases]

    cases_qs = Case.objects.filter(id__in=case_ids)
    if only_status:
        cases_qs = cases_qs.filter(status=only_status)
    if not force:
        cases_qs = cases_qs.filter(probation_officer__isnull=True)

    cases_list: List[Case] = list(cases_qs.select_related("probation_officer").order_by("id"))

    if not cases_list:
        return OfficerAssignmentResult(assigned=0, skipped_already_assigned=0, skipped_no_officers=0)

    caseloads = {o.id: 0 for o in officers}
    existing = (
        Case.objects.filter(probation_officer__in=officers)
        .filter(Q(status=Case.Status.ACTIVE) | Q(status__isnull=True))
        .values("probation_officer")
        .annotate(c=Count("id"))
    )
    for row in existing:
        caseloads[row["probation_officer"]] = row["c"]

    assigned = 0
    skipped_already_assigned = 0

    def pick_officer_id() -> int:
        return min(caseloads.items(), key=lambda kv: (kv[1], kv[0]))[0]

    with transaction.atomic():
        for case in cases_list:
            if case.probation_officer_id and not force:
                skipped_already_assigned += 1
                continue

            officer_id = pick_officer_id()
            if not dry_run:
                case.probation_officer_id = officer_id
                case.save(update_fields=["probation_officer"])
            caseloads[officer_id] += 1
            assigned += 1

        if dry_run:
            transaction.set_rollback(True)

    return OfficerAssignmentResult(
        assigned=assigned,
        skipped_already_assigned=skipped_already_assigned,
        skipped_no_officers=0,
    )
