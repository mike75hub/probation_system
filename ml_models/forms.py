"""
Forms for ml_models app.
"""
from django import forms
from django.core.validators import FileExtensionValidator
from .models import MLModel, TrainingJob, Prediction
from datasets.models import Dataset

class MLModelForm(forms.ModelForm):
    class Meta:
        model = MLModel
        fields = [
            'name', 'description', 'model_type', 'algorithm', 'purpose',
            'training_dataset', 'target_column', 'hyperparameters', 'notes'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'hyperparameters': forms.Textarea(attrs={'rows': 3, 'placeholder': 'JSON format: {"key": "value"}'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'purpose': forms.TextInput(attrs={'placeholder': 'e.g., Predict recidivism risk'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Show datasets that are available for use (exclude archived/error only)
        self.fields['training_dataset'].queryset = Dataset.objects.exclude(
            status__in=[Dataset.Status.ARCHIVED, Dataset.Status.ERROR]
        ).order_by('-upload_date')
        
        # Add help text
        self.fields['hyperparameters'].help_text = 'Enter hyperparameters in JSON format'
    
    def clean_hyperparameters(self):
        hyperparameters = self.cleaned_data.get('hyperparameters')
        if hyperparameters:
            try:
                import json
                if isinstance(hyperparameters, str):
                    json.loads(hyperparameters)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for hyperparameters")
        return hyperparameters

class TrainingJobForm(forms.ModelForm):
    class Meta:
        model = TrainingJob
        fields = ['ml_model', 'dataset', 'parameters']
        widgets = {
            'parameters': forms.Textarea(attrs={'rows': 3, 'placeholder': 'JSON format: {"key": "value"}'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Show datasets that are available for use (exclude archived/error only)
        self.fields['dataset'].queryset = Dataset.objects.exclude(
            status__in=[Dataset.Status.ARCHIVED, Dataset.Status.ERROR]
        ).order_by('-upload_date')
    
    def clean_parameters(self):
        parameters = self.cleaned_data.get('parameters')
        if parameters:
            try:
                import json
                if isinstance(parameters, str):
                    json.loads(parameters)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for parameters")
        return parameters

class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ['ml_model', 'offender', 'input_features']
        widgets = {
            'input_features': forms.Textarea(attrs={'rows': 4, 'placeholder': 'JSON format: {"feature1": value1, "feature2": value2}'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter active models
        self.fields['ml_model'].queryset = MLModel.objects.filter(
            is_active=True, 
            status__in=['trained', 'deployed']
        )
    
    def clean_input_features(self):
        input_features = self.cleaned_data.get('input_features')
        if input_features:
            try:
                import json
                if isinstance(input_features, str):
                    json.loads(input_features)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for input features")
        return input_features

class ModelTrainingForm(forms.Form):
    """Form for training a new model."""
    
    # Model information
    name = forms.CharField(
        max_length=200,
        help_text="Give your model a descriptive name"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Describe what this model will do"
    )
    
    # Data selection
    dataset = forms.ModelChoiceField(
        queryset=Dataset.objects.none(),
        help_text="Select the dataset to use for training"
    )
    
    # Algorithm selection
    ALGORITHM_CHOICES = [
        ('random_forest', 'Random Forest'),
        ('logistic_regression', 'Logistic Regression'),
        ('decision_tree', 'Decision Tree'),
        ('xgboost', 'XGBoost'),
        ('svm', 'Support Vector Machine'),
    ]
    
    algorithm = forms.ChoiceField(
        choices=ALGORITHM_CHOICES,
        initial='random_forest',
        help_text="Select the machine learning algorithm"
    )
    
    # Model type
    MODEL_TYPE_CHOICES = [
        ('classification', 'Classification'),
        ('regression', 'Regression'),
    ]
    
    model_type = forms.ChoiceField(
        choices=MODEL_TYPE_CHOICES,
        initial='classification',
        help_text="Select the type of problem"
    )
    
    # Target column
    target_column = forms.CharField(
        help_text="Enter the name of the target column in your dataset"
    )
    
    # Training parameters
    test_size = forms.FloatField(
        initial=0.2,
        min_value=0.1,
        max_value=0.5,
        help_text="Proportion of data to use for testing (0.1-0.5)"
    )
    
    random_state = forms.IntegerField(
        initial=42,
        help_text="Random seed for reproducibility"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['dataset'].queryset = Dataset.objects.exclude(
            status__in=[Dataset.Status.ARCHIVED, Dataset.Status.ERROR]
        ).order_by('-upload_date')

class SinglePredictionForm(forms.Form):
    """Form for making a single prediction."""
    
    ml_model = forms.ModelChoiceField(
        queryset=MLModel.objects.filter(is_active=True, status__in=['trained', 'deployed']),
        help_text="Select a trained or deployed model"
    )

class BatchPredictionForm(forms.Form):
    """Form for batch predictions."""
    
    ml_model = forms.ModelChoiceField(
        queryset=MLModel.objects.filter(is_active=True, status__in=['trained', 'deployed']),
        help_text="Select a trained or deployed model"
    )
    
    input_file = forms.FileField(
        help_text="Upload a CSV file with features for prediction",
        validators=[FileExtensionValidator(['csv'])]
    )
    
    def clean_input_file(self):
        file = self.cleaned_data.get('input_file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size exceeds 10MB limit")
            
            # Check file content
            import pandas as pd
            try:
                df = pd.read_csv(file)
                if df.empty:
                    raise forms.ValidationError("CSV file is empty")
            except Exception as e:
                raise forms.ValidationError(f"Error reading CSV file: {str(e)}")
        
        return file
