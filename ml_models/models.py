"""
Models for ML model management.
"""
import os
import pickle
import json
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from accounts.models import User
from datasets.models import Dataset

class MLModel(models.Model):
    """Main model for storing trained ML models."""
    
    class ModelType(models.TextChoices):
        CLASSIFICATION = 'classification', _('Classification')
        REGRESSION = 'regression', _('Regression')
        CLUSTERING = 'clustering', _('Clustering')
        RECOMMENDER = 'recommender', _('Recommender System')
        ANOMALY_DETECTION = 'anomaly_detection', _('Anomaly Detection')
    
    class Algorithm(models.TextChoices):
        LOGISTIC_REGRESSION = 'logistic_regression', _('Logistic Regression')
        RANDOM_FOREST = 'random_forest', _('Random Forest')
        DECISION_TREE = 'decision_tree', _('Decision Tree')
        SVM = 'svm', _('Support Vector Machine')
        XGBOOST = 'xgboost', _('XGBoost')
        LIGHTGBM = 'lightgbm', _('LightGBM')
        CATBOOST = 'catboost', _('CatBoost')
        NEURAL_NETWORK = 'neural_network', _('Neural Network')
        KMEANS = 'kmeans', _('K-Means')
        DBSCAN = 'dbscan', _('DBSCAN')
    
    class Status(models.TextChoices):
        TRAINING = 'training', _('Training')
        TRAINED = 'trained', _('Trained')
        VALIDATING = 'validating', _('Validating')
        DEPLOYED = 'deployed', _('Deployed')
        ERROR = 'error', _('Error')
        RETIRED = 'retired', _('Retired')
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        verbose_name=_('Model Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    model_type = models.CharField(
        max_length=50,
        choices=ModelType.choices,
        verbose_name=_('Model Type')
    )
    algorithm = models.CharField(
        max_length=50,
        choices=Algorithm.choices,
        verbose_name=_('Algorithm')
    )
    purpose = models.CharField(
        max_length=200,
        verbose_name=_('Model Purpose'),
        help_text=_('What problem does this model solve?')
    )
    
    # Data Information
    training_dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        null=True,
        related_name='trained_models',
        verbose_name=_('Training Dataset')
    )
    feature_columns = models.JSONField(
        default=list,
        verbose_name=_('Feature Columns')
    )
    target_column = models.CharField(
        max_length=100,
        verbose_name=_('Target Column')
    )
    
    # Model Files
    model_file = models.FileField(
        upload_to='ml_models/trained/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Model File')
    )
    scaler_file = models.FileField(
        upload_to='ml_models/scalers/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Scaler File')
    )
    encoder_file = models.FileField(
        upload_to='ml_models/encoders/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Encoder File')
    )
    
    # Training Parameters
    hyperparameters = models.JSONField(
        default=dict,
        verbose_name=_('Hyperparameters')
    )
    training_parameters = models.JSONField(
        default=dict,
        verbose_name=_('Training Parameters')
    )
    
    # Performance Metrics
    accuracy = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Accuracy')
    )
    precision = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Precision')
    )
    recall = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Recall')
    )
    f1_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('F1 Score')
    )
    mse = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Mean Squared Error')
    )
    rmse = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Root Mean Squared Error')
    )
    r2_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('R² Score')
    )
    auc_roc = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('AUC-ROC Score')
    )
    confusion_matrix = models.JSONField(
        default=dict,
        verbose_name=_('Confusion Matrix')
    )
    feature_importance = models.JSONField(
        default=dict,
        verbose_name=_('Feature Importance')
    )
    
    # Status and Metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRAINING,
        verbose_name=_('Status')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active Model')
    )
    trained_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='trained_ml_models',
        verbose_name=_('Trained By')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    last_trained = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Trained')
    )
    deployed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deployed At')
    )
    
    # Versioning
    version = models.CharField(
        max_length=20,
        default='1.0.0',
        verbose_name=_('Version')
    )
    parent_model = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_models',
        verbose_name=_('Parent Model')
    )
    
    # Additional Info
    training_time_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Training Time (seconds)')
    )
    model_size_kb = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Model Size (KB)')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('ML Model')
        verbose_name_plural = _('ML Models')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.algorithm})"
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'training': 'warning',
            'trained': 'info',
            'validating': 'primary',
            'deployed': 'success',
            'error': 'danger',
            'retired': 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def get_model_file_path(self):
        """Get absolute path to model file."""
        if self.model_file:
            return self.model_file.path
        return None
    
    def load_model(self):
        """Load the trained model from file."""
        if not self.model_file:
            return None
        
        try:
            with open(self.model_file.path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    
    def get_performance_summary(self):
        """Get a summary of model performance."""
        summary = {
            'algorithm': self.get_algorithm_display(),
            'status': self.get_status_display(),
            'version': self.version,
            'trained_at': self.last_trained.strftime('%Y-%m-%d %H:%M')
        }
        
        if self.model_type == 'classification':
            summary.update({
                'accuracy': self.accuracy,
                'precision': self.precision,
                'recall': self.recall,
                'f1_score': self.f1_score,
                'auc_roc': self.auc_roc
            })
        elif self.model_type == 'regression':
            summary.update({
                'mse': self.mse,
                'rmse': self.rmse,
                'r2_score': self.r2_score
            })
        
        return summary

class TrainingJob(models.Model):
    """Tracks ML model training jobs."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RUNNING = 'running', _('Running')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    ml_model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name='training_jobs',
        verbose_name=_('ML Model')
    )
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Dataset')
    )
    job_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Job ID')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Status')
    )
    parameters = models.JSONField(
        default=dict,
        verbose_name=_('Training Parameters')
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        verbose_name=_('Progress Percentage')
    )
    current_step = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Current Step')
    )
    
    # Results
    metrics = models.JSONField(
        default=dict,
        verbose_name=_('Training Metrics')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    output_log = models.TextField(
        blank=True,
        verbose_name=_('Output Log')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Started At')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At')
    )
    
    # Resource usage
    cpu_usage = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('CPU Usage (%)')
    )
    memory_usage_mb = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Memory Usage (MB)')
    )
    training_time_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Training Time (seconds)')
    )
    
    class Meta:
        verbose_name = _('Training Job')
        verbose_name_plural = _('Training Jobs')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Training Job: {self.job_id} - {self.ml_model.name}"
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'pending': 'secondary',
            'running': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'warning'
        }
        return colors.get(self.status, 'secondary')

class Prediction(models.Model):
    """Stores predictions made by ML models."""
    
    ml_model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name='predictions',
        verbose_name=_('ML Model')
    )
    offender = models.ForeignKey(
        'offenders.Offender',
        on_delete=models.SET_NULL,
        null=True,
        related_name='ml_predictions',
        verbose_name=_('Offender')
    )
    
    # Input features
    input_features = models.JSONField(
        default=dict,
        verbose_name=_('Input Features')
    )
    
    # Prediction results
    prediction_result = models.JSONField(
        default=dict,
        verbose_name=_('Prediction Result')
    )
    prediction_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Prediction Confidence')
    )
    predicted_class = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Predicted Class')
    )
    predicted_value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Predicted Value')
    )
    
    # Metadata
    made_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Made By')
    )
    prediction_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Prediction Time')
    )
    batch_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Batch ID')
    )
    
    # Ground truth (if available)
    actual_value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Actual Value')
    )
    actual_class = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Actual Class')
    )
    is_correct = models.BooleanField(
        null=True,
        blank=True,
        verbose_name=_('Prediction Correct')
    )
    
    class Meta:
        verbose_name = _('Prediction')
        verbose_name_plural = _('Predictions')
        ordering = ['-prediction_time']
    
    def __str__(self):
        return f"Prediction by {self.ml_model.name} for {self.offender}"
    
    def get_prediction_summary(self):
        """Get a summary of the prediction."""
        summary = {
            'model': self.ml_model.name,
            'offender': str(self.offender),
            'timestamp': self.prediction_time.strftime('%Y-%m-%d %H:%M'),
            'confidence': self.prediction_confidence
        }
        
        if self.ml_model.model_type == 'classification':
            summary.update({
                'predicted_class': self.predicted_class,
                'actual_class': self.actual_class,
                'is_correct': self.is_correct
            })
        elif self.ml_model.model_type == 'regression':
            summary.update({
                'predicted_value': self.predicted_value,
                'actual_value': self.actual_value
            })
        
        return summary