"""
Views for dashboard functionality with enhanced features and performance.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q, F, Sum
from django.db.models.functions import TruncMonth, TruncDay, ExtractWeek
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from datetime import datetime, timedelta, date
import calendar

from accounts.models import User
from offenders.models import Offender, Case, Assessment
from programs.models import Program, Enrollment
from monitoring.models import CheckIn, GPSMonitoring, DrugTest
from datasets.models import Dataset, DatasetSource
from ml_models.models import MLModel, Prediction, TrainingJob
from reports.models import GeneratedReport, ReportSchedule

from .models import (
    DashboardMetric, DashboardWidget, DashboardLayout, 
    DashboardWidgetPreference, ActivityLog, Notification,
    DashboardAnalytics
)

logger = logging.getLogger(__name__)

def is_admin(user):
    """Check if user is admin."""
    return user.is_authenticated and (user.is_superuser or user.role == 'admin')

def is_officer(user):
    """Check if user is officer."""
    return user.is_authenticated and user.role == 'officer'

def is_offender(user):
    """Check if user is offender."""
    return user.is_authenticated and user.role == 'offender'

def is_judiciary(user):
    """Check if user is judiciary staff."""
    return user.is_authenticated and user.role == 'judiciary'

def log_dashboard_access(user, request=None):
    """Log dashboard access with performance tracking."""
    start_time = timezone.now()
    
    # Log the access
    activity = ActivityLog.log_activity(
        user=user,
        action='view',
        module='dashboard',
        description='Accessed dashboard',
        request=request,
        details={'dashboard_version': 'v2.0'}
    )
    
    # Update dashboard analytics
    try:
        today = timezone.now().date()
        analytics, created = DashboardAnalytics.objects.get_or_create(date=today)
        analytics.total_visits += 1
        if not analytics.details.get('user_ids'):
            analytics.details['user_ids'] = []
        if user.id not in analytics.details['user_ids']:
            analytics.details['user_ids'].append(user.id)
            analytics.unique_users += 1
        analytics.save()
    except Exception as e:
        logger.error(f"Error updating dashboard analytics: {e}")

@login_required
@cache_page(60 * 5)  # Cache for 5 minutes
def dashboard_view(request):
    """Main dashboard view with role-specific content and caching."""
    start_time = timezone.now()
    
    # Log dashboard access
    log_dashboard_access(request.user, request)
    
    # Get user role
    role = get_user_role(request.user)
    
    # Calculate metrics if needed (async in production)
    refresh_metrics = request.GET.get('refresh', 'false').lower() == 'true'
    DashboardMetric.calculate_all_metrics(force_recalculate=refresh_metrics)
    
    # Get dashboard context
    context = get_dashboard_context(request.user, role)
    
    # Add performance data
    load_time = (timezone.now() - start_time).total_seconds()
    context['load_time'] = round(load_time * 1000, 2)  # Convert to milliseconds
    
    # Check for welcome message for first-time users
    if not request.session.get('dashboard_welcome_shown'):
        context['show_welcome'] = True
        request.session['dashboard_welcome_shown'] = True
    
    # Template selection based on role
    template_map = {
        'admin': 'dashboard/home.html',
        'officer': 'dashboard/home.html',
        'offender': 'dashboard/home.html',
        'judiciary': 'dashboard/home.html',
        'default': 'dashboard/home.html',
    }
    
    template_name = template_map.get(role, template_map['default'])
    
    return render(request, template_name, context)

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin-only dashboard view."""
    return dashboard_view(request)

@login_required
@user_passes_test(is_officer)
def officer_dashboard(request):
    """Officer-only dashboard view."""
    return dashboard_view(request)

@login_required
@user_passes_test(is_offender)
def offender_dashboard(request):
    """Offender-only dashboard view."""
    return dashboard_view(request)

@login_required
@user_passes_test(is_judiciary)
def judiciary_dashboard(request):
    """Judiciary-only dashboard view."""
    return dashboard_view(request)

@login_required
def widget_list(request):
    """Return available widgets for the current user."""
    widgets = DashboardWidget.objects.filter(is_active=True).order_by('order', 'name')
    visible_widgets = [w for w in widgets if w.is_visible_to_user(request.user)]
    data = [w.get_widget_config(user=request.user) for w in visible_widgets]
    return JsonResponse({'widgets': data})

@login_required
@require_http_methods(["POST"])
def toggle_widget(request, widget_id):
    """Toggle visibility for a widget in the user's layout."""
    widget = get_object_or_404(DashboardWidget, id=widget_id)
    layout, _ = DashboardLayout.objects.get_or_create(user=request.user)
    preference, _ = DashboardWidgetPreference.objects.get_or_create(
        layout=layout,
        widget=widget
    )
    preference.is_visible = not preference.is_visible
    preference.save()
    return JsonResponse({'widget_id': widget.id, 'is_visible': preference.is_visible})

def get_user_role(user):
    """Determine user role for dashboard display."""
    if user.is_superuser or (hasattr(user, 'role') and user.role == 'admin'):
        return 'admin'
    elif hasattr(user, 'role'):
        return user.role
    return 'default'

def get_dashboard_context(user, role=None):
    """Get comprehensive dashboard context based on user role."""
    if not role:
        role = get_user_role(user)
    
    # Common context for all roles
    context = {
        'user': user,
        'role': role,
        'current_time': timezone.now(),
        'today': timezone.now().date(),
        'current_year': timezone.now().year,
        'current_month': timezone.now().strftime('%B'),
    }
    
    # Role-specific context
    context_functions = {
        'admin': get_admin_dashboard_context,
        'officer': get_officer_dashboard_context,
        'offender': get_offender_dashboard_context,
        'judiciary': get_judiciary_dashboard_context,
    }
    
    context_function = context_functions.get(role, get_default_dashboard_context)
    context.update(context_function(user))
    
    # Add notifications
    context['notifications'] = get_user_notifications(user)
    context['unread_notification_count'] = Notification.get_unread_count(user)
    
    # Add recent activities
    context['recent_activities'] = get_recent_activities(user, limit=10)
    
    # Add dashboard layout
    context['dashboard_layout'] = get_user_dashboard_layout(user, role)
    
    # Add quick stats for widgets
    context['quick_stats'] = get_quick_stats(user, role)
    
    # Add system alerts if any
    context['system_alerts'] = get_system_alerts()
    
    return context

def get_admin_dashboard_context(user):
    """Get comprehensive admin dashboard context."""
    from django.db import connection
    
    # Basic statistics with caching
    cache_key = f"admin_dashboard_stats_{timezone.now().date()}"
    stats = cache.get(cache_key)
    
    if not stats:
        stats = {
            # Offender statistics
            'total_offenders': Offender.objects.count(),
            'active_offenders': Offender.objects.filter(is_active=True).count(),
            'inactive_offenders': Offender.objects.filter(is_active=False).count(),
            'new_offenders_today': Offender.objects.filter(
                date_created__date=timezone.now().date()
            ).count(),
            
            # Case statistics
            'total_cases': Case.objects.count(),
            'active_cases': Case.objects.filter(status='active').count(),
            'completed_cases': Case.objects.filter(status='completed').count(),
            'violated_cases': Case.objects.filter(status='violated').count(),
            
            # User statistics
            'total_officers': User.objects.filter(role='officer', is_active=True).count(),
            'total_admins': User.objects.filter(role='admin', is_active=True).count(),
            'total_offender_users': User.objects.filter(role='offender', is_active=True).count(),
            'active_sessions': 0,  # Would require session tracking
            
            # Risk distribution
            'risk_distribution': get_risk_distribution(),
            
            # Program statistics
            'total_programs': Program.objects.count(),
            'active_enrollments': Enrollment.objects.filter(status='active').count(),
            'completed_enrollments': Enrollment.objects.filter(status='completed').count(),
            
            # Dataset statistics
            'total_datasets': Dataset.objects.count(),
            'total_datapoints': Dataset.objects.aggregate(
                total=Sum('row_count')
            )['total'] or 0,
            
            # ML Model statistics
            'total_models': MLModel.objects.count(),
            'active_models': MLModel.objects.filter(is_active=True).count(),
            'total_predictions': Prediction.objects.count(),
            
            # Monitoring statistics
            'today_checkins': CheckIn.objects.filter(
                scheduled_date=timezone.now().date()
            ).count(),
            'overdue_checkins': CheckIn.objects.filter(
                scheduled_date__lt=timezone.now().date(),
                status='pending'
            ).count(),
            
            # Report statistics
            'total_reports': GeneratedReport.objects.count(),
            'scheduled_reports': ReportSchedule.objects.filter(status='active').count(),
        }
        
        # Calculate database size
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                stats['db_size_mb'] = round(cursor.fetchone()[0] / (1024 * 1024), 2)
        except:
            stats['db_size_mb'] = 0
        
        # Cache for 15 minutes
        cache.set(cache_key, stats, 60 * 15)
    
    # Recent data (not cached as heavily)
    recent_data = {
        'recent_offenders': Offender.objects.all().select_related(
            'user'
        ).order_by('-date_created')[:10],
        
        'recent_cases': Case.objects.all().select_related(
            'offender', 'probation_officer'
        ).order_by('-date_created')[:10],
        
        'recent_assessments': Assessment.objects.all().select_related(
            'offender', 'assessed_by'
        ).order_by('-assessment_date')[:10],
        
        'recent_datasets': Dataset.objects.all().order_by('-upload_date')[:5],
        
        'recent_models': MLModel.objects.all().order_by('-created_at')[:5],
        
        'recent_predictions': Prediction.objects.all().select_related(
            'model', 'offender'
        ).order_by('-prediction_time')[:10],
        
        'system_activities': ActivityLog.objects.all().select_related(
            'user'
        ).order_by('-created_at')[:20],
    }
    
    # Charts data
    charts_data = {
        'monthly_offender_trend': get_monthly_offender_trend(6),
        'case_status_distribution': get_case_status_distribution(),
        'risk_level_distribution': get_risk_distribution_chart(),
        'program_enrollment_trend': get_program_enrollment_trend(6),
        'compliance_rate_trend': get_compliance_rate_trend(6),
        'prediction_accuracy': get_prediction_accuracy_stats(),
    }
    
    # System health
    system_health = {
        'database_status': 'healthy',
        'cache_status': 'healthy',
        'storage_status': check_storage_status(),
        'background_tasks': check_background_tasks(),
        'last_backup': get_last_backup_time(),
    }
    
    return {
        'page_title': 'Administrator Dashboard',
        'page_subtitle': 'System Overview & Analytics',
        'dashboard_type': 'admin',
        
        **stats,
        **recent_data,
        'charts_data': charts_data,
        'system_health': system_health,
        
        # JSON data for JavaScript
        'risk_distribution_json': json.dumps(stats['risk_distribution']),
        'monthly_trend_json': json.dumps(charts_data['monthly_offender_trend']),
        
        # Quick actions
        'quick_actions': [
            {'title': 'System Settings', 'url': '/admin/', 'icon': 'bi-gear', 'color': 'primary', 'permission': 'admin'},
            {'title': 'User Management', 'url': '/accounts/users/', 'icon': 'bi-people', 'color': 'success', 'permission': 'admin'},
            {'title': 'Database Backup', 'url': '/admin/backup/', 'icon': 'bi-database', 'color': 'info', 'permission': 'admin'},
            {'title': 'System Logs', 'url': '/admin/logs/', 'icon': 'bi-clipboard-data', 'color': 'warning', 'permission': 'admin'},
            {'title': 'API Documentation', 'url': '/api/docs/', 'icon': 'bi-code-slash', 'color': 'dark', 'permission': 'admin'},
        ]
    }

def get_officer_dashboard_context(user):
    """Get comprehensive officer dashboard context."""
    # Get officer's cases and offenders
    my_cases = Case.objects.filter(
        probation_officer=user, 
        status='active'
    ).select_related('offender')
    
    my_offenders = Offender.objects.filter(
        cases__in=my_cases
    ).distinct().select_related('user')
    
    # Basic statistics
    stats = {
        'total_cases': my_cases.count(),
        'total_offenders': my_offenders.count(),
        
        'high_risk_cases': my_cases.filter(offender__risk_level='high').count(),
        'medium_risk_cases': my_cases.filter(offender__risk_level='medium').count(),
        'low_risk_cases': my_cases.filter(offender__risk_level='low').count(),
        
        'cases_ending_soon': my_cases.filter(
            sentence_end__range=[
                timezone.now().date(),
                timezone.now().date() + timedelta(days=30)
            ]
        ).count(),
        
        'overdue_assessments': Assessment.objects.filter(
            offender__in=my_offenders,
            assessment_date__lt=timezone.now().date()
        ).count(),
        
        'pending_checkins': CheckIn.objects.filter(
            offender__in=my_offenders,
            status='pending',
            scheduled_date__lte=timezone.now().date()
        ).count(),
        
        'completed_programs': Enrollment.objects.filter(
            offender__in=my_offenders,
            status='completed'
        ).count(),
    }
    
    # Recent and upcoming
    recent_data = {
        'recent_checkins': CheckIn.objects.filter(
            offender__in=my_offenders
        ).select_related('offender').order_by('-checkin_time')[:10],
        
        'recent_assessments': Assessment.objects.filter(
            offender__in=my_offenders
        ).select_related('offender').order_by('-assessment_date')[:10],
        
        'upcoming_checkins': CheckIn.objects.filter(
            offender__in=my_offenders,
            status='pending',
            scheduled_date__gte=timezone.now().date()
        ).select_related('offender').order_by('scheduled_date')[:10],
        
        'upcoming_assessments': Assessment.objects.filter(
            offender__in=my_offenders,
            assessment_date__gte=timezone.now().date()
        ).select_related('offender').order_by('assessment_date')[:10],
        
        'offender_progress': Enrollment.objects.filter(
            offender__in=my_offenders
        ).select_related('program', 'offender').order_by('-updated_at')[:10],
    }
    
    # Charts data
    charts_data = {
        'caseload_distribution': get_officer_caseload_distribution(user),
        'compliance_rate_by_offender': get_compliance_rate_by_offender(my_offenders),
        'risk_distribution': get_officer_risk_distribution(my_cases),
        'program_completion_rate': get_program_completion_rate(my_offenders),
    }
    
    # Alerts and warnings
    alerts = get_officer_alerts(user, my_cases, my_offenders)
    
    return {
        'page_title': 'Officer Dashboard',
        'page_subtitle': f'Caseload Management • {stats["total_cases"]} Active Cases',
        'dashboard_type': 'officer',
        
        **stats,
        **recent_data,
        'charts_data': charts_data,
        'alerts': alerts,
        
        'my_cases': my_cases,
        'my_offenders': my_offenders,
        
        # Quick actions
        'quick_actions': [
            {'title': 'New Assessment', 'url': '/offenders/assessment/new/', 'icon': 'bi-clipboard-check', 'color': 'primary'},
            {'title': 'Schedule Check-in', 'url': '/monitoring/checkins/schedule/', 'icon': 'bi-calendar-plus', 'color': 'success'},
            {'title': 'Add Offender', 'url': '/offenders/new/', 'icon': 'bi-person-plus', 'color': 'info'},
            {'title': 'Generate Report', 'url': '/reports/generate/', 'icon': 'bi-file-earmark-text', 'color': 'warning'},
            {'title': 'View High Risk', 'url': '/offenders/?risk=high', 'icon': 'bi-exclamation-triangle', 'color': 'danger'},
        ],
        
        # Today's schedule
        'todays_schedule': get_todays_schedule(user),
    }

def get_offender_dashboard_context(user):
    """Get comprehensive offender dashboard context."""
    try:
        offender = user.offender_profile
        active_cases = offender.cases.filter(status='active')
        active_case = active_cases.first() if active_cases.exists() else None
        
        # Basic information
        info = {
            'offender': offender,
            'active_case': active_case,
            'probation_officer': offender.probation_officer if hasattr(offender, 'probation_officer') else None,
            'current_risk_level': offender.risk_level,
            'supervision_level': offender.supervision_level if hasattr(offender, 'supervision_level') else 'Standard',
        }
        
        # Statistics
        stats = {
            'days_remaining': active_case.days_remaining() if active_case else 0,
            'total_checkins': CheckIn.objects.filter(offender=offender).count(),
            'on_time_checkins': CheckIn.objects.filter(
                offender=offender,
                status='completed',
                completed_date__lte=F('scheduled_date')
            ).count(),
            'total_programs': Enrollment.objects.filter(offender=offender).count(),
            'completed_programs': Enrollment.objects.filter(
                offender=offender,
                status='completed'
            ).count(),
            'current_programs': Enrollment.objects.filter(
                offender=offender,
                status='active'
            ).count(),
        }
        
        # Compliance metrics
        if stats['total_checkins'] > 0:
            stats['compliance_rate'] = round((stats['on_time_checkins'] / stats['total_checkins']) * 100, 1)
        else:
            stats['compliance_rate'] = 100.0
        
        # Recent and upcoming
        recent_data = {
            'recent_checkins': CheckIn.objects.filter(
                offender=offender
            ).order_by('-checkin_time')[:10],
            
            'recent_assessments': Assessment.objects.filter(
                offender=offender
            ).order_by('-assessment_date')[:5],
            
            'upcoming_checkins': CheckIn.objects.filter(
                offender=offender,
                status='pending',
                scheduled_date__gte=timezone.now().date()
            ).order_by('scheduled_date')[:10],
            
            'current_programs_list': Enrollment.objects.filter(
                offender=offender,
                status='active'
            ).select_related('program')[:5],
            
            'program_progress': Enrollment.objects.filter(
                offender=offender
            ).select_related('program', 'offender').order_by('-updated_at')[:5],
        }
        
        # Requirements and tasks
        requirements = get_offender_requirements(offender)
        
        # Progress charts
        charts_data = {
            'compliance_trend': get_offender_compliance_trend(offender, 6),
            'program_progress': get_offender_program_progress(offender),
            'risk_score_history': get_offender_risk_score_history(offender),
        }
        
        # Messages and communications
        messages = get_offender_messages(offender)
        
        return {
            'page_title': 'My Dashboard',
            'page_subtitle': f'Welcome back, {offender.first_name}',
            'dashboard_type': 'offender',
            
            **info,
            **stats,
            **recent_data,
            'charts_data': charts_data,
            'requirements': requirements,
            'messages': messages,
            
            # Quick actions
            'quick_actions': [
                {'title': 'Check In', 'url': '/monitoring/checkin/', 'icon': 'bi-check-circle', 'color': 'success'},
                {'title': 'View Progress', 'url': '/programs/my-progress/', 'icon': 'bi-graph-up', 'color': 'primary'},
                {'title': 'Message Officer', 'url': '/communications/new/', 'icon': 'bi-chat', 'color': 'info'},
                {'title': 'View Documents', 'url': '/documents/', 'icon': 'bi-file-text', 'color': 'warning'},
                {'title': 'Update Profile', 'url': '/accounts/profile/', 'icon': 'bi-person', 'color': 'dark'},
            ],
            
            # Rewards and incentives (if applicable)
            'rewards': get_offender_rewards(offender),
            
            # Important dates
            'important_dates': get_offender_important_dates(offender),
        }
        
    except AttributeError:
        # User doesn't have offender profile
        return {
            'page_title': 'My Dashboard',
            'page_subtitle': 'Welcome',
            'dashboard_type': 'offender',
            'error': 'Offender profile not found. Please contact your probation officer.',
        }

def get_judiciary_dashboard_context(user):
    """Get judiciary dashboard context."""
    # Cases awaiting judicial review
    pending_reviews = Case.objects.filter(
        status='awaiting_review'
    ).select_related('offender', 'probation_officer')[:10]
    
    # Upcoming hearings
    upcoming_hearings = get_upcoming_hearings()  # This would come from a hearings model
    
    # Case statistics for judge
    stats = {
        'total_cases_reviewed': Case.objects.filter(
            reviewed_by=user
        ).count(),
        'cases_awaiting_review': Case.objects.filter(
            status='awaiting_review'
        ).count(),
        'upcoming_hearings': len(upcoming_hearings),
        'average_case_duration': get_average_case_duration(),
    }
    
    return {
        'page_title': 'Judicial Dashboard',
        'page_subtitle': 'Case Management & Reviews',
        'dashboard_type': 'judiciary',
        
        'pending_reviews': pending_reviews,
        'upcoming_hearings': upcoming_hearings,
        **stats,
        
        # Quick actions
        'quick_actions': [
            {'title': 'Review Cases', 'url': '/cases/review/', 'icon': 'bi-gavel', 'color': 'primary'},
            {'title': 'Schedule Hearing', 'url': '/hearings/schedule/', 'icon': 'bi-calendar-event', 'color': 'success'},
            {'title': 'View Reports', 'url': '/reports/judicial/', 'icon': 'bi-file-earmark-text', 'color': 'info'},
            {'title': 'Case Search', 'url': '/cases/search/', 'icon': 'bi-search', 'color': 'warning'},
        ],
    }

def get_default_dashboard_context(user):
    """Default dashboard context for other roles."""
    return {
        'page_title': 'Dashboard',
        'page_subtitle': 'Welcome to Probation Management System',
        'dashboard_type': 'default',
        'message': 'Your role-specific dashboard is being prepared.',
        'quick_actions': [
            {'title': 'View Profile', 'url': '/accounts/profile/', 'icon': 'bi-person', 'color': 'primary'},
            {'title': 'System Guide', 'url': '/help/', 'icon': 'bi-question-circle', 'color': 'info'},
            {'title': 'Contact Support', 'url': '/support/', 'icon': 'bi-headset', 'color': 'success'},
        ]
    }

# API Views
@login_required
@require_http_methods(["GET"])
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics with caching."""
    cache_key = f"dashboard_stats_{request.user.id}_{timezone.now().date()}"
    cached_data = cache.get(cache_key)
    
    if cached_data and not request.GET.get('refresh'):
        return JsonResponse(cached_data)
    
    user = request.user
    role = get_user_role(user)
    
    data = {
        'user': {
            'id': user.id,
            'username': user.username,
            'role': role,
            'full_name': user.get_full_name(),
        },
        'timestamp': timezone.now().isoformat(),
        'role': role,
    }
    
    # Get role-specific stats
    stats_functions = {
        'admin': get_admin_stats_data,
        'officer': get_officer_stats_data,
        'offender': get_offender_stats_data,
        'judiciary': get_judiciary_stats_data,
    }
    
    stats_function = stats_functions.get(role, get_default_stats_data)
    data.update(stats_function(user))
    
    # Add notifications count
    data['notifications'] = {
        'unread_count': Notification.get_unread_count(user),
        'total_count': Notification.objects.filter(user=user).count(),
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, data, 60 * 5)
    
    return JsonResponse(data)

def get_admin_stats_data(user):
    """Get admin statistics data for API."""
    return {
        'offenders': {
            'total': Offender.objects.count(),
            'active': Offender.objects.filter(is_active=True).count(),
            'new_today': Offender.objects.filter(
                date_created__date=timezone.now().date()
            ).count(),
        },
        'cases': {
            'total': Case.objects.count(),
            'active': Case.objects.filter(status='active').count(),
            'completed': Case.objects.filter(status='completed').count(),
        },
        'users': {
            'total': User.objects.count(),
            'officers': User.objects.filter(role='officer').count(),
            'active_today': 0,  # Would require session tracking
        },
        'system': {
            'datasets': Dataset.objects.count(),
            'models': MLModel.objects.count(),
            'predictions': Prediction.objects.count(),
        }
    }

def get_officer_stats_data(user):
    """Get officer statistics data for API."""
    my_cases = Case.objects.filter(probation_officer=user, status='active')
    my_offenders = Offender.objects.filter(cases__in=my_cases).distinct()
    
    return {
        'caseload': {
            'total_cases': my_cases.count(),
            'total_offenders': my_offenders.count(),
            'high_risk': my_cases.filter(offender__risk_level='high').count(),
        },
        'tasks': {
            'pending_checkins': CheckIn.objects.filter(
                offender__in=my_offenders,
                status='pending',
                scheduled_date__lte=timezone.now().date()
            ).count(),
            'overdue_assessments': Assessment.objects.filter(
                offender__in=my_offenders,
                assessment_date__lt=timezone.now().date()
            ).count(),
            'upcoming_endings': my_cases.filter(
                sentence_end__range=[
                    timezone.now().date(),
                    timezone.now().date() + timedelta(days=30)
                ]
            ).count(),
        },
        'compliance': {
            'total_checkins': CheckIn.objects.filter(offender__in=my_offenders).count(),
            'on_time_checkins': CheckIn.objects.filter(
                offender__in=my_offenders,
                status='completed',
                completed_date__lte=F('scheduled_date')
            ).count(),
        }
    }

def get_offender_stats_data(user):
    """Get offender statistics data for API."""
    try:
        offender = user.offender_profile
        active_cases = offender.cases.filter(status='active')
        
        return {
            'case': {
                'active': active_cases.exists(),
                'days_remaining': active_cases.first().days_remaining() if active_cases.exists() else 0,
                'officer': offender.probation_officer.get_full_name() if hasattr(offender, 'probation_officer') else 'Not Assigned',
            },
            'compliance': {
                'rate': get_offender_compliance_rate(offender),
                'next_checkin': get_next_checkin(offender),
                'total_checkins': CheckIn.objects.filter(offender=offender).count(),
            },
            'programs': {
                'total': Enrollment.objects.filter(offender=offender).count(),
                'active': Enrollment.objects.filter(offender=offender, status='active').count(),
                'completed': Enrollment.objects.filter(offender=offender, status='completed').count(),
            }
        }
    except:
        return {}

def get_judiciary_stats_data(user):
    """Get judiciary statistics data for API."""
    return {
        'cases': {
            'total': Case.objects.count(),
            'active': Case.objects.filter(status='active').count(),
            'completed': Case.objects.filter(status='completed').count(),
            'violated': Case.objects.filter(status='violated').count(),
        }
    }

def get_default_stats_data(user):
    """Get default statistics data for API."""
    return {
        'offenders': {
            'total': Offender.objects.count(),
            'active': Offender.objects.filter(is_active=True).count(),
        },
        'cases': {
            'total': Case.objects.count(),
            'active': Case.objects.filter(status='active').count(),
        }
    }

@login_required
@require_http_methods(["GET"])
def dashboard_chart_data(request, chart_type):
    """API endpoint for chart data with role-specific charts."""
    user = request.user
    role = get_user_role(user)
    
    # Chart data providers
    chart_providers = {
        'risk_distribution': get_risk_distribution_chart,
        'case_status': get_case_status_distribution_chart,
        'monthly_offenders': get_monthly_offender_chart,
        'officer_caseload': lambda: get_officer_caseload_chart(user) if role == 'officer' else {},
        'offender_compliance': lambda: get_offender_compliance_chart(user) if role == 'offender' else {},
        'program_enrollment': get_program_enrollment_chart,
        'prediction_accuracy': get_prediction_accuracy_chart,
    }
    
    provider = chart_providers.get(chart_type)
    if provider:
        data = provider()
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)

@login_required
@require_http_methods(["GET", "POST"])
def notifications_api(request):
    """Enhanced notifications API with pagination and filtering."""
    if request.method == 'GET':
        # Get parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        category = request.GET.get('category', '')
        
        # Build queryset
        queryset = Notification.objects.filter(user=request.user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        if category:
            queryset = queryset.filter(category=category)
        
        # Get total count
        total_count = queryset.count()
        
        # Paginate
        start = (page - 1) * limit
        end = start + limit
        notifications = queryset.order_by('-created_at')[start:end]
        
        data = {
            'notifications': [
                {
                    'id': n.id,
                    'title': n.title,
                    'message': n.message,
                    'type': n.notification_type,
                    'category': n.category,
                    'priority': n.priority,
                    'created_at': n.created_at.isoformat(),
                    'read_at': n.read_at.isoformat() if n.read_at else None,
                    'is_read': n.is_read,
                    'action_url': n.action_url,
                    'action_text': n.action_text,
                    'metadata': n.metadata,
                }
                for n in notifications
            ],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit,
            },
            'summary': {
                'unread_count': Notification.get_unread_count(request.user),
                'total_count': total_count,
            }
        }
        
        return JsonResponse(data)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    notification = Notification.objects.get(id=notification_id, user=request.user)
                    notification.mark_as_read()
                    return JsonResponse({'success': True, 'message': 'Notification marked as read'})
            
            elif action == 'mark_all_read':
                updated = Notification.objects.filter(
                    user=request.user, 
                    is_read=False
                ).update(is_read=True, read_at=timezone.now())
                return JsonResponse({'success': True, 'message': f'{updated} notifications marked as read'})
            
            elif action == 'dismiss':
                notification_id = data.get('notification_id')
                if notification_id:
                    notification = Notification.objects.get(id=notification_id, user=request.user)
                    notification.mark_as_dismissed()
                    return JsonResponse({'success': True, 'message': 'Notification dismissed'})
            
            elif action == 'archive':
                notification_id = data.get('notification_id')
                if notification_id:
                    notification = Notification.objects.get(id=notification_id, user=request.user)
                    notification.archive()
                    return JsonResponse({'success': True, 'message': 'Notification archived'})
            
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
        except Notification.DoesNotExist:
            return JsonResponse({'error': 'Notification not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["GET"])
def activity_feed_api(request):
    """Activity feed API with filtering options."""
    # Get parameters
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    module = request.GET.get('module', '')
    action = request.GET.get('action', '')
    days = int(request.GET.get('days', 7))
    
    # Build queryset
    since_date = timezone.now() - timedelta(days=days)
    queryset = ActivityLog.objects.filter(
        user=request.user,
        created_at__gte=since_date
    )
    
    if module:
        queryset = queryset.filter(module=module)
    
    if action:
        queryset = queryset.filter(action=action)
    
    # Get total count
    total_count = queryset.count()
    
    # Paginate
    start = (page - 1) * limit
    end = start + limit
    activities = queryset.select_related('user').order_by('-created_at')[start:end]
    
    data = {
        'activities': [
            {
                'id': a.id,
                'action': a.get_action_display(),
                'module': a.get_module_display(),
                'severity': a.severity,
                'description': a.description,
                'created_at': a.created_at.isoformat(),
                'details': a.details,
                'icon': get_activity_icon(a.action, a.module),
                'color': get_severity_color(a.severity),
            }
            for a in activities
        ],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'pages': (total_count + limit - 1) // limit,
        },
        'summary': {
            'total_activities': total_count,
            'period_days': days,
        }
    }
    
    return JsonResponse(data)

@login_required
def dashboard_settings_view(request):
    """Dashboard settings view with widget customization."""
    layout, created = DashboardLayout.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            # Update layout settings
            layout.theme = request.POST.get('theme', 'light')
            layout.refresh_interval = int(request.POST.get('refresh_interval', 300))
            layout.show_animations = request.POST.get('show_animations') == 'on'
            layout.compact_mode = request.POST.get('compact_mode') == 'on'
            
            # Update widget preferences
            widget_data = request.POST.get('widgets')
            if widget_data:
                widgets = json.loads(widget_data)
                for widget_config in widgets:
                    widget_id = widget_config.get('id')
                    widget = DashboardWidget.objects.get(id=widget_id)
                    
                    preference, _ = DashboardWidgetPreference.objects.get_or_create(
                        layout=layout,
                        widget=widget
                    )
                    
                    preference.is_visible = widget_config.get('visible', True)
                    preference.order = widget_config.get('order', 0)
                    preference.settings = widget_config.get('settings', {})
                    preference.save()
            
            layout.save()
            
            messages.success(request, 'Dashboard settings updated successfully!')
            return redirect('dashboard:settings')
            
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    # Get available widgets for user's role
    role = get_user_role(request.user)
    # `roles` is stored as comma-separated text (SQLite-compatible), so use
    # model-level visibility logic instead of unsupported DB lookups like `__len`.
    available_widgets_qs = DashboardWidget.objects.filter(is_active=True).order_by('order')
    available_widgets = [w for w in available_widgets_qs if w.is_visible_to_user(request.user)]
    
    # Get user's widget preferences
    widget_preferences = {
        pref.widget_id: pref
        for pref in layout.widgetpreferences.select_related('widget').all()
    }
    
    context = {
        'page_title': 'Dashboard Settings',
        'page_subtitle': 'Manage your dashboard preferences',
        'layout': layout,
        'available_widgets': available_widgets,
        'widget_preferences': widget_preferences,
        'themes': [
            {'value': 'light', 'label': 'Light', 'icon': 'bi-sun'},
            {'value': 'dark', 'label': 'Dark', 'icon': 'bi-moon'},
            {'value': 'auto', 'label': 'Auto', 'icon': 'bi-circle-half'},
        ],
        'refresh_intervals': [
            {'value': 60, 'label': '1 minute'},
            {'value': 300, 'label': '5 minutes'},
            {'value': 900, 'label': '15 minutes'},
            {'value': 1800, 'label': '30 minutes'},
            {'value': 3600, 'label': '1 hour'},
            {'value': 0, 'label': 'Never'},
        ]
    }
    
    return render(request, 'dashboard/settings.html', context)

@login_required
@require_http_methods(["POST"])
def reset_dashboard_layout(request):
    """Reset dashboard layout to defaults."""
    try:
        layout = DashboardLayout.objects.get(user=request.user)
        role = get_user_role(request.user)
        layout.reset_to_default(role)
        
        messages.success(request, 'Dashboard layout reset to defaults!')
        return redirect('dashboard:settings')
    except Exception as e:
        messages.error(request, f'Error resetting layout: {str(e)}')
        return redirect('dashboard:settings')

# Helper functions
def get_risk_distribution():
    """Get risk level distribution."""
    return {
        'high': Offender.objects.filter(risk_level='high').count(),
        'medium': Offender.objects.filter(risk_level='medium').count(),
        'low': Offender.objects.filter(risk_level='low').count(),
        'unknown': Offender.objects.filter(risk_level='', risk_level__isnull=True).count(),
    }

def get_monthly_offender_trend(months=6):
    """Get monthly offender registration trend."""
    from django.db.models.functions import TruncMonth
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30*months)
    
    monthly_data = (
        Offender.objects
        .filter(date_created__range=[start_date, end_date])
        .annotate(month=TruncMonth('date_created'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    
    # Format for chart
    labels = []
    data = []
    
    for item in monthly_data:
        month_name = item['month'].strftime('%b %Y')
        labels.append(month_name)
        data.append(item['count'])
    
    return {'labels': labels, 'data': data}

def get_case_status_distribution():
    """Get case status distribution."""
    statuses = ['active', 'completed', 'violated', 'transferred', 'closed']
    distribution = {}
    
    for status in statuses:
        distribution[status] = Case.objects.filter(status=status).count()
    
    return distribution

def get_risk_distribution_chart():
    """Return chart-ready risk distribution data."""
    dist = get_risk_distribution()
    return {
        'labels': ['High Risk', 'Medium Risk', 'Low Risk', 'Unknown'],
        'data': [
            dist.get('high', 0),
            dist.get('medium', 0),
            dist.get('low', 0),
            dist.get('unknown', 0),
        ],
    }

def get_case_status_distribution_chart():
    """Return chart-ready case status distribution data."""
    dist = get_case_status_distribution()
    return {
        'labels': ['Active', 'Completed', 'Violated', 'Transferred', 'Closed'],
        'data': [
            dist.get('active', 0),
            dist.get('completed', 0),
            dist.get('violated', 0),
            dist.get('transferred', 0),
            dist.get('closed', 0),
        ],
    }

def get_monthly_offender_chart(months=6):
    """Return chart-ready monthly offender trend data."""
    return get_monthly_offender_trend(months)

def get_program_enrollment_trend(months=6):
    """Return monthly program enrollment counts."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30 * months)
    monthly_data = (
        Enrollment.objects
        .filter(enrollment_date__range=[start_date, end_date])
        .annotate(month=TruncMonth('enrollment_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    labels = []
    data = []
    for item in monthly_data:
        labels.append(item['month'].strftime('%b %Y'))
        data.append(item['count'])
    return {'labels': labels, 'data': data}

def get_program_enrollment_chart():
    """Return chart-ready program enrollment status data."""
    statuses = ['pending', 'active', 'completed', 'dropped_out', 'transferred', 'suspended']
    labels = [s.replace('_', ' ').title() for s in statuses]
    data = [Enrollment.objects.filter(status=s).count() for s in statuses]
    return {'labels': labels, 'data': data}

def get_compliance_rate_trend(months=6):
    """Return monthly compliance rate based on check-ins."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30 * months)
    monthly = (
        CheckIn.objects
        .filter(scheduled_date__range=[start_date, end_date])
        .annotate(month=TruncMonth('scheduled_date'))
        .values('month')
        .annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
        )
        .order_by('month')
    )
    labels = []
    data = []
    for item in monthly:
        labels.append(item['month'].strftime('%b %Y'))
        total = item['total'] or 0
        completed = item['completed'] or 0
        rate = round((completed / total) * 100, 1) if total else 0.0
        data.append(rate)
    return {'labels': labels, 'data': data}

def get_prediction_accuracy_stats():
    """Return basic prediction accuracy stats."""
    total = Prediction.objects.count()
    correct = Prediction.objects.filter(is_correct=True).count()
    incorrect = Prediction.objects.filter(is_correct=False).count()
    accuracy = round((correct / total) * 100, 1) if total else 0.0
    return {
        'total': total,
        'correct': correct,
        'incorrect': incorrect,
        'accuracy': accuracy,
    }

def get_prediction_accuracy_chart():
    """Return chart-ready prediction accuracy data."""
    stats = get_prediction_accuracy_stats()
    unknown = max(stats['total'] - stats['correct'] - stats['incorrect'], 0)
    return {
        'labels': ['Correct', 'Incorrect', 'Unknown'],
        'data': [stats['correct'], stats['incorrect'], unknown],
    }

def get_officer_caseload_distribution(user):
    """Return case status distribution for an officer."""
    statuses = ['active', 'completed', 'violated', 'transferred']
    labels = [s.title() for s in statuses]
    data = [
        Case.objects.filter(probation_officer=user, status=s).count()
        for s in statuses
    ]
    return {'labels': labels, 'data': data}

def get_officer_caseload_chart(user):
    """Return chart-ready officer caseload data."""
    return get_officer_caseload_distribution(user)

def get_officer_risk_distribution(my_cases):
    """Return risk distribution for cases in an officer's caseload."""
    offenders = Offender.objects.filter(cases__in=my_cases).distinct()
    return {
        'high': offenders.filter(risk_level='high').count(),
        'medium': offenders.filter(risk_level='medium').count(),
        'low': offenders.filter(risk_level='low').count(),
        'unknown': offenders.filter(risk_level='', risk_level__isnull=True).count(),
    }

def get_compliance_rate_by_offender(my_offenders):
    """Return compliance rate per offender for charting."""
    labels = []
    data = []
    for offender in my_offenders:
        labels.append(str(offender))
        total = CheckIn.objects.filter(offender=offender).count()
        completed = CheckIn.objects.filter(offender=offender, status='completed').count()
        data.append(round((completed / total) * 100, 1) if total else 0.0)
    return {'labels': labels, 'data': data}

def get_program_completion_rate(my_offenders):
    """Return overall program completion rate for offenders."""
    total = Enrollment.objects.filter(offender__in=my_offenders).count()
    completed = Enrollment.objects.filter(
        offender__in=my_offenders,
        status='completed'
    ).count()
    return round((completed / total) * 100, 1) if total else 0.0

def get_todays_schedule(user):
    """Return today's check-ins for a probation officer."""
    today = timezone.now().date()
    return CheckIn.objects.filter(
        probation_officer=user,
        scheduled_date__date=today
    ).select_related('offender').order_by('scheduled_date')

def get_officer_alerts(user, my_cases, my_offenders):
    """Return alerts for officer dashboard."""
    alerts = []
    overdue_checkins = CheckIn.objects.filter(
        probation_officer=user,
        status='scheduled',
        scheduled_date__lt=timezone.now()
    ).count()
    if overdue_checkins:
        alerts.append({
            'type': 'warning',
            'message': f'{overdue_checkins} overdue check-ins',
        })
    return alerts

def get_offender_compliance_rate(offender):
    """Return overall compliance rate for an offender."""
    total = CheckIn.objects.filter(offender=offender).count()
    completed = CheckIn.objects.filter(offender=offender, status='completed').count()
    return round((completed / total) * 100, 1) if total else 0.0

def get_next_checkin(offender):
    """Return next scheduled check-in for an offender."""
    upcoming = CheckIn.objects.filter(
        offender=offender,
        scheduled_date__gte=timezone.now()
    ).order_by('scheduled_date').first()
    return upcoming.scheduled_date if upcoming else None

def get_offender_compliance_trend(offender, months=6):
    """Return monthly compliance trend for an offender."""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30 * months)
    monthly = (
        CheckIn.objects
        .filter(offender=offender, scheduled_date__range=[start_date, end_date])
        .annotate(month=TruncMonth('scheduled_date'))
        .values('month')
        .annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
        )
        .order_by('month')
    )
    labels = []
    data = []
    for item in monthly:
        labels.append(item['month'].strftime('%b %Y'))
        total = item['total'] or 0
        completed = item['completed'] or 0
        data.append(round((completed / total) * 100, 1) if total else 0.0)
    return {'labels': labels, 'data': data}

def get_offender_compliance_chart(user):
    """Return chart-ready compliance data for an offender user."""
    try:
        offender = user.offender_profile
    except Exception:
        return {'labels': [], 'data': []}
    return get_offender_compliance_trend(offender, 6)

def check_storage_status():
    """Return a basic storage status indicator."""
    return 'healthy'

def check_background_tasks():
    """Return a basic background task status indicator."""
    return 'healthy'

def get_last_backup_time():
    """Return last backup time if available."""
    return None

def get_admin_quick_stats(user):
    """Return quick stats for admin dashboard widgets."""
    total_users = User.objects.count()
    return {
        'total_users': total_users,
        'user_trend': 'stable',
        'db_size_mb': 0,
        'api_requests': 0,
        'api_trend': 'stable',
    }

def get_officer_quick_stats(user):
    """Return quick stats for officer dashboard widgets."""
    my_cases = Case.objects.filter(probation_officer=user)
    my_offenders = Offender.objects.filter(cases__in=my_cases).distinct()
    total_checkins = CheckIn.objects.filter(offender__in=my_offenders).count()
    completed_checkins = CheckIn.objects.filter(
        offender__in=my_offenders,
        status='completed'
    ).count()
    compliance_rate = round((completed_checkins / total_checkins) * 100, 1) if total_checkins else 0.0
    return {
        'total_offenders': my_offenders.count(),
        'active_cases': my_cases.filter(status='active').count(),
        'high_risk': my_offenders.filter(risk_level='high').count(),
        'compliance_rate': compliance_rate,
    }

def get_offender_quick_stats(user):
    """Return quick stats for offender dashboard widgets."""
    try:
        offender = user.offender_profile
    except Exception:
        return get_default_quick_stats(user)
    total_checkins = CheckIn.objects.filter(offender=offender).count()
    completed_checkins = CheckIn.objects.filter(offender=offender, status='completed').count()
    compliance_rate = round((completed_checkins / total_checkins) * 100, 1) if total_checkins else 0.0
    return {
        'total_offenders': 1,
        'active_cases': offender.cases.filter(status='active').count(),
        'high_risk': 1 if offender.risk_level == 'high' else 0,
        'compliance_rate': compliance_rate,
    }

def get_default_quick_stats(user):
    """Return default quick stats."""
    return {
        'total_offenders': 0,
        'active_cases': 0,
        'high_risk': 0,
        'compliance_rate': 0,
    }

def get_user_notifications(user, limit=10):
    """Get user notifications."""
    return Notification.objects.filter(
        user=user,
        is_dismissed=False,
        valid_until__gte=timezone.now(),
        valid_from__lte=timezone.now()
    ).order_by('-priority', '-created_at')[:limit]

def get_recent_activities(user, limit=10):
    """Get recent user activities."""
    return ActivityLog.objects.filter(
        user=user
    ).select_related('user').order_by('-created_at')[:limit]

def get_user_dashboard_layout(user, role):
    """Get or create user dashboard layout."""
    layout, created = DashboardLayout.objects.get_or_create(user=user)
    
    if created:
        layout.reset_to_default(role)
    
    return layout

def get_quick_stats(user, role):
    """Get quick statistics for dashboard widgets."""
    cache_key = f"quick_stats_{user.id}_{role}_{timezone.now().date()}"
    stats = cache.get(cache_key)
    
    if not stats:
        stats_functions = {
            'admin': get_admin_quick_stats,
            'officer': get_officer_quick_stats,
            'offender': get_offender_quick_stats,
        }
        
        stats_function = stats_functions.get(role, get_default_quick_stats)
        stats = stats_function(user)
        
        # Cache for 10 minutes
        cache.set(cache_key, stats, 60 * 10)
    
    return stats

def get_system_alerts():
    """Get system alerts for dashboard."""
    alerts = []
    
    # Check for overdue metrics calculation
    last_metric = DashboardMetric.objects.order_by('-calculated_at').first()
    if last_metric and (timezone.now() - last_metric.calculated_at).total_seconds() > 3600:
        alerts.append({
            'type': 'warning',
            'message': 'Dashboard metrics haven\'t been updated in over an hour',
            'action': '/admin/dashboard/update-metrics/',
        })
    
    # Check for system warnings
    # Add more checks as needed
    
    return alerts

def get_activity_icon(action, module):
    """Get Bootstrap icon for activity."""
    icon_map = {
        'login': 'bi-box-arrow-in-right',
        'logout': 'bi-box-arrow-right',
        'create': 'bi-plus-circle',
        'update': 'bi-pencil',
        'delete': 'bi-trash',
        'view': 'bi-eye',
        'download': 'bi-download',
        'upload': 'bi-upload',
        'train': 'bi-cpu',
        'predict': 'bi-graph-up',
        'export': 'bi-file-arrow-down',
        'import': 'bi-file-arrow-up',
    }
    
    # Default icons by module
    default_icons = {
        'offenders': 'bi-people',
        'cases': 'bi-folder',
        'assessments': 'bi-clipboard-check',
        'datasets': 'bi-database',
        'ml_models': 'bi-cpu',
        'monitoring': 'bi-calendar-check',
        'programs': 'bi-mortarboard',
        'reports': 'bi-file-earmark-bar-graph',
        'dashboard': 'bi-speedometer2',
        'system': 'bi-gear',
        'accounts': 'bi-person',
    }
    
    return icon_map.get(action, default_icons.get(module, 'bi-circle'))

def get_severity_color(severity):
    """Get Bootstrap color class for severity."""
    color_map = {
        'info': 'primary',
        'low': 'success',
        'medium': 'warning',
        'high': 'danger',
        'critical': 'dark',
    }
    return color_map.get(severity, 'secondary')

# Error handling
def dashboard_error_view(request, exception=None):
    """Custom error view for dashboard."""
    logger.error(f"Dashboard error: {exception}")
    
    context = {
        'page_title': 'Dashboard Error',
        'error_message': 'An error occurred while loading the dashboard.',
        'error_details': str(exception) if exception else 'Unknown error',
    }
    
    return render(request, 'dashboard/error.html', context, status=500)

# Health check endpoint (for monitoring)
@csrf_exempt
def dashboard_health_check(request):
    """Health check endpoint for dashboard."""
    health = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'components': {
            'database': 'healthy',
            'cache': 'healthy',
            'metrics': 'healthy',
        }
    }
    
    try:
        # Check database
        User.objects.count()
        health['components']['database'] = 'healthy'
    except:
        health['components']['database'] = 'unhealthy'
        health['status'] = 'unhealthy'
    
    try:
        # Check cache
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['components']['cache'] = 'healthy'
        else:
            health['components']['cache'] = 'unhealthy'
            health['status'] = 'unhealthy'
    except:
        health['components']['cache'] = 'unhealthy'
        health['status'] = 'unhealthy'
    
    try:
        # Check metrics
        DashboardMetric.objects.count()
        health['components']['metrics'] = 'healthy'
    except:
        health['components']['metrics'] = 'unhealthy'
        health['status'] = 'unhealthy'
    
    return JsonResponse(health)

# Export functionality
@login_required
@require_http_methods(["GET"])
def export_dashboard_data(request, format='json'):
    """Export dashboard data in various formats."""
    user = request.user
    role = get_user_role(user)
    
    data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'role': role,
        },
        'timestamp': timezone.now().isoformat(),
        'dashboard_data': get_dashboard_context(user, role),
    }
    
    if format == 'json':
        response = JsonResponse(data, json_dumps_params={'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="dashboard_export_{timezone.now().date()}.json"'
        return response
    elif format == 'csv':
        # Implement CSV export
        pass
    
    return JsonResponse({'error': 'Unsupported format'}, status=400)
