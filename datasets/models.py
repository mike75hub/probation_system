"""
Models for dataset management.
"""
import os
import pandas as pd
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from accounts.models import User

class DatasetSource(models.Model):
    """Source information for datasets."""
    
    class SourceType(models.TextChoices):
        INTERNAL = 'internal', _('Internal System')
        EXTERNAL = 'external', _('External Source')
        GOVERNMENT = 'government', _('Government Agency')
        NGO = 'ngo', _('NGO Partner')
        RESEARCH = 'research', _('Research Institution')
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Source Name')
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.INTERNAL,
        verbose_name=_('Source Type')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Contact Person')
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name=_('Contact Email')
    )
    reliability_score = models.IntegerField(
        default=5,
        verbose_name=_('Reliability Score (1-10)'),
        help_text=_('How reliable is this data source?')
    )
    
    class Meta:
        verbose_name = _('Dataset Source')
        verbose_name_plural = _('Dataset Sources')
    
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

class Dataset(models.Model):
    """Main dataset model for storing and managing datasets."""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        UPLOADED = 'uploaded', _('Uploaded')
        VALIDATING = 'validating', _('Validating')
        PROCESSING = 'processing', _('Processing')
        READY = 'ready', _('Ready')
        ERROR = 'error', _('Error')
        ARCHIVED = 'archived', _('Archived')
    
    class DatasetType(models.TextChoices):
        OFFENDER_PROFILE = 'offender_profile', _('Offender Profiles')
        RISK_ASSESSMENT = 'risk_assessment', _('Risk Assessment Data')
        RECIDIVISM = 'recidivism', _('Recidivism Data')
        PROGRAM_EFFECTIVENESS = 'program_effectiveness', _('Program Effectiveness')
        BEHAVIORAL = 'behavioral', _('Behavioral Data')
        DEMOGRAPHIC = 'demographic', _('Demographic Data')
        CUSTOM = 'custom', _('Custom Dataset')
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        verbose_name=_('Dataset Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    dataset_type = models.CharField(
        max_length=50,
        choices=DatasetType.choices,
        verbose_name=_('Dataset Type')
    )
    
    # Source Information
    source = models.ForeignKey(
        DatasetSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='datasets',
        verbose_name=_('Data Source')
    )
    internal_source = models.BooleanField(
        default=False,
        verbose_name=_('Internal Data Source'),
        help_text=_('Is this data from our internal systems?')
    )
    
    # File Information
    original_file = models.FileField(
        upload_to='datasets/uploaded/%Y/%m/%d/',
        validators=[FileExtensionValidator(['csv', 'xlsx', 'xls', 'json', 'parquet'])],
        verbose_name=_('Original File')
    )
    processed_file = models.FileField(
        upload_to='datasets/processed/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Processed File')
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name=_('File Size (bytes)')
    )
    file_format = models.CharField(
        max_length=20,
        verbose_name=_('File Format')
    )
    
    # Data Statistics
    row_count = models.IntegerField(
        default=0,
        verbose_name=_('Number of Rows')
    )
    column_count = models.IntegerField(
        default=0,
        verbose_name=_('Number of Columns')
    )
    column_names = models.JSONField(
        default=list,
        verbose_name=_('Column Names')
    )
    data_types = models.JSONField(
        default=dict,
        verbose_name=_('Data Types')
    )
    
    # Quality Metrics
    missing_values_count = models.JSONField(
        default=dict,
        verbose_name=_('Missing Values Count')
    )
    duplicate_rows = models.IntegerField(
        default=0,
        verbose_name=_('Duplicate Rows')
    )
    data_quality_score = models.FloatField(
        default=0.0,
        verbose_name=_('Data Quality Score (0-100)')
    )
    
    # Status and Metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status')
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_datasets',
        verbose_name=_('Uploaded By')
    )
    
    # Timestamps
    upload_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Upload Date')
    )
    last_modified = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Modified')
    )
    processing_started = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Processing Started')
    )
    processing_completed = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Processing Completed')
    )
    
    # Privacy and Compliance
    contains_pii = models.BooleanField(
        default=False,
        verbose_name=_('Contains PII')
    )
    is_encrypted = models.BooleanField(
        default=False,
        verbose_name=_('Is Encrypted')
    )
    retention_period = models.IntegerField(
        default=365,
        verbose_name=_('Retention Period (days)')
    )
    
    class Meta:
        verbose_name = _('Dataset')
        verbose_name_plural = _('Datasets')
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.name} ({self.get_dataset_type_display()})"
    
    def get_file_size_display(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'draft': 'secondary',
            'uploaded': 'info',
            'validating': 'warning',
            'processing': 'primary',
            'ready': 'success',
            'error': 'danger',
            'archived': 'dark'
        }
        return colors.get(self.status, 'secondary')
    
    def get_preview_data(self, rows=5):
        """Get preview of dataset data."""
        try:
            if self.processed_file and os.path.exists(self.processed_file.path):
                file_path = self.processed_file.path
            elif os.path.exists(self.original_file.path):
                file_path = self.original_file.path
            else:
                return []
            
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=rows)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path, nrows=rows)
            else:
                return []
            
            return df.to_dict('records')
        except Exception as e:
            print(f"Error getting preview: {e}")
            return []
    
    def analyze_data(self):
        """Perform data analysis and update metrics."""
        try:
            file_path = self.original_file.path
            if not os.path.exists(file_path):
                return False
            
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                return False
            
            # Update statistics
            self.row_count = len(df)
            self.column_count = len(df.columns)
            self.column_names = df.columns.tolist()
            self.data_types = df.dtypes.astype(str).to_dict()
            self.missing_values_count = df.isnull().sum().to_dict()
            self.duplicate_rows = df.duplicated().sum()
            
            # Calculate quality score
            total_cells = self.row_count * self.column_count
            missing_cells = sum(self.missing_values_count.values())
            quality = 1 - (missing_cells / total_cells) if total_cells > 0 else 0
            self.data_quality_score = round(quality * 100, 2)
            self.status = self.Status.READY
            
            self.save()
            return True
        except Exception as e:
            print(f"Error analyzing data: {e}")
            return False

class FeatureMap(models.Model):
    """Maps dataset columns to standard features for ML."""
    
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='feature_maps',
        verbose_name=_('Dataset')
    )
    source_column = models.CharField(
        max_length=100,
        verbose_name=_('Source Column Name')
    )
    mapped_feature = models.CharField(
        max_length=100,
        verbose_name=_('Mapped Feature Name')
    )
    feature_type = models.CharField(
        max_length=50,
        choices=[
            ('numerical', 'Numerical'),
            ('categorical', 'Categorical'),
            ('datetime', 'DateTime'),
            ('text', 'Text'),
            ('binary', 'Binary'),
            ('ordinal', 'Ordinal')
        ],
        verbose_name=_('Feature Type')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Feature Description')
    )
    is_target = models.BooleanField(
        default=False,
        verbose_name=_('Is Target Variable')
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name=_('Is Required')
    )
    transformation = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('standard_scaler', 'Standard Scaler'),
            ('minmax_scaler', 'Min-Max Scaler'),
            ('label_encoder', 'Label Encoder'),
            ('onehot_encoder', 'One-Hot Encoder'),
            ('log_transform', 'Log Transform'),
            ('none', 'None')
        ],
        default='none',
        verbose_name=_('Transformation')
    )
    
    class Meta:
        verbose_name = _('Feature Map')
        verbose_name_plural = _('Feature Maps')
        unique_together = ['dataset', 'source_column']
    
    def __str__(self):
        return f"{self.source_column} → {self.mapped_feature}"
