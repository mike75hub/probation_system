"""
Admin configuration for offenders app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Offender, Case, Assessment

class AssessmentInline(admin.TabularInline):
    """Inline display for assessments."""
    model = Assessment
    extra = 1
    readonly_fields = ['overall_risk_score']

class CaseInline(admin.TabularInline):
    """Inline display for cases."""
    model = Case
    extra = 1
    readonly_fields = ['days_remaining']

@admin.register(Offender)
class OffenderAdmin(admin.ModelAdmin):
    """Admin interface for Offenders."""
    
    list_display = [
        'offender_id', 
        'user_display', 
        'age', 
        'risk_level_display',
        'is_active',
        'date_created'
    ]
    
    list_filter = [
        'risk_level',
        'is_active',
        'gender',
        'county',
        'date_created'
    ]
    
    search_fields = [
        'offender_id',
        'user__first_name',
        'user__last_name',
        'user__username',
        'id_number',
        'county'
    ]
    
    readonly_fields = [
        'date_created',
        'date_updated',
        'age',
        'ml_risk_score'
    ]
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'user',
                'offender_id',
                'date_of_birth',
                'age',
                'gender',
                'nationality',
                'id_number'
            )
        }),
        ('Contact Information', {
            'fields': (
                'address',
                'county',
                'sub_county',
                'phone_alternative',
                'email',
                'emergency_contact_name',
                'emergency_contact_phone',
                'emergency_contact_relationship'
            )
        }),
        ('Risk Assessment', {
            'fields': (
                'risk_level',
                'ml_risk_score',
                'is_active'
            )
        }),
        ('Metadata', {
            'fields': (
                'date_created',
                'date_updated'
            )
        }),
    )
    
    inlines = [CaseInline, AssessmentInline]
    
    def user_display(self, obj):
        """Display user's full name."""
        return obj.user.get_full_name()
    user_display.short_description = 'Name'
    
    def risk_level_display(self, obj):
        """Display risk level with color."""
        colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger'
        }
        color = colors.get(obj.risk_level, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_risk_level_display()
        )
    risk_level_display.short_description = 'Risk Level'

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """Admin interface for Cases."""
    
    list_display = [
        'case_number',
        'offender_display',
        'offense',
        'sentence_type',
        'status_display',
        'probation_officer_display',
        'days_remaining_display'
    ]
    
    list_filter = [
        'status',
        'sentence_type',
        'offense_category',
        'court_location',
        'date_created'
    ]
    
    search_fields = [
        'case_number',
        'offender__offender_id',
        'offender__user__first_name',
        'offender__user__last_name',
        'offense',
        'court_name'
    ]
    
    readonly_fields = [
        'date_created',
        'date_updated',
        'days_remaining'
    ]
    
    fieldsets = (
        ('Case Information', {
            'fields': (
                'case_number',
                'offender',
                'court_name',
                'court_location'
            )
        }),
        ('Offense Details', {
            'fields': (
                'offense',
                'offense_category',
                'offense_date'
            )
        }),
        ('Sentencing', {
            'fields': (
                'sentence_start',
                'sentence_end',
                'sentence_duration',
                'sentence_type',
                'days_remaining'
            )
        }),
        ('Assignment', {
            'fields': (
                'probation_officer',
                'status'
            )
        }),
        ('Additional Information', {
            'fields': (
                'special_conditions',
                'notes'
            )
        }),
        ('Metadata', {
            'fields': (
                'date_created',
                'date_updated'
            )
        }),
    )
    
    def offender_display(self, obj):
        """Display offender information."""
        return f"{obj.offender.offender_id} - {obj.offender.user.get_full_name()}"
    offender_display.short_description = 'Offender'
    
    def status_display(self, obj):
        """Display status with color."""
        colors = {
            'active': 'primary',
            'completed': 'success',
            'violated': 'danger',
            'transferred': 'warning'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def probation_officer_display(self, obj):
        """Display probation officer."""
        if obj.probation_officer:
            return obj.probation_officer.get_full_name()
        return '-'
    probation_officer_display.short_description = 'Officer'
    
    def days_remaining_display(self, obj):
        """Display days remaining."""
        days = obj.days_remaining()
        if days == 0:
            return format_html('<span class="badge bg-success">Completed</span>')
        elif days < 30:
            return format_html('<span class="badge bg-danger">{} days</span>', days)
        elif days < 90:
            return format_html('<span class="badge bg-warning">{} days</span>', days)
        else:
            return format_html('<span class="badge bg-info">{} days</span>', days)
    days_remaining_display.short_description = 'Remaining'

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """Admin interface for Assessments."""
    
    list_display = [
        'offender_display',
        'assessment_date',
        'criminal_history',
        'employment_status',
        'overall_risk_score_display',
        'assessed_by_display'
    ]
    
    list_filter = [
        'assessment_date',
        'substance_abuse',
        'mental_health_issues',
        'employment_status'
    ]
    
    search_fields = [
        'offender__offender_id',
        'offender__user__first_name',
        'offender__user__last_name',
        'notes'
    ]
    
    readonly_fields = [
        'overall_risk_score',
        'calculate_risk_score'
    ]
    
    fieldsets = (
        ('Assessment Information', {
            'fields': (
                'offender',
                'assessment_date',
                'assessed_by'
            )
        }),
        ('Criminal History', {
            'fields': ('criminal_history',)
        }),
        ('Social Factors', {
            'fields': (
                'education_level',
                'employment_status',
                'employment_duration'
            )
        }),
        ('Behavioral Factors', {
            'fields': (
                'substance_abuse',
                'mental_health_issues',
                'anger_issues'
            )
        }),
        ('Support Systems', {
            'fields': (
                'family_support',
                'peer_support',
                'community_ties'
            )
        }),
        ('Risk Factors', {
            'fields': (
                'financial_stability',
                'housing_stability'
            )
        }),
        ('Results', {
            'fields': (
                'overall_risk_score',
                'recommended_interventions',
                'notes'
            )
        }),
    )
    
    def offender_display(self, obj):
        """Display offender information."""
        return f"{obj.offender.offender_id} - {obj.offender.user.get_full_name()}"
    offender_display.short_description = 'Offender'
    
    def overall_risk_score_display(self, obj):
        """Display risk score with color."""
        score = obj.overall_risk_score or 0
        if score < 30:
            color = 'success'
            text = f'Low ({score:.1f})'
        elif score < 70:
            color = 'warning'
            text = f'Medium ({score:.1f})'
        else:
            color = 'danger'
            text = f'High ({score:.1f})'
        
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            text
        )
    overall_risk_score_display.short_description = 'Risk Score'
    
    def assessed_by_display(self, obj):
        """Display assessor name."""
        if obj.assessed_by:
            return obj.assessed_by.get_full_name()
        return '-'
    assessed_by_display.short_description = 'Assessed By'