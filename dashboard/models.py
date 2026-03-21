"""
Models for dashboard analytics and statistics.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum, F, ExpressionWrapper, FloatField
from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import DateTimeField

class DashboardMetric(models.Model):
    """Stores dashboard metrics for caching with improved performance."""
    
    METRIC_TYPES = [
        ('offender_count', 'Total Offenders'),
        ('active_cases', 'Active Cases'),
        ('high_risk', 'High Risk Offenders'),
        ('medium_risk', 'Medium Risk Offenders'),
        ('low_risk', 'Low Risk Offenders'),
        ('completed_programs', 'Completed Programs'),
        ('active_programs', 'Active Programs'),
        ('recidivism_rate', 'Recidivism Rate'),
        ('avg_risk_score', 'Average Risk Score'),
        ('officer_caseload', 'Officer Caseload'),
        ('pending_checkins', 'Pending Check-ins'),
        ('overdue_checkins', 'Overdue Check-ins'),
        ('compliance_rate', 'Compliance Rate'),
        ('monthly_admissions', 'Monthly Admissions'),
        ('success_rate', 'Program Success Rate'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES, unique=True)
    value = models.FloatField()
    label = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=20, default='primary')
    icon = models.CharField(max_length=50, default='bi-graph-up')
    change = models.FloatField(default=0, help_text="Percentage change from previous period")
    trend = models.CharField(max_length=10, default='stable', 
                           choices=[('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')])
    
    # Time tracking with improved caching
    calculated_at = models.DateTimeField(auto_now=True)
    valid_until = models.DateTimeField()
    period = models.CharField(max_length=20, default='realtime',
                            choices=[('realtime', 'Real-time'), ('daily', 'Daily'), 
                                    ('weekly', 'Weekly'), ('monthly', 'Monthly')])
    
    # For comparison with previous period
    previous_value = models.FloatField(null=True, blank=True)
    comparison_period = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name = _('Dashboard Metric')
        verbose_name_plural = _('Dashboard Metrics')
        ordering = ['metric_type']
        indexes = [
            models.Index(fields=['metric_type', 'calculated_at']),
            models.Index(fields=['valid_until']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value}"
    
    def is_valid(self):
        """Check if metric is still valid."""
        return timezone.now() < self.valid_until
    
    def get_cache_key(self):
        """Get cache key for this metric."""
        return f"dashboard_metric_{self.metric_type}"
    
    def save(self, *args, **kwargs):
        # Update cache when saving
        super().save(*args, **kwargs)
        cache.set(self.get_cache_key(), self.value, 3600)  # Cache for 1 hour
    
    @classmethod
    def get_or_calculate(cls, metric_type, force_recalculate=False):
        """Get metric from cache or calculate it."""
        cache_key = f"dashboard_metric_{metric_type}"
        
        # Try cache first
        if not force_recalculate:
            metric = cls.objects.filter(
                metric_type=metric_type, 
                valid_until__gt=timezone.now()
            ).first()
            if metric:
                return metric.value
            
            # Try Django cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
        
        # Calculate fresh
        calculator_map = {
            'offender_count': cls.calculate_offender_count,
            'active_cases': cls.calculate_active_cases,
            'high_risk': cls.calculate_high_risk,
            'medium_risk': cls.calculate_medium_risk,
            'low_risk': cls.calculate_low_risk,
            'completed_programs': cls.calculate_completed_programs,
            'active_programs': cls.calculate_active_programs,
            'recidivism_rate': cls.calculate_recidivism_rate,
            'avg_risk_score': cls.calculate_avg_risk_score,
            'officer_caseload': cls.calculate_officer_caseload,
            'pending_checkins': cls.calculate_pending_checkins,
            'overdue_checkins': cls.calculate_overdue_checkins,
            'compliance_rate': cls.calculate_compliance_rate,
            'monthly_admissions': cls.calculate_monthly_admissions,
            'success_rate': cls.calculate_success_rate,
        }
        
        calculator = calculator_map.get(metric_type)
        if calculator:
            value = calculator()
            cls.update_metric(metric_type, value)
            cache.set(cache_key, value, 3600)
            return value
        
        return 0

    @classmethod
    def calculate_all_metrics(cls, force_recalculate=False):
        """Calculate all metrics and return a dict of values."""
        results = {}
        for metric_type, _ in cls.METRIC_TYPES:
            results[metric_type] = cls.get_or_calculate(
                metric_type,
                force_recalculate=force_recalculate
            )
        return results
    
    @staticmethod
    def calculate_offender_count():
        """Calculate total active offenders."""
        try:
            from offenders.models import Offender
            return Offender.objects.filter(is_active=True).count()
        except:
            return 0
    
    @staticmethod
    def calculate_active_cases():
        """Calculate active cases."""
        try:
            from offenders.models import Case
            return Case.objects.filter(status='active').count()
        except:
            return 0
    
    @staticmethod
    def calculate_high_risk():
        """Calculate high risk offenders."""
        try:
            from offenders.models import Offender
            return Offender.objects.filter(risk_level='high', is_active=True).count()
        except:
            return 0
    
    @staticmethod
    def calculate_medium_risk():
        """Calculate medium risk offenders."""
        try:
            from offenders.models import Offender
            return Offender.objects.filter(risk_level='medium', is_active=True).count()
        except:
            return 0
    
    @staticmethod
    def calculate_low_risk():
        """Calculate low risk offenders."""
        try:
            from offenders.models import Offender
            return Offender.objects.filter(risk_level='low', is_active=True).count()
        except:
            return 0
    
    @staticmethod
    def calculate_completed_programs():
        """Calculate completed programs."""
        try:
            from programs.models import Enrollment
            return Enrollment.objects.filter(status='completed').count()
        except:
            return 0
    
    @staticmethod
    def calculate_active_programs():
        """Calculate active program enrollments."""
        try:
            from programs.models import Enrollment
            return Enrollment.objects.filter(status='active').count()
        except:
            return 0
    
    @staticmethod
    def calculate_recidivism_rate():
        """Calculate recidivism rate."""
        try:
            from datasets.models import Dataset, Prediction
            # Get recidivism predictions
            predictions = Prediction.objects.filter(
                model__model_type='recidivism',
                predicted_value=True
            )
            if predictions.exists():
                total = predictions.count()
                # This is a simplified version - you'd need actual recidivism data
                return round((predictions.filter(confidence__gt=0.7).count() / total) * 100, 1)
        except:
            pass
        return 15.0  # Default fallback
    
    @staticmethod
    def calculate_avg_risk_score():
        """Calculate average risk score from recent assessments."""
        try:
            from offenders.models import Assessment
            assessments = Assessment.objects.filter(
                overall_risk_score__isnull=False,
                date__gte=timezone.now() - timedelta(days=90)  # Last 3 months
            )
            if assessments.exists():
                avg_score = assessments.aggregate(Avg('overall_risk_score'))['overall_risk_score__avg']
                return round(avg_score, 1)
        except:
            pass
        return 0.0
    
    @staticmethod
    def calculate_officer_caseload():
        """Calculate average officer caseload."""
        try:
            from accounts.models import User
            from offenders.models import Case
            officers = User.objects.filter(role='officer', is_active=True)
            if officers.exists():
                total_cases = Case.objects.filter(
                    probation_officer__in=officers, 
                    status='active'
                ).count()
                return round(total_cases / officers.count(), 1)
        except:
            pass
        return 0.0
    
    @staticmethod
    def calculate_pending_checkins():
        """Calculate pending check-ins for today."""
        try:
            from monitoring.models import CheckIn
            now = timezone.now()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return CheckIn.objects.filter(
                scheduled_date__gte=start,
                scheduled_date__lt=end,
                status='scheduled'
            ).count()
        except:
            return 0
    
    @staticmethod
    def calculate_overdue_checkins():
        """Calculate overdue check-ins."""
        try:
            from monitoring.models import CheckIn
            now = timezone.now()
            return CheckIn.objects.filter(
                scheduled_date__lt=now,
                status='scheduled'
            ).count()
        except:
            return 0
    
    @staticmethod
    def calculate_compliance_rate():
        """Calculate overall compliance rate."""
        try:
            from monitoring.models import CheckIn
            total_checkins = CheckIn.objects.count()
            if total_checkins > 0:
                one_hour_after_scheduled = ExpressionWrapper(
                    F("scheduled_date") + timedelta(hours=1),
                    output_field=DateTimeField(),
                )
                completed_on_time = CheckIn.objects.filter(
                    status='completed',
                    actual_date__isnull=False,
                    actual_date__lte=one_hour_after_scheduled,
                ).count()
                return round((completed_on_time / total_checkins) * 100, 1)
        except:
            pass
        return 85.0  # Default fallback
    
    @staticmethod
    def calculate_monthly_admissions():
        """Calculate monthly offender admissions."""
        try:
            from offenders.models import Offender
            current_month = timezone.now().replace(day=1)
            return Offender.objects.filter(
                date_created__gte=current_month,
                is_active=True
            ).count()
        except:
            return 0
    
    @staticmethod
    def calculate_success_rate():
        """Calculate program success rate."""
        try:
            from programs.models import Enrollment
            completed_programs = Enrollment.objects.filter(status='completed')
            if completed_programs.exists():
                successful = completed_programs.filter(
                    completion_grade__in=['excellent', 'good', 'satisfactory']
                ).count()
                return round((successful / completed_programs.count()) * 100, 1)
        except:
            pass
        return 75.0  # Default fallback
    
    @classmethod
    def update_metric(cls, metric_type, value, period='realtime'):
        """Update or create a metric with trend analysis."""
        now = timezone.now()
        metric, created = cls.objects.get_or_create(
            metric_type=metric_type,
            defaults={
                'value': value,
                'valid_until': now + timedelta(hours=1),
                'period': period,
                'previous_value': value,  # Same as current for new metrics
                'comparison_period': 'initial'
            }
        )
        
        if not created:
            # Calculate trend
            if metric.previous_value and metric.previous_value > 0:
                change = ((value - metric.previous_value) / metric.previous_value) * 100
                metric.change = round(change, 1)
                metric.trend = 'up' if change > 0 else 'down' if change < 0 else 'stable'
            
            metric.value = value
            metric.previous_value = metric.value  # Store current as previous for next time
            metric.valid_until = now + timedelta(hours=1)
            metric.calculated_at = now
            metric.period = period
            metric.save()

class DashboardWidget(models.Model):
    """Customizable dashboard widgets with improved configuration."""
    
    WIDGET_TYPES = [
        ('stats', 'Statistics Card'),
        ('chart', 'Chart'),
        ('table', 'Data Table'),
        ('list', 'List View'),
        ('progress', 'Progress Bar'),
        ('map', 'Map'),
        ('calendar', 'Calendar'),
        ('gauge', 'Gauge'),
    ]
    
    CHART_TYPES = [
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('pie', 'Pie Chart'),
        ('doughnut', 'Doughnut Chart'),
        ('radar', 'Radar Chart'),
        ('scatter', 'Scatter Plot'),
        ('polar', 'Polar Area'),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Widget Name'))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_('Widget Slug'))
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES, verbose_name=_('Widget Type'))
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, blank=True, verbose_name=_('Chart Type'))
    
    # Data configuration
    DATA_SOURCE_CHOICES = [
        ('metric', 'Dashboard Metric'),
        ('model', 'Database Model'),
        ('api', 'External API'),
        ('custom', 'Custom Query'),
        ('function', 'Python Function'),
    ]
    
    data_source = models.CharField(max_length=100, choices=DATA_SOURCE_CHOICES, default='metric', verbose_name=_('Data Source'))
    
    metric_source = models.CharField(max_length=100, blank=True, verbose_name=_('Metric Source'))
    model_name = models.CharField(max_length=100, blank=True, verbose_name=_('Model Name'))
    api_endpoint = models.URLField(blank=True, verbose_name=_('API Endpoint'))
    custom_query = models.TextField(blank=True, verbose_name=_('Custom Query'))
    
    # Display configuration
    title = models.CharField(max_length=200, blank=True, verbose_name=_('Display Title'))
    subtitle = models.CharField(max_length=200, blank=True, verbose_name=_('Subtitle'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    display_options = models.JSONField(default=dict, verbose_name=_('Display Options'))
    
    # Position and sizing with responsive support
    column = models.IntegerField(default=0, verbose_name=_('Column Position'))
    row = models.IntegerField(default=0, verbose_name=_('Row Position'))
    width_sm = models.IntegerField(default=12, verbose_name=_('Width (Small screens)'))
    width_md = models.IntegerField(default=6, verbose_name=_('Width (Medium screens)'))
    width_lg = models.IntegerField(default=4, verbose_name=_('Width (Large screens)'))
    height = models.IntegerField(default=300, verbose_name=_('Height (px)'))
    
    # Visibility and permissions - Using TextField instead of ArrayField for SQLite compatibility
    roles = models.TextField(
        default='',
        verbose_name=_('Visible to Roles'),
        help_text=_('Comma-separated list of roles')
    )
    is_default = models.BooleanField(default=False, verbose_name=_('Default Widget'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    order = models.IntegerField(default=0, verbose_name=_('Display Order'))
    
    # Refresh and caching
    refresh_interval = models.IntegerField(default=300, verbose_name=_('Refresh Interval (seconds)'))
    cache_duration = models.IntegerField(default=300, verbose_name=_('Cache Duration (seconds)'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard Widget')
        verbose_name_plural = _('Dashboard Widgets')
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['widget_type', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_roles_list(self):
        """Convert roles string to list."""
        if self.roles:
            return [role.strip() for role in self.roles.split(',') if role.strip()]
        return []
    
    def get_widget_config(self, user=None):
        """Get widget configuration for frontend."""
        config = {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'type': self.widget_type,
            'chart_type': self.chart_type,
            'data_source': self.data_source,
            'title': self.title or self.name,
            'subtitle': self.subtitle,
            'description': self.description,
            'display_options': {
                'colors': self.display_options.get('colors', ['#4e73df', '#1cc88a', '#36b9cc']),
                'show_legend': self.display_options.get('show_legend', True),
                'show_grid': self.display_options.get('show_grid', True),
                'animation': self.display_options.get('animation', True),
                **self.display_options
            },
            'position': {
                'column': self.column,
                'row': self.row,
                'width_sm': self.width_sm,
                'width_md': self.width_md,
                'width_lg': self.width_lg,
                'height': self.height
            },
            'refresh_interval': self.refresh_interval,
            'is_active': self.is_active,
            'is_default': self.is_default
        }
        
        # Add data based on source
        if self.data_source == 'metric' and self.metric_source:
            config['data'] = DashboardMetric.get_or_calculate(self.metric_source)
        elif self.data_source == 'model' and self.model_name:
            config['data'] = self.get_model_data()
        
        return config
    
    def get_model_data(self):
        """Get data from specified model."""
        # This would be implemented based on your models
        # For now, return sample data
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'datasets': [{
                'label': self.name,
                'data': [65, 59, 80, 81, 56],
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
            }]
        }
    
    def is_visible_to_user(self, user):
        """Check if widget is visible to user."""
        roles_list = self.get_roles_list()
        if not roles_list:
            return True
        
        user_role = user.role if hasattr(user, 'role') else 'user'
        return user_role in roles_list

class DashboardLayout(models.Model):
    """User dashboard layout preferences with versioning."""
    
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='dashboard_layout')
    layout_config = models.JSONField(default=dict, verbose_name=_('Layout Configuration'))
    widget_order = models.JSONField(default=list, verbose_name=_('Widget Order'))
    
    # Grid configuration
    columns = models.IntegerField(default=12, verbose_name=_('Grid Columns'))
    row_height = models.IntegerField(default=100, verbose_name=_('Row Height (px)'))
    margin = models.IntegerField(default=10, verbose_name=_('Grid Margin'))
    
    # Widgets
    widgets = models.ManyToManyField('DashboardWidget', through='DashboardWidgetPreference', 
                                    related_name='layouts')
    
    # Settings
    theme = models.CharField(max_length=20, default='light', 
                           choices=[('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')])
    refresh_interval = models.IntegerField(default=300, verbose_name=_('Refresh Interval (seconds)'))
    show_animations = models.BooleanField(default=True, verbose_name=_('Show Animations'))
    compact_mode = models.BooleanField(default=False, verbose_name=_('Compact Mode'))
    
    # Versioning
    version = models.IntegerField(default=1, verbose_name=_('Layout Version'))
    previous_layout = models.JSONField(null=True, blank=True, verbose_name=_('Previous Layout'))
    
    updated_at = models.DateTimeField(auto_now=True)
    last_reset = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Reset'))
    
    class Meta:
        verbose_name = _('Dashboard Layout')
        verbose_name_plural = _('Dashboard Layouts')
    
    def __str__(self):
        return f"{self.user.username}'s Dashboard Layout (v{self.version})"
    
    def save(self, *args, **kwargs):
        # Store previous layout before updating
        if self.pk:
            existing = DashboardLayout.objects.get(pk=self.pk)
            self.previous_layout = existing.layout_config
        
        super().save(*args, **kwargs)
    
    def get_active_widgets(self):
        """Get active widgets for this layout."""
        return self.widgetpreferences.filter(
            widget__is_active=True,
            is_visible=True
        ).select_related('widget').order_by('order')
    
    def reset_to_default(self, role=None):
        """Reset layout to default for user role."""
        if not role:
            role = self.user.role if hasattr(self.user, 'role') else 'user'
        
        default_layout = self.get_default_layout(role)
        self.layout_config = default_layout['layout']
        self.widget_order = default_layout['widgets']
        self.version += 1
        self.last_reset = timezone.now()
        self.save()
        
        # Clear widget preferences and set defaults
        self.widgetpreferences.all().delete()
        
        default_widgets = DashboardWidget.objects.filter(
            is_default=True,
            is_active=True
        )
        
        for i, widget in enumerate(default_widgets):
            DashboardWidgetPreference.objects.create(
                layout=self,
                widget=widget,
                is_visible=True,
                order=i,
                settings={}
            )
    
    @classmethod
    def get_default_layout(cls, role):
        """Get default layout configuration for a role."""
        defaults = {
            'admin': {
                'layout': {
                    'columns': 12,
                    'rowHeight': 100,
                    'margin': [10, 10],
                    'containerPadding': [10, 10],
                },
                'widgets': [
                    {'i': 'stats_overview', 'x': 0, 'y': 0, 'w': 12, 'h': 2, 'minW': 4, 'minH': 2},
                    {'i': 'risk_distribution', 'x': 0, 'y': 2, 'w': 6, 'h': 4},
                    {'i': 'compliance_trend', 'x': 6, 'y': 2, 'w': 6, 'h': 4},
                    {'i': 'recent_activity', 'x': 0, 'y': 6, 'w': 12, 'h': 4},
                    {'i': 'system_metrics', 'x': 0, 'y': 10, 'w': 12, 'h': 3},
                ]
            },
            'officer': {
                'layout': {
                    'columns': 12,
                    'rowHeight': 100,
                    'margin': [10, 10],
                },
                'widgets': [
                    {'i': 'my_cases', 'x': 0, 'y': 0, 'w': 4, 'h': 3},
                    {'i': 'pending_tasks', 'x': 4, 'y': 0, 'w': 4, 'h': 3},
                    {'i': 'high_risk_alert', 'x': 8, 'y': 0, 'w': 4, 'h': 3},
                    {'i': 'offender_progress', 'x': 0, 'y': 3, 'w': 12, 'h': 5},
                    {'i': 'checkin_schedule', 'x': 0, 'y': 8, 'w': 12, 'h': 4},
                ]
            },
            'offender': {
                'layout': {
                    'columns': 12,
                    'rowHeight': 100,
                },
                'widgets': [
                    {'i': 'my_progress', 'x': 0, 'y': 0, 'w': 6, 'h': 4},
                    {'i': 'upcoming_checkins', 'x': 6, 'y': 0, 'w': 6, 'h': 4},
                    {'i': 'program_status', 'x': 0, 'y': 4, 'w': 12, 'h': 4},
                    {'i': 'compliance_score', 'x': 0, 'y': 8, 'w': 6, 'h': 3},
                    {'i': 'rewards', 'x': 6, 'y': 8, 'w': 6, 'h': 3},
                ]
            }
        }
        return defaults.get(role, defaults['admin'])

class DashboardWidgetPreference(models.Model):
    """User preferences for specific widgets."""
    
    layout = models.ForeignKey(DashboardLayout, on_delete=models.CASCADE, 
                             related_name='widgetpreferences')
    widget = models.ForeignKey(DashboardWidget, on_delete=models.CASCADE,
                             related_name='preferences')
    
    # Display settings
    is_visible = models.BooleanField(default=True, verbose_name=_('Visible'))
    order = models.IntegerField(default=0, verbose_name=_('Order'))
    settings = models.JSONField(default=dict, verbose_name=_('Widget Settings'))
    
    # Customizations
    custom_title = models.CharField(max_length=200, blank=True, verbose_name=_('Custom Title'))
    custom_size = models.JSONField(default=dict, verbose_name=_('Custom Size'))
    filters = models.JSONField(default=dict, verbose_name=_('Filters'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Widget Preference')
        verbose_name_plural = _('Widget Preferences')
        unique_together = ['layout', 'widget']
        ordering = ['order']
    
    def __str__(self):
        return f"{self.layout.user.username} - {self.widget.name}"

class ActivityLog(models.Model):
    """Enhanced activity logging with categorization and aggregation."""
    
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('session_timeout', 'Session Timeout'),
        ('password_change', 'Password Change'),
        ('profile_update', 'Profile Update'),
        ('create', 'Create Record'),
        ('update', 'Update Record'),
        ('delete', 'Delete Record'),
        ('view', 'View Record'),
        ('download', 'Download File'),
        ('upload', 'Upload File'),
        ('export', 'Export Data'),
        ('import', 'Import Data'),
        ('train', 'Model Training'),
        ('predict', 'Make Prediction'),
        ('evaluate', 'Model Evaluation'),
        ('schedule', 'Schedule Task'),
        ('approve', 'Approve Request'),
        ('reject', 'Reject Request'),
        ('assign', 'Assign Task'),
        ('complete', 'Complete Task'),
        ('system', 'System Action'),
    ]
    
    MODULE_TYPES = [
        ('dashboard', 'Dashboard'),
        ('offenders', 'Offenders Management'),
        ('cases', 'Case Management'),
        ('assessments', 'Risk Assessments'),
        ('datasets', 'Data Management'),
        ('ml_models', 'Machine Learning'),
        ('monitoring', 'Monitoring & Compliance'),
        ('programs', 'Rehabilitation Programs'),
        ('reports', 'Reporting & Analytics'),
        ('accounts', 'User Accounts'),
        ('system', 'System Administration'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Information'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, 
                           related_name='activity_logs', verbose_name=_('User'))
    action = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name=_('Action'))
    module = models.CharField(max_length=20, choices=MODULE_TYPES, verbose_name=_('Module'))
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='info', 
                              verbose_name=_('Severity'))
    
    # Target object reference (generic foreign key approach)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Details
    description = models.TextField(verbose_name=_('Description'))
    details = models.JSONField(default=dict, verbose_name=_('Details'))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP Address'))
    user_agent = models.TextField(blank=True, verbose_name=_('User Agent'))
    session_key = models.CharField(max_length=40, blank=True, verbose_name=_('Session Key'))
    
    # Location (if available)
    location = models.CharField(max_length=255, blank=True, verbose_name=_('Location'))
    coordinates = models.JSONField(null=True, blank=True, verbose_name=_('Coordinates'))
    
    # Performance metrics
    duration = models.FloatField(null=True, blank=True, verbose_name=_('Duration (seconds)'))
    memory_usage = models.IntegerField(null=True, blank=True, verbose_name=_('Memory Usage (KB)'))
    
    # Status
    is_success = models.BooleanField(default=True, verbose_name=_('Success'))
    error_message = models.TextField(blank=True, verbose_name=_('Error Message'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    timestamp = models.DateTimeField(default=timezone.now, verbose_name=_('Timestamp'))
    
    class Meta:
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['module', 'action']),
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'System'
        return f"{username} - {self.get_action_display()} - {self.get_module_display()}"
    
    @classmethod
    def log_activity(cls, user=None, action='view', module='dashboard', 
                    description='', details=None, severity='info',
                    content_object=None, request=None, duration=None,
                    memory_usage=None, is_success=True, error_message=''):
        """Enhanced helper method to log activities."""
        if details is None:
            details = {}
        
        log_data = {
            'user': user,
            'action': action,
            'module': module,
            'severity': severity,
            'description': description,
            'details': details,
            'duration': duration,
            'memory_usage': memory_usage,
            'is_success': is_success,
            'error_message': error_message,
            'timestamp': timezone.now(),
        }
        
        # Add request info if available
        if request:
            log_data.update({
                'ip_address': cls.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'session_key': request.session.session_key if request.session else '',
            })
        
        # Add content object reference if provided
        if content_object:
            from django.contrib.contenttypes.models import ContentType
            log_data['content_type'] = ContentType.objects.get_for_model(content_object)
            log_data['object_id'] = content_object.pk
        
        log_entry = cls.objects.create(**log_data)
        
        # Cleanup old logs (keep last 10,000 entries per user if user specified)
        if user:
            cls.cleanup_user_logs(user)
        
        return log_entry
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def cleanup_user_logs(cls, user, keep_count=10000):
        """Cleanup old logs for a user."""
        user_logs = cls.objects.filter(user=user).order_by('-created_at')
        if user_logs.count() > keep_count:
            ids_to_delete = user_logs.values_list('id', flat=True)[keep_count:]
            cls.objects.filter(id__in=list(ids_to_delete)).delete()

class Notification(models.Model):
    """Enhanced notification system with priority and categorization."""
    
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('alert', 'Alert'),
        ('reminder', 'Reminder'),
        ('announcement', 'Announcement'),
        ('system', 'System'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CATEGORIES = [
        ('system', 'System Notification'),
        ('monitoring', 'Monitoring Alert'),
        ('compliance', 'Compliance Issue'),
        ('schedule', 'Schedule Reminder'),
        ('risk', 'Risk Alert'),
        ('program', 'Program Update'),
        ('report', 'Report Ready'),
        ('training', 'Model Training'),
        ('prediction', 'Prediction Result'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    message = models.TextField(verbose_name=_('Message'))
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    category = models.CharField(max_length=20, choices=CATEGORIES, default='general')
    
    # Action
    action_url = models.CharField(max_length=500, blank=True, verbose_name=_('Action URL'))
    action_text = models.CharField(max_length=100, blank=True, verbose_name=_('Action Text'))
    action_data = models.JSONField(default=dict, verbose_name=_('Action Data'))
    
    # Status
    is_read = models.BooleanField(default=False, verbose_name=_('Read'))
    is_archived = models.BooleanField(default=False, verbose_name=_('Archived'))
    is_dismissed = models.BooleanField(default=False, verbose_name=_('Dismissed'))
    
    # Expiry and scheduling
    valid_from = models.DateTimeField(default=timezone.now, verbose_name=_('Valid From'))
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name=_('Valid Until'))
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name=_('Scheduled For'))
    
    # Metadata
    source = models.CharField(max_length=100, blank=True, verbose_name=_('Source'))
    source_id = models.CharField(max_length=100, blank=True, verbose_name=_('Source ID'))
    metadata = models.JSONField(default=dict, verbose_name=_('Metadata'))
    
    # Delivery tracking
    delivery_method = models.CharField(max_length=20, default='in_app',
                                     choices=[('in_app', 'In App'), ('email', 'Email'), 
                                             ('sms', 'SMS'), ('push', 'Push'), ('all', 'All')])
    email_sent = models.BooleanField(default=False, verbose_name=_('Email Sent'))
    push_sent = models.BooleanField(default=False, verbose_name=_('Push Sent'))
    sms_sent = models.BooleanField(default=False, verbose_name=_('SMS Sent'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Read At'))
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Archived At'))
    dismissed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Dismissed At'))
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['category', 'priority']),
            models.Index(fields=['valid_until', 'is_dismissed']),
        ]
    
    def __str__(self):
        return f"[{self.priority.upper()}] {self.title} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Set default valid_until if not set
        if not self.valid_until:
            self.valid_until = self.created_at + timedelta(days=30)
        
        super().save(*args, **kwargs)
    
    def mark_as_read(self, commit=True):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            if commit:
                self.save()
    
    def mark_as_dismissed(self, commit=True):
        """Mark notification as dismissed."""
        if not self.is_dismissed:
            self.is_dismissed = True
            self.dismissed_at = timezone.now()
            if commit:
                self.save()
    
    def archive(self, commit=True):
        """Archive notification."""
        if not self.is_archived:
            self.is_archived = True
            self.archived_at = timezone.now()
            if commit:
                self.save()
    
    def is_valid(self):
        """Check if notification is still valid."""
        now = timezone.now()
        if self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        return not self.is_dismissed
    
    @classmethod
    def create_notification(cls, user, title, message, notification_type='info', 
                           priority='medium', category='general', 
                           action_url='', action_text='', action_data=None,
                           source='', source_id='', metadata=None, 
                           delivery_method='in_app', valid_from=None, valid_until=None,
                           scheduled_for=None):
        """Create a new notification with enhanced options."""
        if action_data is None:
            action_data = {}
        if metadata is None:
            metadata = {}
        
        if valid_from is None:
            valid_from = timezone.now()
        
        notification = cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            category=category,
            action_url=action_url,
            action_text=action_text,
            action_data=action_data,
            source=source,
            source_id=source_id,
            metadata=metadata,
            delivery_method=delivery_method,
            valid_from=valid_from,
            valid_until=valid_until,
            scheduled_for=scheduled_for
        )
        
        # Log the notification creation
        ActivityLog.log_activity(
            user=user,
            action='create',
            module='dashboard',
            description=f'Created notification: {title}',
            details={
                'notification_id': notification.id,
                'type': notification_type,
                'priority': priority,
                'category': category
            }
        )
        
        return notification
    
    @classmethod
    def get_unread_count(cls, user):
        """Get count of unread notifications for user."""
        return cls.objects.filter(
            user=user,
            is_read=False,
            is_dismissed=False,
            valid_until__gte=timezone.now(),
            valid_from__lte=timezone.now()
        ).count()
    
    @classmethod
    def get_recent_notifications(cls, user, limit=10, include_read=False):
        """Get recent notifications for user."""
        queryset = cls.objects.filter(
            user=user,
            is_dismissed=False,
            valid_until__gte=timezone.now(),
            valid_from__lte=timezone.now()
        )
        
        if not include_read:
            queryset = queryset.filter(is_read=False)
        
        return queryset.order_by('-priority', '-created_at')[:limit]

# Analytics models - Comment out if you get errors
class DashboardAnalytics(models.Model):
    """Track dashboard usage and performance analytics."""
    
    date = models.DateField(unique=True, verbose_name=_('Date'))
    
    # Usage metrics
    total_visits = models.IntegerField(default=0, verbose_name=_('Total Visits'))
    unique_users = models.IntegerField(default=0, verbose_name=_('Unique Users'))
    average_session_duration = models.FloatField(default=0, verbose_name=_('Avg Session Duration'))
    
    # Widget usage
    most_viewed_widget = models.CharField(max_length=100, blank=True, verbose_name=_('Most Viewed Widget'))
    widget_interactions = models.IntegerField(default=0, verbose_name=_('Widget Interactions'))
    
    # Performance
    avg_load_time = models.FloatField(default=0, verbose_name=_('Average Load Time (ms)'))
    api_calls = models.IntegerField(default=0, verbose_name=_('API Calls'))
    cache_hit_rate = models.FloatField(default=0, verbose_name=_('Cache Hit Rate'))
    
    # User engagement
    active_users = models.IntegerField(default=0, verbose_name=_('Active Users'))
    returning_users = models.IntegerField(default=0, verbose_name=_('Returning Users'))
    
    # Error tracking
    errors_count = models.IntegerField(default=0, verbose_name=_('Errors Count'))
    most_common_error = models.CharField(max_length=200, blank=True, verbose_name=_('Most Common Error'))
    
    # Mobile usage
    mobile_visits = models.IntegerField(default=0, verbose_name=_('Mobile Visits'))
    desktop_visits = models.IntegerField(default=0, verbose_name=_('Desktop Visits'))
    
    details = models.JSONField(default=dict, verbose_name=_('Detailed Analytics'))
    
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Dashboard Analytics')
        verbose_name_plural = _('Dashboard Analytics')
        ordering = ['-date']
    
    def __str__(self):
        return f"Dashboard Analytics - {self.date}"
