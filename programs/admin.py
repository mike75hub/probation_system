"""
Admin configuration for programs app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import ProgramCategory, Program, Enrollment, Session, Attendance

@admin.register(ProgramCategory)
class ProgramCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'display_order', 'icon_display', 'color_display', 'program_count', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['is_active', 'color']
    ordering = ['display_order', 'name']
    
    def icon_display(self, obj):
        return format_html('<i class="{}"></i> {}', obj.icon, obj.icon)
    icon_display.short_description = 'Icon'
    
    def color_display(self, obj):
        return format_html(
            '<span class="badge bg-{}">{}</span>', 
            obj.color, obj.color.title()
        )
    color_display.short_description = 'Color'
    
    def program_count(self, obj):
        return obj.programs.count()
    program_count.short_description = 'Programs'

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'program_type', 'delivery_method', 'status_badge', 'duration_weeks',
        'current_participants', 'max_participants', 'start_date', 'is_featured'
    ]
    list_filter = ['program_type', 'delivery_method', 'status', 'category', 'is_featured', 'start_date']
    search_fields = ['name', 'code', 'description', 'objectives']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description', 'program_type', 'category', 'objectives')
        }),
        ('Program Details', {
            'fields': ('frequency', 'curriculum', 'duration_weeks', 'hours_per_week', 'max_participants')
        }),
        ('Eligibility', {
            'fields': (
                'eligibility_criteria',
                'target_risk_level',
                'referral_required',
                'prerequisites',
                'completion_criteria',
                'expected_outcomes',
            )
        }),
        ('Facilitators', {
            'fields': ('facilitator', 'co_facilitator', 'facilitator_notes')
        }),
        ('Schedule & Location', {
            'fields': (
                'delivery_method',
                'location',
                'schedule_description',
                'start_date',
                'end_date',
                'enrollment_deadline',
            )
        }),
        ('Cost & Resources', {
            'fields': ('cost_per_participant', 'resources_required')
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'created_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'archived': 'dark',
            'draft': 'warning'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def current_participants(self, obj):
        return obj.current_participants_count()
    current_participants.short_description = 'Current Participants'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'offender', 'program', 'status_badge', 'enrollment_date',
        'attendance_rate', 'completion_grade', 'certificate_issued'
    ]
    list_filter = ['status', 'program', 'enrollment_date', 'certificate_issued']
    search_fields = ['offender__user__first_name', 'offender__user__last_name', 'program__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Enrollment Details', {
            'fields': ('program', 'offender', 'referred_by', 'referral_notes')
        }),
        ('Status', {
            'fields': ('status', 'enrollment_date', 'actual_start_date', 'actual_end_date')
        }),
        ('Performance', {
            'fields': ('attendance_rate', 'participation_score', 'skill_improvement')
        }),
        ('Completion', {
            'fields': ('completion_grade', 'certificate_issued', 'certificate_issue_date')
        }),
        ('Feedback', {
            'fields': ('progress_notes', 'facilitator_feedback', 'officer_feedback')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'active': 'success',
            'completed': 'info',
            'dropped_out': 'danger',
            'transferred': 'primary',
            'suspended': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['program', 'session_number', 'title', 'date', 'facilitator', 'is_completed']
    list_filter = ['program', 'date', 'is_completed']
    search_fields = ['title', 'description', 'program__name']
    ordering = ['program', 'session_number']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['session', 'enrollment', 'status', 'check_in_time', 'participation_score']
    list_filter = ['status', 'session__program', 'session__date']
    search_fields = ['enrollment__offender__user__first_name', 'enrollment__offender__user__last_name']
