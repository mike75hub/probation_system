"""
Views for programs app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Avg, Q, Sum
from django.http import JsonResponse, HttpResponse
import json
from datetime import datetime, timedelta

from .models import Program, ProgramCategory, Enrollment, Session, Attendance
from .forms import (
    ProgramForm, ProgramCategoryForm, EnrollmentForm, 
    SessionForm, AttendanceForm, ProgramSearchForm
)
from offenders.models import Offender

# Program Category Views
@method_decorator(login_required, name='dispatch')
class ProgramCategoryListView(ListView):
    model = ProgramCategory
    template_name = 'programs/category_list.html'
    context_object_name = 'categories'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Program Categories'
        return context

@method_decorator(login_required, name='dispatch')
class ProgramCategoryCreateView(CreateView):
    model = ProgramCategory
    form_class = ProgramCategoryForm
    template_name = 'programs/category_form.html'
    success_url = reverse_lazy('programs:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Program category created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Program Category'
        return context

@method_decorator(login_required, name='dispatch')
class ProgramCategoryUpdateView(UpdateView):
    model = ProgramCategory
    form_class = ProgramCategoryForm
    template_name = 'programs/category_form.html'
    
    def get_success_url(self):
        return reverse_lazy('programs:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Program category updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Program Category'
        return context

@method_decorator(login_required, name='dispatch')
class ProgramCategoryDeleteView(DeleteView):
    model = ProgramCategory
    template_name = 'programs/category_delete.html'
    success_url = reverse_lazy('programs:category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Program category deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Program Views
@method_decorator(login_required, name='dispatch')
class ProgramListView(ListView):
    model = Program
    template_name = 'programs/program_list.html'
    context_object_name = 'programs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply filters
        program_type = self.request.GET.get('program_type')
        status = self.request.GET.get('status')
        category = self.request.GET.get('category')
        search = self.request.GET.get('search')
        
        if program_type:
            queryset = queryset.filter(program_type=program_type)
        if status:
            queryset = queryset.filter(status=status)
        if category:
            queryset = queryset.filter(category_id=category)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(objectives__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Rehabilitation Programs'
        context['search_form'] = ProgramSearchForm(self.request.GET or None)
        context['total_programs'] = Program.objects.count()
        context['active_programs'] = Program.objects.filter(status='active').count()
        
        # Statistics
        context['enrollment_count'] = Enrollment.objects.count()
        context['avg_completion_rate'] = Program.objects.annotate(
            completion=Avg('enrollments__attendance_rate')
        ).aggregate(avg=Avg('completion'))['avg'] or 0
        
        return context

@method_decorator(login_required, name='dispatch')
class ProgramDetailView(DetailView):
    model = Program
    template_name = 'programs/program_detail.html'
    context_object_name = 'program'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program = self.object
        
        context['title'] = program.name
        context['enrollments'] = program.enrollments.all().order_by('-enrollment_date')
        context['sessions'] = program.sessions.all().order_by('session_number')
        context['active_enrollments'] = program.enrollments.filter(status='active').count()
        context['completion_rate'] = program.completion_rate()
        
        # Add enrollment form for modal
        context['enrollment_form'] = EnrollmentForm(initial={'program': program})
        
        return context

@method_decorator(login_required, name='dispatch')
class ProgramCreateView(CreateView):
    model = Program
    form_class = ProgramForm
    template_name = 'programs/program_form.html'
    success_url = reverse_lazy('programs:program_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Program created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Program'
        return context

@method_decorator(login_required, name='dispatch')
class ProgramUpdateView(UpdateView):
    model = Program
    form_class = ProgramForm
    template_name = 'programs/program_form.html'
    
    def get_success_url(self):
        return reverse_lazy('programs:program_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Program updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Program'
        return context

@method_decorator(login_required, name='dispatch')
class ProgramDeleteView(DeleteView):
    model = Program
    template_name = 'programs/program_delete.html'
    success_url = reverse_lazy('programs:program_list')
    
    def delete(self, request, *args, **kwargs):
        program = self.get_object()
        messages.success(request, f'Program "{program.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Enrollment Views
@method_decorator(login_required, name='dispatch')
class EnrollmentListView(ListView):
    model = Enrollment
    template_name = 'programs/enrollment_list.html'
    context_object_name = 'enrollments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by program if provided
        program_id = self.request.GET.get('program')
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by offender if provided
        offender_id = self.request.GET.get('offender')
        if offender_id:
            queryset = queryset.filter(offender_id=offender_id)
        
        return queryset.order_by('-enrollment_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Program Enrollments'
        context['total_enrollments'] = Enrollment.objects.count()
        context['active_enrollments'] = Enrollment.objects.filter(status='active').count()
        context['completed_enrollments'] = Enrollment.objects.filter(status='completed').count()
        
        # Available programs for filter
        context['programs'] = Program.objects.filter(status='active')
        
        return context

@method_decorator(login_required, name='dispatch')
class EnrollmentCreateView(CreateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'programs/enrollment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('programs:enrollment_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Enrollment created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Enrollment'
        return context

@method_decorator(login_required, name='dispatch')
class EnrollmentDetailView(DetailView):
    model = Enrollment
    template_name = 'programs/enrollment_detail.html'
    context_object_name = 'enrollment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment = self.object
        
        context['title'] = f'Enrollment: {enrollment.offender}'
        context['attendances'] = enrollment.attendances.select_related('session').order_by('-session__date')
        context['total_sessions'] = enrollment.program.sessions.count()
        context['attended_sessions'] = enrollment.attendances.filter(status='present').count()
        
        return context

@method_decorator(login_required, name='dispatch')
class EnrollmentUpdateView(UpdateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'programs/enrollment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('programs:enrollment_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Enrollment updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Enrollment'
        return context

@method_decorator(login_required, name='dispatch')
class EnrollmentDeleteView(DeleteView):
    model = Enrollment
    template_name = 'programs/enrollment_delete.html'
    success_url = reverse_lazy('programs:enrollment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Enrollment deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Session Views
@method_decorator(login_required, name='dispatch')
class SessionCreateView(CreateView):
    model = Session
    form_class = SessionForm
    template_name = 'programs/session_form.html'
    
    def get_success_url(self):
        return reverse_lazy('programs:program_detail', kwargs={'pk': self.object.program.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Session created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Session'
        return context

@method_decorator(login_required, name='dispatch')
class SessionUpdateView(UpdateView):
    model = Session
    form_class = SessionForm
    template_name = 'programs/session_form.html'
    
    def get_success_url(self):
        return reverse_lazy('programs:program_detail', kwargs={'pk': self.object.program.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Session updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Session'
        return context

# Function-based views
@login_required
def program_dashboard(request):
    """Program dashboard view."""
    # Program statistics
    total_programs = Program.objects.count()
    active_programs = Program.objects.filter(status='active').count()
    total_enrollments = Enrollment.objects.count()
    active_enrollments = Enrollment.objects.filter(status='active').count()
    
    # Completion rates
    avg_completion_rate = Program.objects.annotate(
        completion=Avg('enrollments__attendance_rate')
    ).aggregate(avg=Avg('completion'))['avg'] or 0
    
    # Recent programs
    recent_programs = Program.objects.order_by('-created_at')[:5]
    
    # Programs by type
    programs_by_type = Program.objects.values('program_type').annotate(
        count=Count('id'),
        avg_duration=Avg('duration_weeks')
    )
    
    # Enrollment trends (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_enrollments = Enrollment.objects.filter(
        enrollment_date__gte=thirty_days_ago
    ).count()
    
    context = {
        'title': 'Programs Dashboard',
        'total_programs': total_programs,
        'active_programs': active_programs,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'avg_completion_rate': avg_completion_rate,
        'recent_programs': recent_programs,
        'programs_by_type': programs_by_type,
        'recent_enrollments': recent_enrollments,
    }
    
    return render(request, 'programs/dashboard.html', context)

@login_required
def take_attendance(request, session_id):
    """Take attendance for a session."""
    session = get_object_or_404(Session, pk=session_id)
    enrollments = session.program.enrollments.filter(status='active')
    
    if request.method == 'POST':
        for enrollment in enrollments:
            status_key = f'attendance_{enrollment.id}'
            if status_key in request.POST:
                attendance, created = Attendance.objects.get_or_create(
                    session=session,
                    enrollment=enrollment
                )
                attendance.status = request.POST[status_key]
                
                # Record check-in time if present
                if request.POST[status_key] == 'present':
                    attendance.check_in_time = datetime.now()
                
                attendance.save()
        
        messages.success(request, 'Attendance recorded successfully!')
        return redirect('programs:session_attendance', session_id=session_id)
    
    # Get existing attendance records
    attendance_records = {}
    for attendance in session.attendances.all():
        attendance_records[attendance.enrollment_id] = attendance
    
    context = {
        'title': f'Take Attendance - Session {session.session_number}',
        'session': session,
        'enrollments': enrollments,
        'attendance_records': attendance_records,
    }
    
    return render(request, 'programs/take_attendance.html', context)

@login_required
def session_attendance(request, session_id):
    """View attendance for a session."""
    session = get_object_or_404(Session, pk=session_id)
    attendances = session.attendances.select_related('enrollment', 'enrollment__offender')
    
    context = {
        'title': f'Attendance - Session {session.session_number}',
        'session': session,
        'attendances': attendances,
    }
    
    return render(request, 'programs/session_attendance.html', context)

@login_required
def generate_certificate(request, enrollment_id):
    """Generate completion certificate."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    
    if enrollment.status != 'completed':
        messages.error(request, 'Certificate can only be generated for completed enrollments.')
        return redirect('programs:enrollment_detail', pk=enrollment_id)
    
    enrollment.certificate_issued = True
    enrollment.certificate_issue_date = datetime.now()
    enrollment.save()
    
    messages.success(request, 'Certificate generated successfully!')
    return redirect('programs:enrollment_detail', pk=enrollment_id)

@login_required
def program_statistics(request):
    """Get program statistics (AJAX)."""
    data = {
        'total_programs': Program.objects.count(),
        'active_programs': Program.objects.filter(status='active').count(),
        'total_enrollments': Enrollment.objects.count(),
        'active_enrollments': Enrollment.objects.filter(status='active').count(),
        'completion_rate': Enrollment.objects.filter(status='completed').count(),
        'dropout_rate': Enrollment.objects.filter(status='dropped_out').count(),
    }
    
    return JsonResponse(data)

@login_required
def recommend_programs(request, offender_id):
    """Recommend programs for an offender."""
    offender = get_object_or_404(Offender, pk=offender_id)
    
    # Get programs that match offender's risk level
    if offender.risk_level == 'low':
        target_risk = ['all', 'low', 'low_medium']
    elif offender.risk_level == 'medium':
        target_risk = ['all', 'medium', 'low_medium', 'medium_high']
    else:  # high
        target_risk = ['all', 'high', 'medium_high']
    
    recommended_programs = Program.objects.filter(
        status='active',
        target_risk_level__in=target_risk,
        is_accepting_enrollments=True
    ).exclude(
        enrollments__offender=offender  # Exclude already enrolled
    )[:10]
    
    context = {
        'title': f'Recommended Programs for {offender}',
        'offender': offender,
        'recommended_programs': recommended_programs,
    }
    
    return render(request, 'programs/recommended_programs.html', context)