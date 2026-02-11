"""
Models for reports app.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings  # Add this import
from django.utils import timezone
from offenders.models import Offender, Case
from monitoring.models import CheckIn, GPSMonitoring, DrugTest, Alert

# Remove: from django.contrib.auth.models import User
# Use settings.AUTH_USER_MODEL instead

class ReportType(models.Model):
    """Types of reports available in the system."""
    
    class ReportCategory(models.TextChoices):
        COMPLIANCE = 'compliance', _('Compliance')
        PERFORMANCE = 'performance', _('Performance')
        OPERATIONAL = 'operational', _('Operational')
        ANALYTICAL = 'analytical', _('Analytical')
        STATISTICAL = 'statistical', _('Statistical')
        CUSTOM = 'custom', _('Custom')
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Report Type Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    category = models.CharField(
        max_length=50,
        choices=ReportCategory.choices,
        default=ReportCategory.COMPLIANCE,
        verbose_name=_('Category')
    )
    
    # Frequency options
    is_daily = models.BooleanField(
        default=False,
        verbose_name=_('Available Daily')
    )
    is_weekly = models.BooleanField(
        default=False,
        verbose_name=_('Available Weekly')
    )
    is_monthly = models.BooleanField(
        default=True,
        verbose_name=_('Available Monthly')
    )
    is_quarterly = models.BooleanField(
        default=False,
        verbose_name=_('Available Quarterly')
    )
    is_yearly = models.BooleanField(
        default=True,
        verbose_name=_('Available Yearly')
    )
    
    # Access control
    allowed_roles = models.JSONField(
        default=list,
        verbose_name=_('Allowed User Roles'),
        help_text=_('List of user roles allowed to generate this report')
    )
    
    # Configuration
    template_path = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Template Path'),
        help_text=_('Path to report template file')
    )
    parameters_schema = models.JSONField(
        default=dict,
        verbose_name=_('Parameters Schema'),
        help_text=_('JSON schema for report parameters')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Report Type')
        verbose_name_plural = _('Report Types')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_allowed_roles_display(self):
        """Return readable allowed roles."""
        role_mapping = {
            'admin': 'Administrator',
            'officer': 'Probation Officer',
            'judiciary': 'Judiciary Staff',
            'ngo': 'NGO Staff'
        }
        return [role_mapping.get(role, role) for role in self.allowed_roles]

class ReportSchedule(models.Model):
    """Schedule for automatic report generation."""
    
    class Frequency(models.TextChoices):
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
        QUARTERLY = 'quarterly', _('Quarterly')
        YEARLY = 'yearly', _('Yearly')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        PAUSED = 'paused', _('Paused')
        COMPLETED = 'completed', _('Completed')
        ERROR = 'error', _('Error')
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Schedule Name')
    )
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name=_('Report Type')
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        verbose_name=_('Frequency')
    )
    
    # Scheduling details
    start_date = models.DateField(
        verbose_name=_('Start Date')
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('End Date'),
        help_text=_('Leave empty for indefinite schedule')
    )
    
    # Time specifications
    scheduled_time = models.TimeField(
        default='09:00',
        verbose_name=_('Scheduled Time'),
        help_text=_('Time of day to generate the report')
    )
    
    # Recipients - FIXED: Use settings.AUTH_USER_MODEL
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,  # Changed from User
        related_name='report_subscriptions',
        verbose_name=_('Recipients'),
        help_text=_('Users who will receive this report')
    )
    
    # Email configuration
    send_email = models.BooleanField(
        default=True,
        verbose_name=_('Send via Email')
    )
    email_subject = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Email Subject')
    )
    email_message = models.TextField(
        blank=True,
        verbose_name=_('Email Message')
    )
    
    # Status and metadata - FIXED: Use settings.AUTH_USER_MODEL
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Status')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed from User
        on_delete=models.CASCADE,
        related_name='created_schedules',
        verbose_name=_('Created By')
    )
    last_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Run')
    )
    next_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Next Run')
    )
    
    # Parameters for this specific schedule
    parameters = models.JSONField(
        default=dict,
        verbose_name=_('Report Parameters')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Report Schedule')
        verbose_name_plural = _('Report Schedules')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def calculate_next_run(self):
        """Calculate the next run date based on frequency."""
        from datetime import datetime, timedelta
        
        if not self.last_run:
            return datetime.combine(self.start_date, self.scheduled_time)
        
        last_run = self.last_run
        
        if self.frequency == 'daily':
            next_run = last_run + timedelta(days=1)
        elif self.frequency == 'weekly':
            next_run = last_run + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # Add approximately one month
            next_month = last_run.month % 12 + 1
            year = last_run.year + (last_run.month // 12)
            next_run = last_run.replace(year=year, month=next_month)
        elif self.frequency == 'quarterly':
            next_run = last_run + timedelta(days=90)
        elif self.frequency == 'yearly':
            next_run = last_run.replace(year=last_run.year + 1)
        else:
            next_run = last_run
        
        return datetime.combine(next_run.date(), self.scheduled_time)

class GeneratedReport(models.Model):
    """Stores generated reports."""
    
    class Format(models.TextChoices):
        PDF = 'pdf', _('PDF')
        EXCEL = 'excel', _('Excel')
        CSV = 'csv', _('CSV')
        HTML = 'html', _('HTML')
        JSON = 'json', _('JSON')
    
    class Status(models.TextChoices):
        GENERATING = 'generating', _('Generating')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        ARCHIVED = 'archived', _('Archived')
    
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.CASCADE,
        related_name='generated_reports',
        verbose_name=_('Report Type')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Report Title')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    # Generation details - FIXED: Use settings.AUTH_USER_MODEL
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed from User
        on_delete=models.CASCADE,
        related_name='generated_reports',
        verbose_name=_('Generated By')
    )
    generation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Generation Date')
    )
    
    # Time period covered
    period_start = models.DateField(
        verbose_name=_('Period Start')
    )
    period_end = models.DateField(
        verbose_name=_('Period End')
    )
    
    # File storage
    file = models.FileField(
        upload_to='reports/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Report File')
    )
    file_format = models.CharField(
        max_length=20,
        choices=Format.choices,
        verbose_name=_('File Format')
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name=_('File Size (bytes)')
    )
    
    # Parameters used for generation
    parameters = models.JSONField(
        default=dict,
        verbose_name=_('Generation Parameters')
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.GENERATING,
        verbose_name=_('Status')
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message')
    )
    generation_time = models.FloatField(
        default=0,
        verbose_name=_('Generation Time (seconds)')
    )
    
    # Scheduling info (if applicable)
    schedule = models.ForeignKey(
        ReportSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports',
        verbose_name=_('Scheduled Report')
    )
    
    # Access tracking
    download_count = models.IntegerField(
        default=0,
        verbose_name=_('Download Count')
    )
    last_downloaded = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Downloaded')
    )
    
    class Meta:
        verbose_name = _('Generated Report')
        verbose_name_plural = _('Generated Reports')
        ordering = ['-generation_date']
    
    def __str__(self):
        return f"{self.title} ({self.period_start} to {self.period_end})"
    
    def get_file_size_display(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def increment_download_count(self):
        """Increment download count and update last downloaded time."""
        self.download_count += 1
        self.last_downloaded = timezone.now()
        self.save()

class ReportTemplate(models.Model):
    """Custom report templates."""
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Template Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    # Template file
    template_file = models.FileField(
        upload_to='report_templates/',
        verbose_name=_('Template File'),
        help_text=_('HTML or other template file')
    )
    
    # Associated report types
    report_types = models.ManyToManyField(
        ReportType,
        related_name='templates',
        verbose_name=_('Applicable Report Types')
    )
    
    # Template metadata
    version = models.CharField(
        max_length=20,
        default='1.0.0',
        verbose_name=_('Version')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Default Template')
    )
    
    # FIXED: Use settings.AUTH_USER_MODEL
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed from User
        on_delete=models.CASCADE,
        related_name='created_templates',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Report Template')
        verbose_name_plural = _('Report Templates')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} v{self.version}"

class ReportAnalytics(models.Model):
    """Track report usage and analytics."""
    
    report = models.ForeignKey(
        GeneratedReport,
        on_delete=models.CASCADE,
        related_name='analytics',
        verbose_name=_('Report')
    )
    # FIXED: Use settings.AUTH_USER_MODEL
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed from User
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('User')
    )
    
    # Action tracking
    ACTION_CHOICES = [
        ('viewed', 'Viewed'),
        ('downloaded', 'Downloaded'),
        ('shared', 'Shared'),
        ('printed', 'Printed'),
        ('emailed', 'Emailed'),
    ]
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    action_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Action Time')
    )
    
    # Additional metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address')
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Session ID')
    )
    
    class Meta:
        verbose_name = _('Report Analytics')
        verbose_name_plural = _('Report Analytics')
        ordering = ['-action_time']
    
    def __str__(self):
        user_str = str(self.user) if self.user else "Anonymous"
        return f"{self.report.title} - {self.get_action_display()} by {user_str}"

class ReportDashboard(models.Model):
    """Dashboard configuration for reports."""
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Dashboard Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    # Dashboard layout
    layout_config = models.JSONField(
        default=dict,
        verbose_name=_('Layout Configuration'),
        help_text=_('JSON configuration for dashboard layout')
    )
    
    # Associated reports
    reports = models.ManyToManyField(
        ReportType,
        through='DashboardReport',
        verbose_name=_('Included Reports')
    )
    
    # Access control
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Public Dashboard')
    )
    # FIXED: Use settings.AUTH_USER_MODEL
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,  # Changed from User
        blank=True,
        related_name='accessible_dashboards',
        verbose_name=_('Allowed Users')
    )
    
    # Settings
    refresh_interval = models.IntegerField(
        default=300,
        verbose_name=_('Refresh Interval (seconds)'),
        help_text=_('Auto-refresh interval in seconds')
    )
    
    # FIXED: Use settings.AUTH_USER_MODEL
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed from User
        on_delete=models.CASCADE,
        related_name='created_dashboards',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Report Dashboard')
        verbose_name_plural = _('Report Dashboards')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class DashboardReport(models.Model):
    """Intermediate model for dashboard-reports relationship."""
    
    dashboard = models.ForeignKey(
        ReportDashboard,
        on_delete=models.CASCADE,
        verbose_name=_('Dashboard')
    )
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.CASCADE,
        verbose_name=_('Report Type')
    )
    
    # Position in dashboard
    position_x = models.IntegerField(
        default=0,
        verbose_name=_('X Position')
    )
    position_y = models.IntegerField(
        default=0,
        verbose_name=_('Y Position')
    )
    width = models.IntegerField(
        default=6,
        verbose_name=_('Width (columns)')
    )
    height = models.IntegerField(
        default=4,
        verbose_name=_('Height (rows)')
    )
    
    # Display settings
    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Custom Title')
    )
    show_title = models.BooleanField(
        default=True,
        verbose_name=_('Show Title')
    )
    refresh_interval = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Refresh Interval (seconds)')
    )
    
    # Parameters for this dashboard instance
    parameters = models.JSONField(
        default=dict,
        verbose_name=_('Report Parameters')
    )
    
    class Meta:
        verbose_name = _('Dashboard Report')
        verbose_name_plural = _('Dashboard Reports')
        unique_together = ['dashboard', 'report_type']
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.report_type.name} in {self.dashboard.name}"