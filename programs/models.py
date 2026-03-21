"""
Models for rehabilitation programs.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from accounts.models import User
from offenders.models import Offender

class ProgramCategory(models.Model):
    """Categories for rehabilitation programs."""
    name = models.CharField(
        max_length=100,
        verbose_name=_('Category Name')
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_('Slug'),
        help_text=_('Optional. Auto-generated from name if blank.')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    icon = models.CharField(
        max_length=50,
        default='fas fa-graduation-cap',
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
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Display Order')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name=_('Updated At')
    )
    
    class Meta:
        verbose_name = _('Program Category')
        verbose_name_plural = _('Program Categories')
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:110] or "category"
            slug = base
            i = 2
            while ProgramCategory.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                suffix = f"-{i}"
                slug = f"{base[: (120 - len(suffix))]}{suffix}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

class Program(models.Model):
    """Rehabilitation program model."""
    
    class ProgramType(models.TextChoices):
        VOCATIONAL = 'vocational', _('Vocational Training')
        EDUCATIONAL = 'educational', _('Educational')
        COUNSELING = 'counseling', _('Counseling')
        LIFE_SKILLS = 'life_skills', _('Life Skills')
        SUBSTANCE_ABUSE = 'substance_abuse', _('Substance Abuse')
        ANGER_MANAGEMENT = 'anger_management', _('Anger Management')
        OTHER = 'other', _('Other')
    
    class ProgramStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        ARCHIVED = 'archived', _('Archived')
        DRAFT = 'draft', _('Draft')

    # Basic Information
    code = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_('Program Code'),
        help_text=_('Optional short code, e.g., VTC-001')
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_('Program Name')
    )
    description = models.TextField(
        verbose_name=_('Description')
    )
    program_type = models.CharField(
        max_length=50,
        choices=ProgramType.choices,
        verbose_name=_('Program Type')
    )
    category = models.ForeignKey(
        ProgramCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programs',
        verbose_name=_('Category')
    )
    
    # Program Details
    frequency = models.CharField(
        max_length=20,
        choices=[
            ("daily", _("Daily")),
            ("weekly", _("Weekly")),
            ("biweekly", _("Bi-Weekly")),
            ("monthly", _("Monthly")),
            ("custom", _("Custom")),
        ],
        default="custom",
        verbose_name=_("Frequency"),
        help_text=_("General cadence; use schedule description for specifics.")
    )
    objectives = models.TextField(
        verbose_name=_('Program Objectives')
    )
    curriculum = models.TextField(
        blank=True,
        verbose_name=_('Curriculum Outline')
    )
    duration_weeks = models.IntegerField(
        verbose_name=_('Duration (weeks)'),
        validators=[MinValueValidator(1), MaxValueValidator(104)]
    )
    hours_per_week = models.IntegerField(
        verbose_name=_('Hours per Week'),
        validators=[MinValueValidator(1), MaxValueValidator(40)]
    )
    max_participants = models.IntegerField(
        verbose_name=_('Maximum Participants'),
        validators=[MinValueValidator(1)]
    )
    
    # Eligibility Criteria
    eligibility_criteria = models.TextField(
        blank=True,
        verbose_name=_('Eligibility Criteria')
    )
    target_risk_level = models.CharField(
        max_length=20,
        choices=[
            ('all', 'All Risk Levels'),
            ('low', 'Low Risk Only'),
            ('medium', 'Medium Risk Only'),
            ('high', 'High Risk Only'),
            ('low_medium', 'Low & Medium Risk'),
            ('medium_high', 'Medium & High Risk')
        ],
        default='all',
        verbose_name=_('Target Risk Level')
    )

    referral_required = models.BooleanField(
        default=False,
        verbose_name=_('Referral Required')
    )
    prerequisites = models.TextField(
        blank=True,
        verbose_name=_('Prerequisites')
    )
    completion_criteria = models.TextField(
        blank=True,
        verbose_name=_('Completion Criteria')
    )
    expected_outcomes = models.TextField(
        blank=True,
        verbose_name=_('Expected Outcomes')
    )
    
    # Facilitator Information
    facilitator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': [User.Role.OFFICER, User.Role.NGO]},
        related_name='facilitated_programs',
        verbose_name=_('Facilitator')
    )
    co_facilitator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role__in': [User.Role.OFFICER, User.Role.NGO]},
        related_name='co_facilitated_programs',
        verbose_name=_('Co-Facilitator')
    )
    facilitator_notes = models.TextField(
        blank=True,
        verbose_name=_('Facilitator Notes')
    )

    # Location & Schedule
    class DeliveryMethod(models.TextChoices):
        IN_PERSON = 'in_person', _('In-Person')
        ONLINE = 'online', _('Online')
        HYBRID = 'hybrid', _('Hybrid')

    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.IN_PERSON,
        verbose_name=_('Delivery Method')
    )
    location = models.CharField(
        max_length=200,
        verbose_name=_('Location')
    )
    schedule_description = models.TextField(
        verbose_name=_('Schedule Description'),
        help_text=_('E.g., Mondays & Wednesdays, 2-4 PM')
    )
    start_date = models.DateField(
        verbose_name=_('Start Date')
    )
    end_date = models.DateField(
        verbose_name=_('End Date')
    )
    enrollment_deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Enrollment Deadline')
    )
    
    # Cost & Resources
    cost_per_participant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name=_('Cost per Participant')
    )
    resources_required = models.TextField(
        blank=True,
        verbose_name=_('Resources Required')
    )
    
    # Status & Metadata
    status = models.CharField(
        max_length=20,
        choices=ProgramStatus.choices,
        default=ProgramStatus.DRAFT,
        verbose_name=_('Status')
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_('Featured Program')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_programs',
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
        verbose_name = _('Program')
        verbose_name_plural = _('Programs')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_program_type_display()})"

    @property
    def max_capacity(self):
        """Template compatibility alias for max_participants."""
        return self.max_participants
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'archived': 'dark',
            'draft': 'warning'
        }
        return colors.get(self.status, 'secondary')
    
    def current_participants_count(self):
        """Get count of active participants."""
        return self.enrollments.filter(status='active').count()
    
    def completion_rate(self):
        """Calculate completion rate."""
        total_enrollments = self.enrollments.count()
        if total_enrollments == 0:
            return 0
        completed = self.enrollments.filter(status='completed').count()
        return (completed / total_enrollments) * 100
    
    def is_accepting_enrollments(self):
        """Check if program is accepting new enrollments."""
        from datetime import date

        if self.status != 'active':
            return False
        if self.enrollment_deadline and date.today() > self.enrollment_deadline:
            return False
        if self.current_participants_count() >= self.max_participants:
            return False
        return True

class Enrollment(models.Model):
    """Program enrollment model."""
    
    class EnrollmentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending Approval')
        ACTIVE = 'active', _('Active')
        COMPLETED = 'completed', _('Completed')
        DROPPED_OUT = 'dropped_out', _('Dropped Out')
        TRANSFERRED = 'transferred', _('Transferred')
        SUSPENDED = 'suspended', _('Suspended')
    
    class CompletionGrade(models.TextChoices):
        EXCELLENT = 'excellent', _('Excellent')
        GOOD = 'good', _('Good')
        SATISFACTORY = 'satisfactory', _('Satisfactory')
        NEEDS_IMPROVEMENT = 'needs_improvement', _('Needs Improvement')
        INCOMPLETE = 'incomplete', _('Incomplete')
    
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('Program')
    )
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='program_enrollments',
        verbose_name=_('Offender')
    )
    
    # Enrollment Details
    enrollment_date = models.DateField(
        verbose_name=_('Enrollment Date')
    )
    referred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': User.Role.OFFICER},
        related_name='referred_enrollments',
        verbose_name=_('Referred By')
    )
    referral_notes = models.TextField(
        blank=True,
        verbose_name=_('Referral Notes')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING,
        verbose_name=_('Status')
    )
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Actual Start Date')
    )
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Actual End Date')
    )
    
    # Performance Tracking
    attendance_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Attendance Rate (%)')
    )
    participation_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name=_('Participation Score (0-10)')
    )
    skill_improvement = models.TextField(
        blank=True,
        verbose_name=_('Skill Improvement Assessment')
    )
    completion_grade = models.CharField(
        max_length=30,
        choices=CompletionGrade.choices,
        blank=True,
        verbose_name=_('Completion Grade')
    )
    certificate_issued = models.BooleanField(
        default=False,
        verbose_name=_('Certificate Issued')
    )
    certificate_issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Certificate Issue Date')
    )
    
    # Progress Notes
    progress_notes = models.TextField(
        blank=True,
        verbose_name=_('Progress Notes')
    )
    facilitator_feedback = models.TextField(
        blank=True,
        verbose_name=_('Facilitator Feedback')
    )
    officer_feedback = models.TextField(
        blank=True,
        verbose_name=_('Probation Officer Feedback')
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
        verbose_name = _('Enrollment')
        verbose_name_plural = _('Enrollments')
        unique_together = ['program', 'offender']
        ordering = ['-enrollment_date']
    
    def __str__(self):
        return f"{self.offender} in {self.program}"
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'pending': 'warning',
            'active': 'success',
            'completed': 'info',
            'dropped_out': 'danger',
            'transferred': 'primary',
            'suspended': 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def calculate_attendance_rate(self, total_sessions, attended_sessions):
        """Calculate attendance rate."""
        if total_sessions > 0:
            self.attendance_rate = (attended_sessions / total_sessions) * 100
            self.save()
    
    def days_enrolled(self):
        """Calculate days since enrollment."""
        from datetime import date
        if self.actual_start_date:
            start_date = self.actual_start_date
        else:
            start_date = self.enrollment_date
        
        end_date = self.actual_end_date or date.today()
        return (end_date - start_date).days

class Session(models.Model):
    """Program session/class model."""
    
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('Program')
    )
    
    # Session Details
    session_number = models.IntegerField(
        verbose_name=_('Session Number')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Session Title')
    )
    description = models.TextField(
        verbose_name=_('Session Description')
    )
    learning_objectives = models.TextField(
        blank=True,
        verbose_name=_('Learning Objectives')
    )
    date = models.DateField(
        verbose_name=_('Session Date')
    )
    start_time = models.TimeField(
        verbose_name=_('Start Time')
    )
    end_time = models.TimeField(
        verbose_name=_('End Time')
    )
    location = models.CharField(
        max_length=200,
        verbose_name=_('Location')
    )
    
    # Facilitator
    facilitator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': [User.Role.OFFICER, User.Role.NGO]},
        verbose_name=_('Facilitator')
    )
    
    # Materials
    materials_required = models.TextField(
        blank=True,
        verbose_name=_('Materials Required')
    )
    reference_materials = models.TextField(
        blank=True,
        verbose_name=_('Reference Materials')
    )
    
    # Status
    is_completed = models.BooleanField(
        default=False,
        verbose_name=_('Session Completed')
    )
    completion_notes = models.TextField(
        blank=True,
        verbose_name=_('Completion Notes')
    )
    
    class Meta:
        verbose_name = _('Session')
        verbose_name_plural = _('Sessions')
        ordering = ['program', 'session_number']
        unique_together = ['program', 'session_number']
    
    def __str__(self):
        return f"Session {self.session_number}: {self.title}"

class Attendance(models.Model):
    """Attendance tracking for program sessions."""
    
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('Session')
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('Enrollment')
    )
    
    # Attendance Status
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused Absence'),
        ('left_early', 'Left Early')
    ]
    
    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        verbose_name=_('Attendance Status')
    )
    check_in_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Check-in Time')
    )
    check_out_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Check-out Time')
    )
    
    # Performance
    participation_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name=_('Participation Score (0-10)')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Attendance')
        verbose_name_plural = _('Attendances')
        unique_together = ['session', 'enrollment']
    
    def __str__(self):
        return f"{self.enrollment.offender} - {self.session}"
