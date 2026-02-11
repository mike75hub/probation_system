"""
Models for offender monitoring and supervision.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from offenders.models import Offender, Case

class CheckInType(models.Model):
    """Types of check-ins (in-person, phone, video, etc.)"""
    name = models.CharField(
        max_length=100,
        verbose_name=_('Check-in Type')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    icon = models.CharField(
        max_length=50,
        default='fas fa-check-circle',
        help_text=_('Font Awesome icon class')
    )
    color = models.CharField(
        max_length=20,
        default='primary',
        help_text=_('Bootstrap color class')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )
    
    class Meta:
        verbose_name = _('Check-in Type')
        verbose_name_plural = _('Check-in Types')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class CheckIn(models.Model):
    """Offender check-in/supervision meeting."""
    
    class CheckInStatus(models.TextChoices):
        SCHEDULED = 'scheduled', _('Scheduled')
        COMPLETED = 'completed', _('Completed')
        MISSED = 'missed', _('Missed')
        CANCELLED = 'cancelled', _('Cancelled')
        RESCHEDULED = 'rescheduled', _('Rescheduled')
    
    class ComplianceLevel(models.TextChoices):
        FULL_COMPLIANCE = 'full', _('Full Compliance')
        PARTIAL_COMPLIANCE = 'partial', _('Partial Compliance')
        NON_COMPLIANT = 'non', _('Non-Compliant')
    
    # Basic Information
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='checkins',
        verbose_name=_('Case')
    )
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='checkins',
        verbose_name=_('Offender')
    )
    probation_officer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': User.Role.OFFICER},
        related_name='supervised_checkins',
        verbose_name=_('Probation Officer')
    )
    
    # Check-in Details
    checkin_type = models.ForeignKey(
        CheckInType,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Check-in Type')
    )
    scheduled_date = models.DateTimeField(
        verbose_name=_('Scheduled Date & Time')
    )
    actual_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Actual Date & Time')
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Location')
    )
    purpose = models.TextField(
        verbose_name=_('Purpose of Check-in')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=CheckInStatus.choices,
        default=CheckInStatus.SCHEDULED,
        verbose_name=_('Status')
    )
    compliance_level = models.CharField(
        max_length=20,
        choices=ComplianceLevel.choices,
        blank=True,
        verbose_name=_('Compliance Level')
    )
    
    # Assessment
    risk_assessment = models.TextField(
        blank=True,
        verbose_name=_('Risk Assessment')
    )
    behavior_notes = models.TextField(
        blank=True,
        verbose_name=_('Behavior Notes')
    )
    progress_notes = models.TextField(
        blank=True,
        verbose_name=_('Progress Notes')
    )
    concerns_issues = models.TextField(
        blank=True,
        verbose_name=_('Concerns/Issues')
    )
    
    # Recommendations
    recommendations = models.TextField(
        blank=True,
        verbose_name=_('Recommendations')
    )
    next_steps = models.TextField(
        blank=True,
        verbose_name=_('Next Steps')
    )
    next_checkin_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Next Check-in Date')
    )
    
    # Verification
    officer_signature = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Officer Signature')
    )
    offender_signature = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Offender Signature')
    )
    witness_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Witness Name')
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_checkins',
        verbose_name=_('Created By')
    )
    
    class Meta:
        verbose_name = _('Check-in')
        verbose_name_plural = _('Check-ins')
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"Check-in: {self.offender} - {self.scheduled_date.strftime('%Y-%m-%d %H:%M')}"
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'scheduled': 'info',
            'completed': 'success',
            'missed': 'danger',
            'cancelled': 'warning',
            'rescheduled': 'primary'
        }
        return colors.get(self.status, 'secondary')
    
    def get_compliance_color(self):
        """Get Bootstrap color class for compliance."""
        colors = {
            'full': 'success',
            'partial': 'warning',
            'non': 'danger'
        }
        return colors.get(self.compliance_level, 'secondary')
    
    def is_overdue(self):
        """Check if check-in is overdue."""
        from django.utils import timezone
        return self.status == 'scheduled' and self.scheduled_date < timezone.now()
    
    def duration_minutes(self):
        """Calculate duration in minutes."""
        if self.actual_date and self.scheduled_date:
            duration = self.actual_date - self.scheduled_date
            return duration.total_seconds() / 60
        return 0

class GPSMonitoring(models.Model):
    """GPS monitoring/tracking for offenders."""
    
    class DeviceStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        MAINTENANCE = 'maintenance', _('Maintenance')
        LOST = 'lost', _('Lost')
        DAMAGED = 'damaged', _('Damaged')
    
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='gps_monitoring',
        verbose_name=_('Offender')
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='gps_monitoring',
        verbose_name=_('Case')
    )
    
    # Device Information
    device_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Device ID')
    )
    device_type = models.CharField(
        max_length=100,
        verbose_name=_('Device Type')
    )
    device_status = models.CharField(
        max_length=20,
        choices=DeviceStatus.choices,
        default=DeviceStatus.ACTIVE,
        verbose_name=_('Device Status')
    )
    issued_date = models.DateField(
        verbose_name=_('Issued Date')
    )
    expected_return_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Expected Return Date')
    )
    actual_return_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Actual Return Date')
    )
    
    # Monitoring Settings
    monitoring_start_date = models.DateField(
        verbose_name=_('Monitoring Start Date')
    )
    monitoring_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Monitoring End Date')
    )
    checkin_frequency_hours = models.IntegerField(
        default=1,
        verbose_name=_('Check-in Frequency (hours)')
    )
    restricted_zones = models.TextField(
        blank=True,
        verbose_name=_('Restricted Zones'),
        help_text=_('JSON format of restricted areas')
    )
    curfew_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Curfew Start Time')
    )
    curfew_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Curfew End Time')
    )
    
    # Device Metadata
    battery_level = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Battery Level (%)')
    )
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Sync Time')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('GPS Monitoring')
        verbose_name_plural = _('GPS Monitoring')
        ordering = ['-issued_date']
    
    def __str__(self):
        return f"GPS Device {self.device_id} - {self.offender}"
    
    def is_active(self):
        """Check if GPS monitoring is currently active."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.device_status != 'active':
            return False
        
        if self.monitoring_end_date and self.monitoring_end_date < today:
            return False
        
        return True

class GPSLocation(models.Model):
    """GPS location tracking data."""
    
    gps_monitoring = models.ForeignKey(
        GPSMonitoring,
        on_delete=models.CASCADE,
        related_name='locations',
        verbose_name=_('GPS Monitoring')
    )
    
    # Location Data
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name=_('Latitude')
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name=_('Longitude')
    )
    accuracy = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Accuracy (meters)')
    )
    altitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Altitude (meters)')
    )
    speed = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Speed (km/h)')
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        verbose_name=_('Location Timestamp')
    )
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Recorded At')
    )
    
    # Status
    is_in_restricted_zone = models.BooleanField(
        default=False,
        verbose_name=_('In Restricted Zone')
    )
    is_curfew_violation = models.BooleanField(
        default=False,
        verbose_name=_('Curfew Violation')
    )
    battery_level = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Battery Level (%)')
    )
    
    # Additional Data
    address = models.TextField(
        blank=True,
        verbose_name=_('Address')
    )
    provider = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Location Provider')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('GPS Location')
        verbose_name_plural = _('GPS Locations')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['gps_monitoring', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"Location: {self.latitude}, {self.longitude} at {self.timestamp}"

class DrugTest(models.Model):
    """Drug and alcohol testing records."""
    
    class TestType(models.TextChoices):
        URINE = 'urine', _('Urine Test')
        BREATH = 'breath', _('Breathalyzer')
        SALIVA = 'saliva', _('Saliva Test')
        HAIR = 'hair', _('Hair Follicle Test')
        BLOOD = 'blood', _('Blood Test')
    
    class TestResult(models.TextChoices):
        NEGATIVE = 'negative', _('Negative')
        POSITIVE = 'positive', _('Positive')
        INCONCLUSIVE = 'inconclusive', _('Inconclusive')
        REFUSED = 'refused', _('Refused to Test')
        TAMPERED = 'tampered', _('Sample Tampered')
    
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='drug_tests',
        verbose_name=_('Offender')
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='drug_tests',
        verbose_name=_('Case')
    )
    conducted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': [User.Role.OFFICER, User.Role.NGO]},
        verbose_name=_('Conducted By')
    )
    
    # Test Information
    test_type = models.CharField(
        max_length=20,
        choices=TestType.choices,
        verbose_name=_('Test Type')
    )
    test_date = models.DateTimeField(
        verbose_name=_('Test Date & Time')
    )
    location = models.CharField(
        max_length=200,
        verbose_name=_('Test Location')
    )
    
    # Results
    result = models.CharField(
        max_length=20,
        choices=TestResult.choices,
        verbose_name=_('Test Result')
    )
    substances_tested = models.TextField(
        verbose_name=_('Substances Tested'),
        help_text=_('Comma-separated list of substances')
    )
    substances_detected = models.TextField(
        blank=True,
        verbose_name=_('Substances Detected'),
        help_text=_('Comma-separated list of detected substances')
    )
    concentration_levels = models.TextField(
        blank=True,
        verbose_name=_('Concentration Levels'),
        help_text=_('JSON format of substance concentrations')
    )
    
    # Observations
    observations = models.TextField(
        blank=True,
        verbose_name=_('Observations')
    )
    offender_comments = models.TextField(
        blank=True,
        verbose_name=_('Offender Comments')
    )
    
    # Follow-up
    follow_up_required = models.BooleanField(
        default=False,
        verbose_name=_('Follow-up Required')
    )
    follow_up_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Follow-up Date')
    )
    recommendations = models.TextField(
        blank=True,
        verbose_name=_('Recommendations')
    )
    
    # Verification
    witness_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Witness Name')
    )
    lab_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Lab Reference Number')
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Drug Test')
        verbose_name_plural = _('Drug Tests')
        ordering = ['-test_date']
    
    def __str__(self):
        return f"Drug Test: {self.offender} - {self.test_date.strftime('%Y-%m-%d')}"
    
    def get_result_color(self):
        """Get Bootstrap color class for result."""
        colors = {
            'negative': 'success',
            'positive': 'danger',
            'inconclusive': 'warning',
            'refused': 'secondary',
            'tampered': 'dark'
        }
        return colors.get(self.result, 'secondary')

class EmploymentVerification(models.Model):
    """Employment verification records."""
    
    class VerificationStatus(models.TextChoices):
        VERIFIED = 'verified', _('Verified')
        UNVERIFIED = 'unverified', _('Unverified')
        PENDING = 'pending', _('Pending Verification')
        TERMINATED = 'terminated', _('Employment Terminated')
    
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='employment_verifications',
        verbose_name=_('Offender')
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='employment_verifications',
        verbose_name=_('Case')
    )
    
    # Employment Details
    employer_name = models.CharField(
        max_length=200,
        verbose_name=_('Employer Name')
    )
    employer_address = models.TextField(
        verbose_name=_('Employer Address')
    )
    employer_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Employer Phone')
    )
    employer_email = models.EmailField(
        blank=True,
        verbose_name=_('Employer Email')
    )
    
    # Position Details
    position = models.CharField(
        max_length=200,
        verbose_name=_('Position/Job Title')
    )
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('contract', 'Contract'),
            ('temporary', 'Temporary'),
            ('self_employed', 'Self-Employed')
        ],
        verbose_name=_('Employment Type')
    )
    start_date = models.DateField(
        verbose_name=_('Start Date')
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('End Date')
    )
    
    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name=_('Verification Status')
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': User.Role.OFFICER},
        verbose_name=_('Verified By')
    )
    verification_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Verification Date')
    )
    verification_method = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Verification Method')
    )
    
    # Income & Hours
    hours_per_week = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Hours per Week')
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Salary/Wage')
    )
    pay_frequency = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('weekly', 'Weekly'),
            ('biweekly', 'Bi-weekly'),
            ('monthly', 'Monthly'),
            ('daily', 'Daily')
        ],
        verbose_name=_('Pay Frequency')
    )
    
    # Supervisor Contact
    supervisor_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Supervisor Name')
    )
    supervisor_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Supervisor Phone')
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_employment_verifications',
        verbose_name=_('Created By')
    )
    
    class Meta:
        verbose_name = _('Employment Verification')
        verbose_name_plural = _('Employment Verifications')
        ordering = ['-start_date']
    
    def __str__(self):
        return f"Employment: {self.offender} - {self.employer_name}"
    
    def is_current(self):
        """Check if employment is current."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.verification_status != 'verified':
            return False
        
        if self.end_date and self.end_date < today:
            return False
        
        return True
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'verified': 'success',
            'unverified': 'danger',
            'pending': 'warning',
            'terminated': 'secondary'
        }
        return colors.get(self.verification_status, 'secondary')

class Alert(models.Model):
    """Monitoring alerts and notifications."""
    
    class AlertType(models.TextChoices):
        CHECKIN_MISSED = 'checkin_missed', _('Check-in Missed')
        GPS_VIOLATION = 'gps_violation', _('GPS Violation')
        DRUG_TEST_POSITIVE = 'drug_test_positive', _('Positive Drug Test')
        EMPLOYMENT_TERMINATED = 'employment_terminated', _('Employment Terminated')
        CURFEW_VIOLATION = 'curfew_violation', _('Curfew Violation')
        RESTRICTED_ZONE = 'restricted_zone', _('Restricted Zone Entry')
        BATTERY_LOW = 'battery_low', _('GPS Battery Low')
        SYSTEM = 'system', _('System Alert')
        OTHER = 'other', _('Other')
    
    class AlertPriority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        CRITICAL = 'critical', _('Critical')
    
    class AlertStatus(models.TextChoices):
        NEW = 'new', _('New')
        ACKNOWLEDGED = 'acknowledged', _('Acknowledged')
        IN_PROGRESS = 'in_progress', _('In Progress')
        RESOLVED = 'resolved', _('Resolved')
        CLOSED = 'closed', _('Closed')
    
    # Alert Information
    alert_type = models.CharField(
        max_length=50,
        choices=AlertType.choices,
        verbose_name=_('Alert Type')
    )
    priority = models.CharField(
        max_length=20,
        choices=AlertPriority.choices,
        default=AlertPriority.MEDIUM,
        verbose_name=_('Priority')
    )
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.NEW,
        verbose_name=_('Status')
    )
    
    # Related Entities
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name=_('Offender')
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts',
        verbose_name=_('Case')
    )
    related_checkin = models.ForeignKey(
        CheckIn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Related Check-in')
    )
    related_gps = models.ForeignKey(
        GPSMonitoring,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Related GPS Monitoring')
    )
    
    # Alert Details
    title = models.CharField(
        max_length=200,
        verbose_name=_('Alert Title')
    )
    description = models.TextField(
        verbose_name=_('Description')
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Location')
    )
    
    # Timestamps
    alert_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Alert Time')
    )
    acknowledged_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Acknowledged Time')
    )
    resolved_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved Time')
    )
    
    # Resolution
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name=_('Acknowledged By')
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name=_('Resolved By')
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name=_('Resolution Notes')
    )
    action_taken = models.TextField(
        blank=True,
        verbose_name=_('Action Taken')
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Alert')
        verbose_name_plural = _('Alerts')
        ordering = ['-alert_time']
    
    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.title}"
    
    def get_priority_color(self):
        """Get Bootstrap color class for priority."""
        colors = {
            'low': 'info',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'dark'
        }
        return colors.get(self.priority, 'secondary')
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'new': 'danger',
            'acknowledged': 'warning',
            'in_progress': 'info',
            'resolved': 'success',
            'closed': 'secondary'
        }
        return colors.get(self.status, 'secondary')