"""
Views for accounts app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .forms import LoginForm, CustomUserCreationForm
from .models import User
from .permissions import (
    admin_required, authenticated_required, admin_required,
    user_can_manage_users
)
from offenders.models import Case, Offender

def login_view(request):
    """
    Handle user login.
    """
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect based on user role
                return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'title': 'Login'
    }
    return render(request, 'accounts/login.html', context)

def logout_view(request):
    """
    Handle user logout.
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'You have been logged out successfully.')
    else:
        messages.info(request, 'You were not logged in.')
    
    return redirect('accounts:login')

@login_required
def dashboard_view(request):
    """
    Main dashboard view with role-specific content.
    """
    user = request.user
    now = timezone.now()
    
    # Base context for all users
    context = {
        'user': user,
        'role': user.role,
        'now': now,
        'title': 'Dashboard'
    }
    
    # Role-specific context
    if user.is_admin():
        # Admin dashboard data
        total_users = User.objects.count()
        total_officers = User.objects.filter(role=User.Role.OFFICER).count()
        total_offenders = User.objects.filter(role=User.Role.OFFENDER).count()
        
        context.update({
            'total_users': total_users,
            'total_officers': total_officers,
            'total_offenders': total_offenders,
            'stats': {
                'active_cases': 24,
                'compliance_rate': 92,
                'risk_reduction': 15,
                'ai_predictions': 8,
            }
        })
    
    elif user.is_officer():
        # Officer dashboard data
        context.update({
            'active_cases': 12,
            'pending_tasks': 3,
            'upcoming_checkins': 5,
            'cases': [
                {'name': 'John Doe', 'case_id': 'CAS-001', 'risk': 'high', 'next_checkin': 'Tomorrow', 'status': 'active'},
                {'name': 'Jane Smith', 'case_id': 'CAS-002', 'risk': 'low', 'next_checkin': 'In 3 days', 'status': 'compliant'},
                {'name': 'Robert Kim', 'case_id': 'CAS-003', 'risk': 'medium', 'next_checkin': 'Today', 'status': 'warning'},
            ],
            'tasks': [
                {'title': 'Case Review', 'time': '10:00 AM', 'description': 'Review CAS-001 progress'},
                {'title': 'Check-in', 'time': '2:00 PM', 'description': 'Monthly check-in with CAS-002'},
                {'title': 'Report Submission', 'time': '4:00 PM', 'description': 'Submit weekly report'},
            ]
        })
    
    elif user.is_offender():
        # Offender dashboard data
        context.update({
            'program_completion': 65,
            'compliance_score': 88,
            'officer_name': 'John Kamau',
            'next_checkin': 'Tomorrow',
            'current_program': 'Vocational Training',
            'tasks': [
                {'title': 'Daily check-in report', 'completed': False},
                {'title': 'Complete counseling session', 'completed': True},
                {'title': 'Submit progress report', 'completed': False},
                {'title': 'Attend vocational class', 'completed': True},
            ],
            'progress': {
                'education': 75,
                'counseling': 60,
                'community_service': 45,
                'job_training': 80,
            }
        })
    
    return render(request, 'dashboard/dashboard.html', context)

def register_view(request):
    """
    Handle user registration (admin only in production).
    In development/demo, this allows self-registration.
    """
    if request.user.is_authenticated:
        messages.info(request, 'You are already logged in.')
        return redirect('accounts:dashboard')
    
    # In production, only admins should be able to register users
    # For now, we allow self-registration for demo purposes
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to the system.')
            
            # Log the registration
            print(f"New user registered: {user.username} ({user.role})")
            
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Register'
    }
    return render(request, 'accounts/register.html', context)

def profile_view(request):
    """
    View and edit user profile.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to view your profile.')
        return redirect('accounts:login')
    
    user = request.user
    
    if request.method == 'POST':
        # Handle profile updates
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email:
            user.email = email
        if phone:
            user.phone = phone
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:profile')
    
    context = {
        'user': user,
        'title': 'My Profile'
    }
    return render(request, 'accounts/profile.html', context)
@login_required
def settings_view(request):
    """
    User settings page.
    """
    user = request.user
    
    if request.method == 'POST':
        # Handle settings updates
        email_notifications = 'email_notifications' in request.POST
        push_notifications = 'push_notifications' in request.POST
        language = request.POST.get('language', 'en')
        timezone = request.POST.get('timezone', 'UTC')
        
        # In a real application, you would save these to a UserSettings model
        # For now, we'll just show a success message
        messages.success(request, 'Settings updated successfully!')
        return redirect('accounts:settings')
    
    context = {
        'user': user,
        'title': 'Settings',
        'languages': [
            {'code': 'en', 'name': 'English'},
            {'code': 'sw', 'name': 'Swahili'},
            {'code': 'fr', 'name': 'French'},
        ],
        'timezones': [
            'UTC',
            'Africa/Nairobi',
            'Africa/Johannesburg',
            'America/New_York',
            'Europe/London',
        ]
    }
    return render(request, 'accounts/settings.html', context)
@login_required
def change_password_view(request):
    """
    Handle password change.
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('accounts:change_password')
        
        # Validate new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
            return redirect('accounts:change_password')
        
        # Validate password strength (simple check)
        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('accounts:change_password')
        
        # Set new password
        request.user.set_password(new_password1)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('accounts:profile')
    
    context = {
        'title': 'Change Password'
    }
    return render(request, 'accounts/change_password.html', context)

def users_list_view(request):
    """
    List all users (admin only).
    """
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('accounts:dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    
    # Filter by role if provided
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Search by username or email
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    context = {
        'users': users,
        'role_filter': role_filter,
        'search_query': search_query,
        'role_choices': User.Role.choices,
        'title': 'User Management'
    }
    return render(request, 'accounts/users_list.html', context)

def create_user_view(request):
    """
    Create new user (admin only).
    """
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('accounts:users_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial = {}
        requested_role = request.GET.get("role")
        if requested_role in {r[0] for r in User.Role.choices}:
            initial["role"] = requested_role
        form = CustomUserCreationForm(initial=initial)
    
    context = {
        'form': form,
        'title': 'Create New User'
    }
    return render(request, 'accounts/create_user.html', context)

def user_detail_view(request, user_id):
    """
    View and edit user details (admin only).
    """
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('accounts:dashboard')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('accounts:users_list')
    
    if request.method == 'POST':
        # Handle user updates
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.designation = request.POST.get('designation', user.designation)
        user.role = request.POST.get('role', user.role)
        user.is_active = 'is_active' in request.POST
        
        user.save()
        messages.success(request, f'User {user.username} updated successfully!')
        return redirect('accounts:user_detail', user_id=user.id)
    
    context = {
        'target_user': user,
        'role_choices': User.Role.choices,
        'title': f'User: {user.username}'
    }
    return render(request, 'accounts/user_detail.html', context)


def officers_list_view(request):
    """
    List officers with caseload (admin only).
    """
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('accounts:dashboard')

    officers = (
        User.objects.filter(role=User.Role.OFFICER)
        .annotate(
            active_case_count=Count(
                "assigned_cases", filter=Q(assigned_cases__status=Case.Status.ACTIVE)
            )
        )
        .order_by("first_name", "last_name", "username")
    )

    search_query = request.GET.get("search", "")
    if search_query:
        officers = officers.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(designation__icontains=search_query)
        )

    context = {
        "officers": officers,
        "search_query": search_query,
        "title": "Officers",
    }
    return render(request, "accounts/officers_list.html", context)


def officer_detail_view(request, user_id):
    """
    Officer profile + caseload view (admin or the officer).
    """
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    officer = get_object_or_404(User, id=user_id, role=User.Role.OFFICER)
    if not request.user.is_admin() and request.user.id != officer.id:
        messages.error(request, "Access denied.")
        return redirect("accounts:dashboard")

    active_cases = (
        Case.objects.filter(probation_officer=officer, status=Case.Status.ACTIVE)
        .select_related("offender", "offender__user")
        .order_by("-date_created")
    )
    offenders = (
        Offender.objects.filter(cases__in=active_cases)
        .distinct()
        .select_related("user")
        .order_by("-date_created")
    )

    stats = {
        "active_cases": active_cases.count(),
        "offenders": offenders.count(),
        "high_risk": offenders.filter(risk_level=Offender.RiskLevel.HIGH).count(),
        "medium_risk": offenders.filter(risk_level=Offender.RiskLevel.MEDIUM).count(),
        "low_risk": offenders.filter(risk_level=Offender.RiskLevel.LOW).count(),
    }

    context = {
        "officer": officer,
        "active_cases": active_cases[:50],
        "offenders": offenders[:50],
        "stats": stats,
        "title": f"Officer: {officer.get_full_name() or officer.username}",
    }
    return render(request, "accounts/officer_detail.html", context)

# Helper functions
def get_user_stats(user):
    """
    Get statistics for the dashboard based on user role.
    """
    stats = {}
    
    if user.is_admin():
        stats = {
            'total_users': User.objects.count(),
            'active_today': User.objects.filter(last_login__date=timezone.now().date()).count(),
            'new_this_month': User.objects.filter(date_joined__month=timezone.now().month).count(),
        }
    elif user.is_officer():
        stats = {
            'assigned_cases': 12,
            'pending_reports': 3,
            'upcoming_court_dates': 2,
            'recent_checkins': 8,
        }
    
    return stats

def get_recent_activity(user):
    """
    Get recent activity for the dashboard.
    """
    activities = []
    
    if user.is_admin():
        activities = [
            {'icon': 'fa-user-plus', 'text': 'New user registered: officer2', 'time': '2 hours ago'},
            {'icon': 'fa-database', 'text': 'ML model training completed', 'time': '1 day ago'},
            {'icon': 'fa-file-export', 'text': 'Monthly report generated', 'time': '2 days ago'},
        ]
    elif user.is_officer():
        activities = [
            {'icon': 'fa-check-circle', 'text': 'Case review completed for CAS-001', 'time': 'Yesterday'},
            {'icon': 'fa-calendar-check', 'text': 'Check-in scheduled for CAS-002', 'time': '2 days ago'},
            {'icon': 'fa-file-alt', 'text': 'Progress report submitted', 'time': '3 days ago'},
        ]
    elif user.is_offender():
        activities = [
            {'icon': 'fa-check', 'text': 'Completed daily check-in', 'time': 'Today'},
            {'icon': 'fa-graduation-cap', 'text': 'Attended vocational training', 'time': 'Yesterday'},
            {'icon': 'fa-comments', 'text': 'Counseling session completed', 'time': '2 days ago'},
        ]
    
    return activities

# Error handling views
def handler404(request, exception):
    """
    Custom 404 error handler.
    """
    context = {
        'title': 'Page Not Found',
        'error_code': 404,
        'error_message': 'The page you are looking for does not exist.'
    }
    return render(request, 'errors/404.html', context, status=404)

def handler500(request):
    """
    Custom 500 error handler.
    """
    context = {
        'title': 'Server Error',
        'error_code': 500,
        'error_message': 'An internal server error occurred. Please try again later.'
    }
    return render(request, 'errors/500.html', context, status=500)

def handler403(request, exception):
    """
    Custom 403 error handler.
    """
    context = {
        'title': 'Access Denied',
        'error_code': 403,
        'error_message': 'You do not have permission to access this page.'
    }
    return render(request, 'errors/403.html', context, status=403)

def handler400(request, exception):
    """
    Custom 400 error handler.
    """
    context = {
        'title': 'Bad Request',
        'error_code': 400,
        'error_message': 'The request could not be understood by the server.'
    }
    return render(request, 'errors/400.html', context, status=400)
