"""
Models for offender management.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from django.utils import timezone

class Offender(models.Model):
    """Main offender profile."""
    
    class RiskLevel(models.TextChoices):
        LOW = 'low', _('Low Risk')
        MEDIUM = 'medium', _('Medium Risk')
        HIGH = 'high', _('High Risk')
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='offender_profile',
        verbose_name=_('User Account')
    )
    offender_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Offender ID')
    )
    date_of_birth = models.DateField(
        verbose_name=_('Date of Birth')
    )
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        verbose_name=_('Gender')
    )
    nationality = models.CharField(
        max_length=100,
        default='Kenyan',
        verbose_name=_('Nationality')
    )
    id_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('National ID Number'),
        help_text=_('Kenyan National ID or Passport')
    )
    
    # Risk assessment
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
        verbose_name=_('Risk Level')
    )
    ml_risk_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('ML Risk Score'),
        help_text=_('AI-predicted risk score (0-1)')
    )
    
    # Contact information
    address = models.TextField(
        verbose_name=_('Physical Address')
    )
    county = models.CharField(
        max_length=100,
        verbose_name=_('County')
    )
    sub_county = models.CharField(
        max_length=100,
        verbose_name=_('Sub-County')
    )
    phone_alternative = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Alternative Phone')
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email Address')
    )
    
    # Emergency contact
    emergency_contact_name = models.CharField(
        max_length=100,
        verbose_name=_('Emergency Contact Name')
    )
    emergency_contact_phone = models.CharField(
        max_length=15,
        verbose_name=_('Emergency Contact Phone')
    )
    emergency_contact_relationship = models.CharField(
        max_length=50,
        verbose_name=_('Relationship')
    )
    
    # Metadata
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date Created')
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date Updated')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active Status')
    )
    
    class Meta:
        verbose_name = _('Offender')
        verbose_name_plural = _('Offenders')
        ordering = ['-date_created']
    
    def __str__(self):
        return f"{self.offender_id} - {self.user.get_full_name()}"

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    def get_full_name(self):
        return self.user.get_full_name()

    @property
    def probation_officer(self):
        """
        Convenience accessor used across dashboards/templates.

        Returns the officer for the offender's most recently-created active case, if any.
        """
        active_case = (
            self.cases.filter(status=Case.Status.ACTIVE)
            .select_related("probation_officer")
            .order_by("-date_created")
            .first()
        )
        return active_case.probation_officer if active_case else None

    @property
    def created_at(self):
        """Template compatibility alias for date_created."""
        return self.date_created
    
    def age(self):
        """Calculate age from date of birth."""
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    def get_risk_color(self):
        """Get Bootstrap color class for risk level."""
        colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger'
        }
        return colors.get(self.risk_level, 'secondary')

class Case(models.Model):
    """Offender's legal case information."""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        COMPLETED = 'completed', _('Completed')
        VIOLATED = 'violated', _('Probation Violated')
        TRANSFERRED = 'transferred', _('Transferred')
    
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name=_('Offender')
    )
    case_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Case Number')
    )
    court_name = models.CharField(
        max_length=200,
        verbose_name=_('Court Name')
    )
    court_location = models.CharField(
        max_length=200,
        verbose_name=_('Court Location')
    )
    
    # Offense details
    offense = models.CharField(
        max_length=300,
        verbose_name=_('Offense Committed')
    )
    offense_category = models.CharField(
        max_length=100,
        choices=[
            ('property', 'Property Crime'),
            ('violent', 'Violent Crime'),
            ('drug', 'Drug Offense'),
            ('traffic', 'Traffic Violation'),
            ('financial', 'Financial Crime'),
            ('other', 'Other')
        ],
        verbose_name=_('Offense Category')
    )
    offense_date = models.DateField(
        verbose_name=_('Date of Offense')
    )
    
    # Sentencing
    sentence_start = models.DateField(
        verbose_name=_('Sentence Start Date')
    )
    sentence_end = models.DateField(
        verbose_name=_('Sentence End Date')
    )
    sentence_duration = models.IntegerField(
        verbose_name=_('Sentence Duration (months)')
    )
    sentence_type = models.CharField(
        max_length=50,
        choices=[
            ('probation', 'Probation'),
            ('community_service', 'Community Service'),
            ('parole', 'Parole'),
            ('conditional_release', 'Conditional Release')
        ],
        verbose_name=_('Sentence Type')
    )
    
    # Probation officer assignment
    probation_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': User.Role.OFFICER},
        related_name='assigned_cases',
        verbose_name=_('Probation Officer')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Case Status')
    )
    
    # Additional information
    special_conditions = models.TextField(
        blank=True,
        verbose_name=_('Special Conditions'),
        help_text=_('Any special conditions or restrictions')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Additional Notes')
    )
    
    # Dates
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date Created')
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Date Updated')
    )
    
    class Meta:
        verbose_name = _('Case')
        verbose_name_plural = _('Cases')
        ordering = ['-date_created']
    
    def __str__(self):
        return f"{self.case_number} - {self.offender}"
    
    def get_status_color(self):
        """Get Bootstrap color class for case status."""
        colors = {
            'active': 'primary',
            'completed': 'success',
            'violated': 'danger',
            'transferred': 'warning'
        }
        return colors.get(self.status, 'secondary')
    
    def days_remaining(self):
        """Calculate days remaining in sentence."""
        from datetime import date
        if self.status == 'completed':
            return 0
        remaining = (self.sentence_end - date.today()).days
        return max(0, remaining)

class Assessment(models.Model):
    """Offender assessment for risk and needs."""
    
    offender = models.ForeignKey(
        Offender,
        on_delete=models.CASCADE,
        related_name='assessments',
        verbose_name=_('Offender')
    )
    assessment_date = models.DateField(
        verbose_name=_('Assessment Date')
    )
    assessed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': User.Role.OFFICER},
        verbose_name=_('Assessed By')
    )
    
    # Criminal History (0-10)
    criminal_history = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name=_('Criminal History Score'),
        help_text=_('Number of prior offenses (0-10)')
    )
    
    # Social Factors (1-5 scale)
    education_level = models.IntegerField(
        choices=[(1, 'No Formal Education'), (2, 'Primary'), (3, 'Secondary'), (4, 'Diploma'), (5, 'Degree/Higher')],
        verbose_name=_('Education Level')
    )
    employment_status = models.CharField(
        max_length=50,
        choices=[
            ('employed', 'Employed'),
            ('self_employed', 'Self-Employed'),
            ('unemployed', 'Unemployed'),
            ('student', 'Student'),
            ('casual', 'Casual Laborer')
        ],
        verbose_name=_('Employment Status')
    )
    employment_duration = models.IntegerField(
        default=0,
        verbose_name=_('Employment Duration (months)'),
        help_text=_('0 if unemployed')
    )
    
    # Behavioral Factors
    substance_abuse = models.BooleanField(
        default=False,
        verbose_name=_('Substance Abuse History')
    )
    mental_health_issues = models.BooleanField(
        default=False,
        verbose_name=_('Mental Health Issues')
    )
    anger_issues = models.BooleanField(
        default=False,
        verbose_name=_('Anger Management Issues')
    )
    
    # Support Systems (1-5 scale)
    family_support = models.IntegerField(
        choices=[(1, 'Very Low'), (2, 'Low'), (3, 'Moderate'), (4, 'High'), (5, 'Very High')],
        verbose_name=_('Family Support')
    )
    peer_support = models.IntegerField(
        choices=[(1, 'Very Low'), (2, 'Low'), (3, 'Moderate'), (4, 'High'), (5, 'Very High')],
        verbose_name=_('Peer Support')
    )
    community_ties = models.IntegerField(
        choices=[(1, 'Very Low'), (2, 'Low'), (3, 'Moderate'), (4, 'High'), (5, 'Very High')],
        verbose_name=_('Community Ties')
    )
    
    # Risk Factors
    financial_stability = models.IntegerField(
        choices=[(1, 'Very Unstable'), (2, 'Unstable'), (3, 'Moderate'), (4, 'Stable'), (5, 'Very Stable')],
        verbose_name=_('Financial Stability')
    )
    housing_stability = models.IntegerField(
        choices=[(1, 'Very Unstable'), (2, 'Unstable'), (3, 'Moderate'), (4, 'Stable'), (5, 'Very Stable')],
        verbose_name=_('Housing Stability')
    )
    
    # Overall Assessment
    overall_risk_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Overall Risk Score'),
        help_text=_('Calculated risk score (0-100)')
    )
    recommended_interventions = models.TextField(
        blank=True,
        verbose_name=_('Recommended Interventions')
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_('Assessment Notes')
    )

    @property
    def overall_risk_level(self):
        """Return risk level derived from overall_risk_score."""
        if self.overall_risk_score is None:
            return None
        if self.overall_risk_score < 30:
            return 'low'
        if self.overall_risk_score < 70:
            return 'medium'
        return 'high'

    @property
    def assessment_type(self):
        """Provide a display label for assessment type."""
        return "Risk Assessment"

    @property
    def next_assessment_date(self):
        """Fallback to current assessment date for scheduling display."""
        return self.assessment_date

    @property
    def is_overdue(self):
        return self.assessment_date < timezone.now().date()

    @property
    def is_completed(self):
        return self.assessment_date <= timezone.now().date()
    
    class Meta:
        verbose_name = _('Assessment')
        verbose_name_plural = _('Assessments')
        ordering = ['-assessment_date']
    
    def __str__(self):
        return f"Assessment for {self.offender} on {self.assessment_date}"
    
    def calculate_risk_score(self):
        """Calculate a basic risk score from assessment factors."""
        score = 0
        
        # Criminal history (weight: 30%)
        score += self.criminal_history * 3
        
        # Social factors (weight: 25%)
        score += (6 - self.education_level) * 2.5  # Lower education = higher risk
        if self.employment_status in ['unemployed', 'casual']:
            score += 10
        
        # Behavioral factors (weight: 25%)
        if self.substance_abuse:
            score += 12.5
        if self.mental_health_issues:
            score += 7.5
        if self.anger_issues:
            score += 5
        
        # Support systems (weight: 20%)
        score += (6 - self.family_support) * 2  # Lower support = higher risk
        score += (6 - self.peer_support) * 1
        score += (6 - self.community_ties) * 1
        
        return min(100, score)  # Cap at 100
    
    def save(self, *args, **kwargs):
        """Calculate risk score before saving."""
        if not self.overall_risk_score:
            self.overall_risk_score = self.calculate_risk_score()
        super().save(*args, **kwargs)
