"""
Role-based permission utilities for the probation system.

This module provides decorators and helper functions to enforce role-based
access control across the system. Each role has specific permissions:

- Admin: Full system access
- Officer: Can manage assigned cases, monitoring, and programs
- Offender: Can view own case, check-ins, programs, and profile
- Judiciary: View-only access to cases and reports (scoped)
- NGO: Can facilitate programs and view program data (scoped)
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.views.generic import View
from .models import User


# ============================================================================
# Decorators for Function-Based Views
# ============================================================================

def admin_required(view_func):
    """
    Restrict access to admins only.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role != User.Role.ADMIN:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def officer_required(view_func):
    """
    Restrict access to officers only.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role != User.Role.OFFICER:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def offender_required(view_func):
    """
    Restrict access to offenders only.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role != User.Role.OFFENDER:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def officer_or_admin_required(view_func):
    """
    Restrict access to officers and admins.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role not in [User.Role.ADMIN, User.Role.OFFICER]:
            messages.error(request, 'Only admins and officers can access this resource.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def ngo_or_admin_required(view_func):
    """
    Restrict access to NGO staff and admins.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role not in [User.Role.ADMIN, User.Role.NGO]:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def judiciary_or_admin_required(view_func):
    """
    Restrict access to judiciary and admins.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role not in [User.Role.ADMIN, User.Role.JUDICIARY]:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def authenticated_required(view_func):
    """
    Require authentication but allow any authenticated user.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# Mixins for Class-Based Views
# ============================================================================

class AdminRequiredMixin(View):
    """
    Mixin to restrict class-based views to admins only.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role != User.Role.ADMIN:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class OfficerRequiredMixin(View):
    """
    Mixin to restrict class-based views to officers only.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role != User.Role.OFFICER:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class OffenderRequiredMixin(View):
    """
    Mixin to restrict class-based views to offenders only.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role != User.Role.OFFENDER:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class OfficerOrAdminMixin(View):
    """
    Mixin to restrict class-based views to officers and admins.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role not in [User.Role.ADMIN, User.Role.OFFICER]:
            messages.error(request, 'Only admins and officers can access this resource.')
            return redirect('accounts:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class NGOOrAdminMixin(View):
    """
    Mixin to restrict class-based views to NGO staff and admins.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role not in [User.Role.ADMIN, User.Role.NGO]:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class JudiciaryOrAdminMixin(View):
    """
    Mixin to restrict class-based views to judiciary and admins.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        if request.user.role not in [User.Role.ADMIN, User.Role.JUDICIARY]:
            messages.error(request, 'You do not have permission to access this resource.')
            return redirect('accounts:dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class AuthenticatedUserMixin(View):
    """
    Mixin to require authentication but allow any authenticated user.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first.')
            return redirect('accounts:login')
        
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# Helper Functions for Permission Checks
# ============================================================================

def user_can_view_offender(user, offender):
    """
    Check if a user can view a specific offender's details.
    
    Rules:
    - Admin: can view any offender
    - Officer: can view offenders assigned to them
    - Offender: can view only their own profile
    - Judiciary: can view offenders (scoped by institution if implemented)
    - NGO: can view offenders participating in their programs
    """
    if user.role == User.Role.ADMIN:
        return True
    
    if user.role == User.Role.OFFICER:
        # Officer can view offenders assigned to them
        from offenders.models import Case
        return Case.objects.filter(
            offender=offender,
            assigned_officer=user,
            status='active'
        ).exists()
    
    if user.role == User.Role.OFFENDER:
        # Offender can view only their own profile
        return offender.user_id == user.id
    
    if user.role == User.Role.JUDICIARY:
        # Judiciary can view any offender (in production, add institution scoping)
        return True
    
    if user.role == User.Role.NGO:
        # NGO can view offenders in their programs
        from programs.models import Enrollment
        return Enrollment.objects.filter(
            offender=offender,
            program__facilitated_by_ngo=True
        ).exists()
    
    return False


def user_can_view_case(user, case):
    """
    Check if a user can view a specific case.
    
    Rules:
    - Admin: can view any case
    - Officer: can view assigned cases or cases under supervision
    - Offender: can view only their own cases
    - Judiciary: can view all cases (scoped by institution if implemented)
    - NGO: limited access
    """
    if user.role == User.Role.ADMIN:
        return True
    
    if user.role == User.Role.OFFICER:
        # Officer can view cases assigned to them
        return case.assigned_officer_id == user.id
    
    if user.role == User.Role.OFFENDER:
        # Offender can view only their own case
        return case.offender.user_id == user.id
    
    if user.role == User.Role.JUDICIARY:
        # Judiciary can view any case
        return True
    
    if user.role == User.Role.NGO:
        # NGO has limited case access
        return False
    
    return False


def user_can_view_checkin(user, checkin):
    """
    Check if a user can view a specific check-in.
    
    Rules:
    - Admin: can view any check-in
    - Officer: can view check-ins for cases they're assigned to
    - Offender: can view only their own check-ins
    - Judiciary/NGO: view-only access based on context
    """
    if user.role == User.Role.ADMIN:
        return True
    
    if user.role == User.Role.OFFICER:
        # Officer can view check-ins for their assigned cases
        return checkin.probation_officer_id == user.id
    
    if user.role == User.Role.OFFENDER:
        # Offender can view only their own check-ins
        return checkin.offender.user_id == user.id
    
    if user.role == User.Role.JUDICIARY:
        return True
    
    if user.role == User.Role.NGO:
        return False
    
    return False


def user_can_edit_offender(user, offender):
    """
    Check if a user can edit an offender's details.
    
    Rules:
    - Admin: can edit any offender
    - Officer: can edit offenders assigned to them
    - Offender: can edit their own profile (limited fields)
    - Judiciary/NGO: cannot edit
    """
    if user.role == User.Role.ADMIN:
        return True
    
    if user.role == User.Role.OFFICER:
        # Officer can edit offenders assigned to them
        from offenders.models import Case
        return Case.objects.filter(
            offender=offender,
            assigned_officer=user,
            status='active'
        ).exists()
    
    if user.role == User.Role.OFFENDER:
        # Offender can edit only their own profile
        return offender.user_id == user.id
    
    return False


def user_can_delete_offender(user, offender):
    """
    Check if a user can delete an offender.
    
    Rules:
    - Only Admin can delete offenders
    """
    return user.role == User.Role.ADMIN


def user_can_manage_users(user):
    """
    Check if a user can manage other users (create, edit, delete).
    
    Rules:
    - Only Admin can manage users
    """
    return user.role == User.Role.ADMIN


def user_can_create_program_enrollment(user):
    """
    Check if a user can enroll offenders in programs.
    
    Rules:
    - Admin: can enroll any offender in any program
    - Officer: can enroll their assigned offenders
    - NGO: can enroll offenders in their programs
    - Others: cannot enroll
    """
    return user.role in [User.Role.ADMIN, User.Role.OFFICER, User.Role.NGO]


def user_can_manage_programs(user):
    """
    Check if a user can create/edit/delete programs.
    
    Rules:
    - Admin: can manage all programs
    - NGO: can manage specific programs they facilitate
    - Others: cannot manage programs
    """
    return user.role in [User.Role.ADMIN, User.Role.NGO]


def user_can_view_reports(user):
    """
    Check if a user can view reports.
    
    Rules:
    - Admin: can view all reports
    - Officer: can view their own reports
    - Judiciary: can view relevant reports
    - NGO: can view program-related reports
    - Offender: can view their own reports (if enabled)
    """
    return user.role in [
        User.Role.ADMIN,
        User.Role.OFFICER,
        User.Role.JUDICIARY,
        User.Role.NGO,
        User.Role.OFFENDER
    ]


def user_can_create_assessment(user):
    """
    Check if a user can create risk assessments.
    
    Rules:
    - Admin: can create for any offender
    - Officer: can create for their assigned offenders
    - Others: cannot create assessments
    """
    return user.role in [User.Role.ADMIN, User.Role.OFFICER]


# ============================================================================
# Context Processors for Templates
# ============================================================================

def add_role_permissions(request):
    """
    Add user role and permission flags to template context.
    
    This can be added to TEMPLATES['OPTIONS']['context_processors'] in settings.py
    """
    context = {}
    
    if request.user.is_authenticated:
        context['user_role'] = request.user.role
        context['is_admin'] = request.user.role == User.Role.ADMIN
        context['is_officer'] = request.user.role == User.Role.OFFICER
        context['is_offender'] = request.user.role == User.Role.OFFENDER
        context['is_judiciary'] = request.user.role == User.Role.JUDICIARY
        context['is_ngo'] = request.user.role == User.Role.NGO
    
    return context
