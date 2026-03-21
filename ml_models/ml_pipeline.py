"""
End-to-end ML pipeline for the probation system.
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files import File
from .trainers import RiskAssessmentTrainer, ProgramRecommenderTrainer
from .predictors import PredictionService

class MLPipeline:
    """Orchestrates the complete ML pipeline."""
    
    def __init__(self):
        self.trainer = RiskAssessmentTrainer()
        self.recommender_trainer = ProgramRecommenderTrainer()
    
    def run_risk_assessment_pipeline(self, dataset_path, model_name="Risk Assessment Model"):
        """Run complete risk assessment pipeline."""
        from .models import MLModel, TrainingJob
        
        print(f"Starting risk assessment pipeline for {dataset_path}")
        
        # Create training job
        job = TrainingJob.objects.create(
            ml_model=None,  # Will be updated after model creation
            job_id=f"risk_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            status='running',
            current_step='Loading dataset'
        )
        
        try:
            # Step 1: Load and prepare data
            job.current_step = 'Preparing data'
            job.save()
            
            # Train model
            result = self.trainer.train_risk_model(
                dataset_path,
                algorithm='random_forest',
                target_column='recidivism_risk'
            )
            
            # Step 2: Create ML model record
            job.current_step = 'Creating model record'
            job.save()
            
            # Save model files
            model_dir = os.path.join(settings.MEDIA_ROOT, 'ml_models', 
                                    datetime.now().strftime('%Y/%m/%d'))
            os.makedirs(model_dir, exist_ok=True)
            
            model_filename = f"{model_name.replace(' ', '_').lower()}_{job.job_id}.pkl"
            model_path = os.path.join(model_dir, model_filename)
            
            # Save model and preprocessing objects
            save_result = self.trainer.save_model(
                result['model_result'],
                model_path,
                scaler=result.get('scaler'),
                encoder=result.get('encoder')
            )
            
            # Step 3: Create MLModel instance
            ml_model = MLModel.objects.create(
                name=model_name,
                description=f"Risk assessment model trained on {os.path.basename(dataset_path)}",
                model_type='classification',
                algorithm='random_forest',
                purpose='Predict offender risk levels',
                training_dataset=None,  # Would link to Dataset model if available
                feature_columns=result.get('feature_names', []),
                target_column='recidivism_risk',
                hyperparameters=result['model_result'].get('parameters', {}),
                training_parameters={'algorithm': 'random_forest'},
                accuracy=result['metrics'].get('accuracy'),
                precision=result['metrics'].get('precision'),
                recall=result['metrics'].get('recall'),
                f1_score=result['metrics'].get('f1_score'),
                confusion_matrix=result['metrics'].get('confusion_matrix'),
                status='trained',
                trained_by=None,  # Would link to user
                training_time_seconds=result['model_result'].get('training_time'),
                version='1.0.0'
            )

            # Attach artifacts to FileFields (so predictors can load from storage reliably).
            try:
                with open(save_result["model_path"], "rb") as f:
                    ml_model.model_file.save(model_filename, File(f), save=False)
                if save_result.get("scaler_path"):
                    with open(save_result["scaler_path"], "rb") as f:
                        ml_model.scaler_file.save(
                            model_filename.replace(".pkl", "_scaler.pkl"), File(f), save=False
                        )
                if save_result.get("encoder_path"):
                    with open(save_result["encoder_path"], "rb") as f:
                        ml_model.encoder_file.save(
                            model_filename.replace(".pkl", "_encoder.pkl"), File(f), save=False
                        )
                ml_model.save()
            except Exception:
                # Don't fail the pipeline if file attachment fails; model record still exists.
                pass
            
            # Update job with model reference
            job.ml_model = ml_model
            job.metrics = result['metrics']
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.training_time_seconds = result['model_result'].get('training_time')
            job.save()
            
            print(f"Pipeline completed successfully. Model ID: {ml_model.id}")
            
            return {
                'success': True,
                'model_id': ml_model.id,
                'job_id': job.job_id,
                'metrics': result['metrics']
            }
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now()
            job.save()
            
            print(f"Pipeline failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'job_id': job.job_id
            }
    
    def run_program_recommendation_pipeline(self, dataset_path, model_name="Program Recommender"):
        """Run program recommendation pipeline."""
        from .models import MLModel, TrainingJob
        
        print(f"Starting program recommendation pipeline for {dataset_path}")
        
        # Create training job
        job = TrainingJob.objects.create(
            ml_model=None,
            job_id=f"recommend_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            status='running',
            current_step='Loading dataset'
        )
        
        try:
            # Train recommender
            result = self.recommender_trainer.train_recommender(dataset_path)
            
            # Create model directory
            model_dir = os.path.join(settings.MEDIA_ROOT, 'ml_models', 
                                    datetime.now().strftime('%Y/%m/%d'))
            os.makedirs(model_dir, exist_ok=True)
            
            # For now, create a simple model file
            model_filename = f"{model_name.replace(' ', '_').lower()}_{job.job_id}.pkl"
            model_path = os.path.join(model_dir, model_filename)
            
            # Save basic model info
            with open(model_path, 'wb') as f:
                import pickle
                pickle.dump({'type': 'recommender', 'data': result}, f)
            
            # Create MLModel instance
            ml_model = MLModel.objects.create(
                name=model_name,
                description="Program recommendation model",
                model_type='recommender',
                algorithm='matrix_factorization',
                purpose='Recommend rehabilitation programs',
                model_file=model_path,
                status='trained',
                trained_by=None,
                version='1.0.0'
            )
            
            # Update job
            job.ml_model = ml_model
            job.metrics = result.get('statistics', {})
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.save()
            
            return {
                'success': True,
                'model_id': ml_model.id,
                'job_id': job.job_id
            }
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now()
            job.save()
            
            return {
                'success': False,
                'error': str(e),
                'job_id': job.job_id
            }
    
    def batch_predict_risks(self, offender_ids, model_id=None):
        """Make batch predictions for multiple offenders."""
        from .models import MLModel, Offender
        from offenders.models import Assessment
        
        if model_id is None:
            # Get the latest risk assessment model
            model = MLModel.objects.filter(
                purpose__icontains='risk',
                status='deployed'
            ).order_by('-created_at').first()
        else:
            model = MLModel.objects.get(id=model_id)
        
        if not model:
            return {'success': False, 'error': 'No deployed risk model found'}
        
        predictions = []
        
        for offender_id in offender_ids:
            try:
                offender = Offender.objects.get(id=offender_id)
                
                # Get latest assessment for features
                assessment = Assessment.objects.filter(
                    offender=offender
                ).order_by('-assessment_date').first()
                
                if assessment:
                    # Convert assessment to features
                    features = {
                        'criminal_history': assessment.criminal_history,
                        'education_level': assessment.education_level,
                        'employment_status': assessment.employment_status,
                        'substance_abuse': int(assessment.substance_abuse),
                        'mental_health_issues': int(assessment.mental_health_issues),
                        'family_support': assessment.family_support,
                        'financial_stability': assessment.financial_stability
                    }
                    
                    # Make prediction
                    result = PredictionService.make_prediction(model, offender, features)
                    
                    if result['success']:
                        predictions.append({
                            'offender_id': offender_id,
                            'offender_name': offender.get_full_name(),
                            'risk_level': result['result'].get('risk_label', 'Unknown'),
                            'confidence': result['result'].get('confidence'),
                            'success': True
                        })
                    else:
                        predictions.append({
                            'offender_id': offender_id,
                            'success': False,
                            'error': result['error']
                        })
                else:
                    predictions.append({
                        'offender_id': offender_id,
                        'success': False,
                        'error': 'No assessment data found'
                    })
                    
            except Exception as e:
                predictions.append({
                    'offender_id': offender_id,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'model_used': model.name,
            'total_predictions': len(predictions),
            'successful_predictions': sum(1 for p in predictions if p['success']),
            'predictions': predictions
        }
    
    def monitor_model_performance(self, model_id, days_back=30):
        """Monitor model performance over time."""
        from .models import MLModel, Prediction
        
        model = MLModel.objects.get(id=model_id)
        
        # Get predictions from last N days
        cutoff_date = datetime.now() - timedelta(days=days_back)
        predictions = Prediction.objects.filter(
            ml_model=model,
            prediction_time__gte=cutoff_date,
            actual_value__isnull=False
        )
        
        if predictions.count() == 0:
            return {
                'success': False,
                'message': 'No ground truth data available for evaluation'
            }
        
        # Calculate performance metrics
        if model.model_type == 'classification':
            correct = sum(1 for p in predictions if p.is_correct)
            accuracy = correct / predictions.count() if predictions.count() > 0 else 0
            
            performance = {
                'total_predictions': predictions.count(),
                'correct_predictions': correct,
                'accuracy': accuracy,
                'time_period_days': days_back
            }
            
        elif model.model_type == 'regression':
            errors = []
            for pred in predictions:
                if pred.actual_value is not None and pred.predicted_value is not None:
                    errors.append(abs(pred.actual_value - pred.predicted_value))
            
            if errors:
                mae = np.mean(errors)
                rmse = np.sqrt(np.mean([e**2 for e in errors]))
                
                performance = {
                    'total_predictions': predictions.count(),
                    'mean_absolute_error': mae,
                    'root_mean_squared_error': rmse,
                    'time_period_days': days_back
                }
            else:
                performance = {'error': 'No valid prediction pairs found'}
        
        else:
            performance = {'error': 'Unsupported model type for monitoring'}
        
        return {
            'success': True,
            'model': model.name,
            'performance': performance,
            'monitoring_period': {
                'from': cutoff_date.strftime('%Y-%m-%d'),
                'to': datetime.now().strftime('%Y-%m-%d')
            }
        }
