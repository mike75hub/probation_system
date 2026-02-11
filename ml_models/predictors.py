"""
Prediction utilities for ML models.
"""
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

class ModelPredictor:
    """Make predictions using trained ML models."""
    
    def __init__(self, model_path, scaler_path=None, encoder_path=None):
        """Initialize predictor with model and preprocessing objects."""
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.encoder_path = encoder_path
        
        # Load objects
        self.model = self._load_model()
        self.scaler = self._load_scaler() if scaler_path else None
        self.encoder = self._load_encoder() if encoder_path else None
    
    def _load_model(self):
        """Load trained model from file."""
        try:
            with open(self.model_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            raise Exception(f"Error loading model: {str(e)}")
    
    def _load_scaler(self):
        """Load scaler from file."""
        try:
            with open(self.scaler_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            raise Exception(f"Error loading scaler: {str(e)}")
    
    def _load_encoder(self):
        """Load encoder from file."""
        try:
            with open(self.encoder_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            raise Exception(f"Error loading encoder: {str(e)}")
    
    def predict(self, features, return_probabilities=False):
        """Make prediction for given features."""
        try:
            # Convert features to numpy array if needed
            if isinstance(features, (list, dict)):
                features = self._preprocess_features(features)
            
            # Apply preprocessing
            if self.scaler:
                features = self.scaler.transform(features)
            
            # Make prediction
            if return_probabilities and hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(features)
                prediction = self.model.predict(features)
                return prediction, probabilities
            else:
                prediction = self.model.predict(features)
                return prediction, None
        
        except Exception as e:
            raise Exception(f"Error making prediction: {str(e)}")
    
    def _preprocess_features(self, features):
        """Preprocess input features."""
        if isinstance(features, list):
            # Convert list to 2D array
            return np.array(features).reshape(1, -1)
        elif isinstance(features, dict):
            # Convert dict to DataFrame
            return pd.DataFrame([features])
        else:
            return features
    
    def batch_predict(self, features_list):
        """Make predictions for multiple instances."""
        predictions = []
        confidences = []
        
        for features in features_list:
            try:
                pred, probs = self.predict(features)
                predictions.append(pred[0] if isinstance(pred, np.ndarray) else pred)
                
                # Calculate confidence score
                if probs is not None:
                    confidence = np.max(probs[0])
                    confidences.append(float(confidence))
                else:
                    confidences.append(None)
            
            except Exception as e:
                predictions.append(None)
                confidences.append(None)
                print(f"Error predicting for features {features}: {e}")
        
        return predictions, confidences

class RiskPredictor(ModelPredictor):
    """Specialized predictor for risk assessment."""
    
    RISK_LEVELS = {
        0: 'Low Risk',
        1: 'Medium Risk',
        2: 'High Risk'
    }
    
    def predict_risk(self, offender_features):
        """Predict risk level for an offender."""
        prediction, probabilities = self.predict(offender_features, return_probabilities=True)
        
        if probabilities is not None:
            risk_level = int(prediction[0])
            confidence = float(np.max(probabilities[0]))
            
            return {
                'risk_level': risk_level,
                'risk_label': self.RISK_LEVELS.get(risk_level, 'Unknown'),
                'confidence': confidence,
                'probabilities': probabilities[0].tolist(),
                'prediction_time': datetime.now().isoformat()
            }
        else:
            return {
                'risk_level': int(prediction[0]),
                'risk_label': self.RISK_LEVELS.get(int(prediction[0]), 'Unknown'),
                'confidence': None,
                'prediction_time': datetime.now().isoformat()
            }
    
    def analyze_risk_factors(self, offender_features, top_n=5):
        """Analyze which features contribute most to the risk prediction."""
        # This is a simplified version
        # For tree-based models, you could use feature_importances_
        # For linear models, you could use coefficients
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            
            # Sort features by importance
            sorted_indices = np.argsort(importances)[::-1]
            
            risk_factors = []
            for i in range(min(top_n, len(sorted_indices))):
                idx = sorted_indices[i]
                risk_factors.append({
                    'feature_index': int(idx),
                    'importance': float(importances[idx]),
                    'value': offender_features.get(f'feature_{idx}', 'N/A')
                })
            
            return risk_factors
        
        return []

class RecidivismPredictor(ModelPredictor):
    """Specialized predictor for recidivism."""
    
    def predict_recidivism(self, offender_features, threshold=0.5):
        """Predict likelihood of recidivism."""
        prediction, probabilities = self.predict(offender_features, return_probabilities=True)
        
        if probabilities is not None:
            recidivism_prob = float(probabilities[0][1])  # Probability of class 1 (recidivism)
            will_recidivate = recidivism_prob >= threshold
            
            return {
                'will_recidivate': bool(will_recidivate),
                'probability': recidivism_prob,
                'confidence': float(np.max(probabilities[0])),
                'threshold': threshold,
                'prediction_time': datetime.now().isoformat()
            }
        else:
            return {
                'will_recidivate': bool(prediction[0]),
                'probability': None,
                'confidence': None,
                'threshold': threshold,
                'prediction_time': datetime.now().isoformat()
            }

class ProgramRecommenderPredictor(ModelPredictor):
    """Specialized predictor for program recommendations."""
    
    def recommend_programs(self, offender_features, top_k=5):
        """Recommend rehabilitation programs for an offender."""
        # This is a simplified version
        # In practice, this would use collaborative filtering or content-based filtering
        
        prediction, _ = self.predict(offender_features)
        
        # Mock recommendations based on prediction
        # In real implementation, this would query a program database
        
        programs = [
            {'id': 1, 'name': 'Vocational Training', 'match_score': 0.85},
            {'id': 2, 'name': 'Anger Management', 'match_score': 0.78},
            {'id': 3, 'name': 'Substance Abuse Counseling', 'match_score': 0.72},
            {'id': 4, 'name': 'Life Skills Training', 'match_score': 0.68},
            {'id': 5, 'name': 'Educational Support', 'match_score': 0.65}
        ]
        
        # Sort by match score
        programs_sorted = sorted(programs, key=lambda x: x['match_score'], reverse=True)
        
        return {
            'recommendations': programs_sorted[:top_k],
            'total_programs': len(programs),
            'prediction_time': datetime.now().isoformat()
        }

class PredictionService:
    """Service for managing predictions."""
    
    @staticmethod
    def get_predictor_for_model(ml_model):
        """Get appropriate predictor for ML model type."""
        if 'risk' in ml_model.name.lower() or 'risk' in ml_model.purpose.lower():
            return RiskPredictor(
                ml_model.model_file.path,
                ml_model.scaler_file.path if ml_model.scaler_file else None,
                ml_model.encoder_file.path if ml_model.encoder_file else None
            )
        elif 'recidivism' in ml_model.name.lower() or 'recidivism' in ml_model.purpose.lower():
            return RecidivismPredictor(
                ml_model.model_file.path,
                ml_model.scaler_file.path if ml_model.scaler_file else None,
                ml_model.encoder_file.path if ml_model.encoder_file else None
            )
        elif 'recommend' in ml_model.name.lower() or 'recommend' in ml_model.purpose.lower():
            return ProgramRecommenderPredictor(
                ml_model.model_file.path,
                ml_model.scaler_file.path if ml_model.scaler_file else None,
                ml_model.encoder_file.path if ml_model.encoder_file else None
            )
        else:
            return ModelPredictor(
                ml_model.model_file.path,
                ml_model.scaler_file.path if ml_model.scaler_file else None,
                ml_model.encoder_file.path if ml_model.encoder_file else None
            )
    
    @staticmethod
    def make_prediction(ml_model, offender, features):
        """Make prediction and save results."""
        from .models import Prediction
        
        try:
            # Get predictor
            predictor = PredictionService.get_predictor_for_model(ml_model)
            
            # Make prediction based on model type
            if isinstance(predictor, RiskPredictor):
                result = predictor.predict_risk(features)
                predicted_value = result.get('risk_level')
                predicted_class = result.get('risk_label')
                confidence = result.get('confidence')
                
            elif isinstance(predictor, RecidivismPredictor):
                result = predictor.predict_recidivism(features)
                predicted_value = result.get('probability')
                predicted_class = 'Will Recidivate' if result.get('will_recidivate') else 'Will Not Recidivate'
                confidence = result.get('confidence')
                
            elif isinstance(predictor, ProgramRecommenderPredictor):
                result = predictor.recommend_programs(features)
                predicted_value = None
                predicted_class = json.dumps(result.get('recommendations', []))
                confidence = None
                
            else:
                prediction, probabilities = predictor.predict(features, return_probabilities=True)
                predicted_value = float(prediction[0]) if isinstance(prediction, np.ndarray) else prediction
                predicted_class = str(predicted_value)
                confidence = float(np.max(probabilities[0])) if probabilities is not None else None
            
            # Save prediction
            prediction_record = Prediction.objects.create(
                ml_model=ml_model,
                offender=offender,
                input_features=features,
                prediction_result=result,
                prediction_confidence=confidence,
                predicted_value=predicted_value,
                predicted_class=predicted_class,
                made_by=offender.user if hasattr(offender, 'user') else None
            )
            
            return {
                'success': True,
                'prediction': prediction_record,
                'result': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }