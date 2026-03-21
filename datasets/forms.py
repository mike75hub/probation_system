"""
Forms for datasets app.
"""
from django import forms
from django.core.validators import FileExtensionValidator
from .models import Dataset, DatasetSource, FeatureMap
from .validators import DatasetValidator

class DatasetSourceForm(forms.ModelForm):
    class Meta:
        model = DatasetSource
        fields = ['name', 'source_type', 'description', 
                 'contact_person', 'contact_email', 'reliability_score']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'reliability_score': forms.NumberInput(attrs={'min': 1, 'max': 10, 'step': 1})
        }

class DatasetUploadForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'description', 'dataset_type', 'source', 'original_file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the dataset content and purpose'}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter a descriptive name for this dataset'})
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    def clean_original_file(self):
        file = self.cleaned_data.get('original_file')
        
        if file:
            # Validate file extension
            DatasetValidator.validate_file_extension(file)
            
            # Validate file size (max 100MB)
            DatasetValidator.validate_file_size(file, max_size_mb=100)
            
            # Get file format
            ext = file.name.split('.')[-1].lower()
            if ext == 'csv':
                # `InMemoryUploadedFile` doesn't have `temporary_file_path()`. Validate from the
                # uploaded file object and ensure we reset the read pointer afterwards.
                try:
                    if hasattr(file, 'seek'):
                        file.seek(0)
                    DatasetValidator.validate_csv_structure(file)
                finally:
                    if hasattr(file, 'seek'):
                        file.seek(0)
        
        return file
    
    def save(self, commit=True):
        dataset = super().save(commit=False)
        
        if self.user:
            dataset.uploaded_by = self.user
        
        # Set file metadata
        if dataset.original_file:
            dataset.file_size = dataset.original_file.size
            dataset.file_format = dataset.original_file.name.split('.')[-1].lower()
            if dataset.status == Dataset.Status.DRAFT:
                dataset.status = Dataset.Status.UPLOADED
        
        if commit:
            dataset.save()
        return dataset

class DatasetUpdateForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'description', 'dataset_type', 'status', 'contains_pii', 'retention_period']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'retention_period': forms.NumberInput(attrs={'min': 1, 'max': 3650})
        }

class FeatureMapForm(forms.ModelForm):
    class Meta:
        model = FeatureMap
        fields = ['source_column', 'mapped_feature', 'feature_type', 
                 'description', 'is_target', 'is_required', 'transformation']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'source_column': forms.TextInput(attrs={'placeholder': 'Original column name'}),
            'mapped_feature': forms.TextInput(attrs={'placeholder': 'Standard feature name'})
        }

class DatasetAnalysisForm(forms.Form):
    """Form for analyzing dataset."""
    analyze_missing_values = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Check for missing values in the dataset"
    )
    check_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Identify duplicate rows"
    )
    validate_data_types = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Validate data types of columns"
    )
    
class DatasetPreviewForm(forms.Form):
    """Form for previewing dataset."""
    rows_to_preview = forms.IntegerField(
        initial=10,
        min_value=1,
        max_value=100,
        help_text="Number of rows to preview (1-100)"
    )
    include_header = forms.BooleanField(
        initial=True,
        help_text="Include column headers in preview"
    )
