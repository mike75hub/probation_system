"""
Admin configuration for ml_models app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import MLModel, TrainingJob, Prediction

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'algorithm', 'model_type', 'status_badge', 
        'accuracy', 'version', 'created_at'
    ]
    list_filter = ['model_type', 'algorithm', 'status', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'purpose']
    readonly_fields = [
        'created_at', 'last_trained', 'deployed_at', 
        'training_time_seconds', 'model_size_kb'
    ]
    actions = ['deploy_models', 'retire_models']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'model_type', 'algorithm', 'purpose')
        }),
        ('Data Information', {
            'fields': ('training_dataset', 'feature_columns', 'target_column')
        }),
        ('Model Files', {
            'fields': ('model_file', 'scaler_file', 'encoder_file')
        }),
        ('Training Parameters', {
            'fields': ('hyperparameters', 'training_parameters')
        }),
        ('Performance Metrics', {
            'fields': (
                ('accuracy', 'precision', 'recall'),
                ('f1_score', 'mse', 'rmse'),
                ('r2_score', 'auc_roc'),
                'confusion_matrix', 'feature_importance'
            )
        }),
        ('Status & Metadata', {
            'fields': (
                'status', 'is_active', 'trained_by',
                ('created_at', 'last_trained', 'deployed_at'),
                'version', 'parent_model'
            )
        }),
        ('Additional Information', {
            'fields': ('training_time_seconds', 'model_size_kb', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'training': 'warning',
            'trained': 'info',
            'validating': 'primary',
            'deployed': 'success',
            'error': 'danger',
            'retired': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def deploy_models(self, request, queryset):
        updated = queryset.update(status='deployed', deployed_at=timezone.now())
        self.message_user(request, f"Deployed {updated} models")
    deploy_models.short_description = "Deploy selected models"
    
    def retire_models(self, request, queryset):
        updated = queryset.update(status='retired', is_active=False)
        self.message_user(request, f"Retired {updated} models")
    retire_models.short_description = "Retire selected models"

@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = [
        'job_id', 'ml_model', 'status_badge', 'progress_percentage', 
        'created_at', 'training_time_seconds'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['job_id', 'ml_model__name', 'error_message']
    readonly_fields = [
        'created_at', 'started_at', 'completed_at',
        'training_time_seconds', 'cpu_usage', 'memory_usage_mb'
    ]
    actions = ['retry_failed_jobs']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('ml_model', 'dataset', 'job_id', 'status')
        }),
        ('Progress Tracking', {
            'fields': ('progress_percentage', 'current_step')
        }),
        ('Parameters', {
            'fields': ('parameters',)
        }),
        ('Results', {
            'fields': ('metrics', 'error_message', 'output_log')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
        ('Resource Usage', {
            'fields': ('cpu_usage', 'memory_usage_mb', 'training_time_seconds'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'secondary',
            'running': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'warning'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def retry_failed_jobs(self, request, queryset):
        failed_jobs = queryset.filter(status='failed')
        count = 0
        for job in failed_jobs:
            job.status = 'pending'
            job.error_message = ''
            job.save()
            count += 1
        self.message_user(request, f"Retried {count} failed jobs")
    retry_failed_jobs.short_description = "Retry failed jobs"

@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = [
        'ml_model', 'offender', 'predicted_class', 
        'prediction_confidence', 'prediction_time', 'is_correct'
    ]
    list_filter = ['ml_model', 'prediction_time', 'is_correct']
    search_fields = [
        'ml_model__name', 'offender__user__first_name', 
        'offender__user__last_name', 'predicted_class'
    ]
    readonly_fields = ['prediction_time']
    date_hierarchy = 'prediction_time'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ml_model', 'offender', 'offender__user')