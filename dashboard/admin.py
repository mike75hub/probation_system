"""
Admin configuration for dashboard app.
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    DashboardMetric, DashboardWidget, DashboardLayout, 
    DashboardWidgetPreference, ActivityLog, Notification,
    DashboardAnalytics
)

@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    """Admin for Dashboard Metrics."""
    list_display = ('metric_type', 'value', 'change', 'trend', 'calculated_at', 'is_valid')
    list_filter = ('metric_type', 'trend', 'period', 'calculated_at')
    search_fields = ('metric_type', 'label')
    readonly_fields = ('calculated_at', 'valid_until')
    fieldsets = (
        ('Basic Information', {
            'fields': ('metric_type', 'label', 'color', 'icon')
        }),
        ('Values', {
            'fields': ('value', 'change', 'trend', 'previous_value', 'comparison_period')
        }),
        ('Timing', {
            'fields': ('calculated_at', 'valid_until', 'period')
        }),
    )
    
    def is_valid(self, obj):
        """Display validity status."""
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'
    
    actions = ['recalculate_metrics']
    
    def recalculate_metrics(self, request, queryset):
        """Recalculate selected metrics."""
        for metric in queryset:
            metric_type = metric.metric_type
            if metric_type == 'offender_count':
                value = DashboardMetric.calculate_offender_count()
            elif metric_type == 'active_cases':
                value = DashboardMetric.calculate_active_cases()
            elif metric_type == 'high_risk':
                value = DashboardMetric.calculate_high_risk()
            else:
                continue
            DashboardMetric.update_metric(metric_type, value)
        
        self.message_user(request, f"Recalculated {queryset.count()} metrics.")
    recalculate_metrics.short_description = "Recalculate selected metrics"


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    """Admin for Dashboard Widgets."""
    list_display = ('name', 'widget_type', 'chart_type', 'is_active', 'is_default', 'order')
    list_filter = ('widget_type', 'chart_type', 'is_active', 'is_default', 'data_source')
    search_fields = ('name', 'title', 'description', 'metric_source')
    list_editable = ('is_active', 'is_default', 'order')
    filter_horizontal = ()
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'widget_type', 'chart_type', 'title', 'subtitle', 'description')
        }),
        ('Data Configuration', {
            'fields': ('data_source', 'metric_source', 'model_name', 'api_endpoint', 'custom_query')
        }),
        ('Display Configuration', {
            'fields': ('display_options', 'width_sm', 'width_md', 'width_lg', 'height')
        }),
        ('Visibility & Permissions', {
            'fields': ('roles', 'is_default', 'is_active', 'order')
        }),
        ('Performance', {
            'fields': ('refresh_interval', 'cache_duration')
        }),
        ('Positioning', {
            'fields': ('column', 'row')
        }),
    )
    prepopulated_fields = {'slug': ('name',)}
    
    def get_form(self, request, obj=None, **kwargs):
        """Add help text to form."""
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['roles'].help_text = 'Comma-separated list of roles: admin, officer, offender, judiciary'
        form.base_fields['display_options'].help_text = 'JSON format: {"colors": ["#4e73df"], "show_legend": true}'
        return form


class DashboardWidgetPreferenceInline(admin.TabularInline):
    """Inline for widget preferences."""
    model = DashboardWidgetPreference
    extra = 0
    fields = ('widget', 'is_visible', 'order', 'custom_title')
    readonly_fields = ('widget',)


@admin.register(DashboardLayout)
class DashboardLayoutAdmin(admin.ModelAdmin):
    """Admin for Dashboard Layouts."""
    list_display = ('user', 'theme', 'refresh_interval', 'version', 'updated_at')
    list_filter = ('theme', 'compact_mode', 'version')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('updated_at', 'last_reset', 'version')
    
    # FIXED: Removed 'widgets' from fieldsets since it's a ManyToManyField with custom through model
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Layout Configuration', {
            'fields': ('layout_config', 'widget_order')
        }),
        ('Display Settings', {
            'fields': ('theme', 'refresh_interval', 'show_animations', 'compact_mode')
        }),
        ('Grid Settings', {
            'fields': ('columns', 'row_height', 'margin')
        }),
        ('Versioning', {
            'fields': ('version', 'previous_layout', 'last_reset')
        }),
    )
    
    raw_id_fields = ('user',)
    inlines = [DashboardWidgetPreferenceInline]  # Use inline for widget preferences
    
    actions = ['reset_to_default']
    
    def reset_to_default(self, request, queryset):
        """Reset selected layouts to default."""
        for layout in queryset:
            user = layout.user
            role = getattr(user, 'role', 'user')
            layout.reset_to_default(role)
        
        self.message_user(request, f"Reset {queryset.count()} layouts to default.")
    reset_to_default.short_description = "Reset to default layout"


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin for Activity Logs."""
    list_display = ('user', 'action', 'module', 'severity', 'is_success', 'created_at')
    list_filter = ('action', 'module', 'severity', 'is_success', 'created_at')
    search_fields = ('user__username', 'description', 'ip_address')
    readonly_fields = ('created_at', 'timestamp', 'ip_address', 'user_agent', 'session_key')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'action', 'module', 'severity')
        }),
        ('Details', {
            'fields': ('description', 'details', 'content_type', 'object_id')
        }),
        ('Technical Information', {
            'fields': ('ip_address', 'user_agent', 'session_key', 'location', 'coordinates')
        }),
        ('Performance Metrics', {
            'fields': ('duration', 'memory_usage')
        }),
        ('Status', {
            'fields': ('is_success', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'timestamp')
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual addition of activity logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of activity logs."""
        return False
    
    def get_queryset(self, request):
        """Optimize queryset for performance."""
        return super().get_queryset(request).select_related('user')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notifications."""
    list_display = ('title', 'user', 'notification_type', 'priority', 'category', 
                   'is_read', 'is_dismissed', 'created_at')
    list_filter = ('notification_type', 'priority', 'category', 'is_read', 
                  'is_dismissed', 'delivery_method', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'source')
    readonly_fields = ('created_at', 'read_at', 'archived_at', 'dismissed_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'message', 'notification_type', 'priority', 'category')
        }),
        ('Actions', {
            'fields': ('action_url', 'action_text', 'action_data')
        }),
        ('Delivery', {
            'fields': ('delivery_method', 'email_sent', 'push_sent', 'sms_sent')
        }),
        ('Status', {
            'fields': ('is_read', 'is_archived', 'is_dismissed')
        }),
        ('Scheduling', {
            'fields': ('valid_from', 'valid_until', 'scheduled_for')
        }),
        ('Metadata', {
            'fields': ('source', 'source_id', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at', 'archived_at', 'dismissed_at')
        }),
    )
    raw_id_fields = ('user',)
    
    actions = ['mark_as_read', 'mark_as_dismissed', 'send_notifications']
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"Marked {updated} notifications as read.")
    mark_as_read.short_description = "Mark as read"
    
    def mark_as_dismissed(self, request, queryset):
        """Mark selected notifications as dismissed."""
        updated = queryset.update(is_dismissed=True, dismissed_at=timezone.now())
        self.message_user(request, f"Dismissed {updated} notifications.")
    mark_as_dismissed.short_description = "Dismiss notifications"
    
    def send_notifications(self, request, queryset):
        """Send selected notifications."""
        sent_count = 0
        for notification in queryset:
            if not notification.email_sent:
                notification.send_email()
                sent_count += 1
        
        self.message_user(request, f"Sent {sent_count} notifications.")
    send_notifications.short_description = "Send notifications"


# Temporarily comment out DashboardAnalyticsAdmin if it causes errors
# @admin.register(DashboardAnalytics)
# class DashboardAnalyticsAdmin(admin.ModelAdmin):
#     """Admin for Dashboard Analytics."""
#     list_display = ('date', 'total_visits', 'unique_users', 'avg_load_time', 
#                    'active_users', 'calculated_at')
#     list_filter = ('date',)
#     search_fields = ('most_viewed_widget', 'most_common_error')
#     readonly_fields = ('calculated_at', 'details')
#     fieldsets = (
#         ('Date', {
#             'fields': ('date',)
#         }),
#         ('Usage Metrics', {
#             'fields': ('total_visits', 'unique_users', 'average_session_duration')
#         }),
#         ('Widget Usage', {
#             'fields': ('most_viewed_widget', 'widget_interactions')
#         }),
#         ('Performance', {
#             'fields': ('avg_load_time', 'api_calls', 'cache_hit_rate')
#         }),
#         ('User Engagement', {
#             'fields': ('active_users', 'returning_users')
#         }),
#         ('Error Tracking', {
#             'fields': ('errors_count', 'most_common_error')
#         }),
#         ('Device Usage', {
#             'fields': ('mobile_visits', 'desktop_visits')
#         }),
#         ('Details', {
#             'fields': ('details',)
#         }),
#         ('Calculation', {
#             'fields': ('calculated_at',)
#         }),
#     )
    
#     def has_add_permission(self, request):
#         """Prevent manual addition of analytics."""
#         return False
    
#     def has_change_permission(self, request, obj=None):
#         """Prevent editing of analytics."""
#         return False

# Custom admin site configuration
class DashboardAdminSite(admin.AdminSite):
    """Custom admin site for dashboard."""
    site_header = "Probation System Dashboard Administration"
    site_title = "Dashboard Admin"
    index_title = "Dashboard Management"

# Register models with custom admin site if needed
dashboard_admin_site = DashboardAdminSite(name='dashboard_admin')
dashboard_admin_site.register(DashboardMetric, DashboardMetricAdmin)
dashboard_admin_site.register(DashboardWidget, DashboardWidgetAdmin)
dashboard_admin_site.register(DashboardLayout, DashboardLayoutAdmin)
dashboard_admin_site.register(ActivityLog, ActivityLogAdmin)
dashboard_admin_site.register(Notification, NotificationAdmin)
# dashboard_admin_site.register(DashboardAnalytics, DashboardAnalyticsAdmin)