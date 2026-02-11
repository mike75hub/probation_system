"""
Admin configuration for datasets app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Dataset, DatasetSource, FeatureMap

@admin.register(DatasetSource)
class DatasetSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'contact_person', 'reliability_score']
    list_filter = ['source_type']
    search_fields = ['name', 'contact_person', 'contact_email']
    ordering = ['name']

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'dataset_type', 'status_badge', 'row_count', 
        'column_count', 'uploaded_by', 'upload_date'
    ]
    list_filter = ['dataset_type', 'status', 'upload_date', 'internal_source']
    search_fields = ['name', 'description', 'uploaded_by__username']
    readonly_fields = [
        'file_size', 'file_format', 'row_count', 'column_count',
        'column_names', 'data_types', 'missing_values_count',
        'duplicate_rows', 'data_quality_score', 'upload_date',
        'last_modified'
    ]
    actions = ['analyze_datasets', 'mark_as_ready']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'dataset_type', 'source')
        }),
        ('File Information', {
            'fields': ('original_file', 'processed_file', 'file_size', 'file_format')
        }),
        ('Data Statistics', {
            'fields': ('row_count', 'column_count', 'column_names', 'data_types')
        }),
        ('Quality Metrics', {
            'fields': ('missing_values_count', 'duplicate_rows', 'data_quality_score')
        }),
        ('Status & Metadata', {
            'fields': ('status', 'uploaded_by', 'upload_date', 'last_modified')
        }),
        ('Privacy & Compliance', {
            'fields': ('contains_pii', 'is_encrypted', 'retention_period')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'uploaded': 'blue',
            'validating': 'yellow',
            'processing': 'orange',
            'ready': 'green',
            'error': 'red',
            'archived': 'dark'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def analyze_datasets(self, request, queryset):
        for dataset in queryset:
            try:
                dataset.analyze_data()
                self.message_user(request, f"Analyzed dataset: {dataset.name}")
            except Exception as e:
                self.message_user(request, f"Error analyzing {dataset.name}: {str(e)}", level='ERROR')
    analyze_datasets.short_description = "Analyze selected datasets"
    
    def mark_as_ready(self, request, queryset):
        updated = queryset.update(status='ready')
        self.message_user(request, f"Marked {updated} datasets as ready")
    mark_as_ready.short_description = "Mark datasets as ready"

@admin.register(FeatureMap)
class FeatureMapAdmin(admin.ModelAdmin):
    list_display = ['dataset', 'source_column', 'mapped_feature', 'feature_type', 'is_target', 'is_required']  # Added 'is_required' here
    list_filter = ['feature_type', 'is_target', 'is_required']
    search_fields = ['source_column', 'mapped_feature', 'dataset__name']
    list_editable = ['is_target', 'is_required']  # Now 'is_required' is also in list_display
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('dataset')