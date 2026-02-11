"""
Views for reports app.
"""
import json
import csv
import io
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt  # Fixed: Separate line
from django.views.decorators.http import require_POST  # Fixed: Separate line
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, Max, Min, F, Case, When
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

import pandas as pd
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import base64
from io import BytesIO

from .models import (
    ReportType, ReportSchedule, GeneratedReport,
    ReportTemplate, ReportDashboard, DashboardReport,
    ReportAnalytics
)
from .forms import (
    ReportTypeForm, ReportScheduleForm, ReportGenerationForm,
    ComplianceReportForm, PerformanceReportForm,
    ReportTemplateForm, DashboardForm, DashboardReportForm
)
from offenders.models import Offender, Case
from monitoring.models import CheckIn, GPSMonitoring, DrugTest, Alert
from accounts.models import User
from programs.models import Program, Enrollment

# Helper functions for role-based permissions
def is_admin(user):
    return user.role == 'admin'

def is_officer(user):
    return user.role == 'officer'

def is_supervisor(user):
    return user.role == 'supervisor'

def is_judiciary(user):
    return user.role == 'judiciary'

def is_ngo(user):
    return user.role == 'ngo'

def can_generate_report(user, report_type):
    """Check if user can generate specific report type."""
    user_role = user.role
    return user_role in report_type.allowed_roles

# ============================================================================
# REPORT DASHBOARD VIEWS
# ============================================================================

@login_required
def report_dashboard(request):
    """Main reports dashboard."""
    user = request.user
    user_role = user.role
    
    # Get accessible report types based on role
    accessible_reports = ReportType.objects.filter(
        is_active=True,
        allowed_roles__contains=[user_role]
    )
    
    # Get recent generated reports by user
    recent_reports = GeneratedReport.objects.filter(
        generated_by=user
    ).order_by('-generation_date')[:10]
    
    # Get scheduled reports
    scheduled_reports = ReportSchedule.objects.filter(
        status='active',
        recipients=user
    )[:5]
    
    # Get dashboards accessible to user
    if user_role in ['admin', 'supervisor']:
        dashboards = ReportDashboard.objects.filter(
            Q(is_public=True) | Q(allowed_users=user) | Q(created_by=user)
        ).distinct()
    else:
        dashboards = ReportDashboard.objects.filter(
            Q(is_public=True) | Q(allowed_users=user)
        ).distinct()
    
    # Quick stats
    stats = {
        'total_reports_generated': GeneratedReport.objects.filter(
            generated_by=user
        ).count(),
        'pending_schedules': ReportSchedule.objects.filter(
            recipients=user,
            status='active'
        ).count(),
        'favorite_reports': accessible_reports.count(),
        'recent_downloads': GeneratedReport.objects.filter(
            generated_by=user,
            download_count__gt=0
        ).order_by('-last_downloaded')[:5].count(),
    }
    
    # Quick report types
    quick_reports = accessible_reports.filter(
        Q(is_daily=True) | Q(is_weekly=True) | Q(is_monthly=True)
    )[:6]
    
    context = {
        'accessible_reports': accessible_reports,
        'recent_reports': recent_reports,
        'scheduled_reports': scheduled_reports,
        'dashboards': dashboards,
        'stats': stats,
        'quick_reports': quick_reports,
        'user_role': user_role,
    }
    
    return render(request, 'reports/dashboard.html', context)

# ============================================================================
# REPORT GENERATION VIEWS
# ============================================================================

@login_required
def generate_report(request):
    """Generate a new report with custom parameters."""
    user = request.user
    
    if request.method == 'POST':
        form = ReportGenerationForm(request.POST, user=user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get form data
                    report_type = form.cleaned_data['report_type']
                    
                    # Check if user can generate this report type
                    if not can_generate_report(user, report_type):
                        messages.error(request, 'You do not have permission to generate this type of report.')
                        return redirect('reports:dashboard')
                    
                    # Calculate date range
                    date_from, date_to = calculate_date_range(form)
                    
                    # Create GeneratedReport record
                    generated_report = GeneratedReport.objects.create(
                        report_type=report_type,
                        title=f"{report_type.name} - {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}",
                        description=f"Report generated by {user.get_full_name()}",
                        generated_by=user,
                        period_start=date_from,
                        period_end=date_to,
                        file_format=form.cleaned_data['format'],
                        parameters={
                            'period': form.cleaned_data['period'],
                            'date_from': date_from.isoformat(),
                            'date_to': date_to.isoformat(),
                            'include_charts': form.cleaned_data['include_charts'],
                            'include_details': form.cleaned_data['include_details'],
                            'filters': {
                                'officer': form.cleaned_data.get('officer', ''),
                                'offender': form.cleaned_data.get('offender', ''),
                                'location': form.cleaned_data.get('location', ''),
                            }
                        }
                    )
                    
                    # Generate report data based on category
                    report_data = generate_report_data(
                        report_type.category,
                        date_from,
                        date_to,
                        form.cleaned_data,
                        user
                    )
                    
                    # Create report file
                    file_content = create_report_file(
                        generated_report,
                        report_data,
                        form.cleaned_data['format'],
                        form.cleaned_data['include_charts']
                    )
                    
                    # Save file to GeneratedReport
                    filename = f"{report_type.name.replace(' ', '_')}_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}"
                    file_extension = get_file_extension(form.cleaned_data['format'])
                    filename = f"{filename}.{file_extension}"
                    
                    generated_report.file.save(filename, file_content)
                    generated_report.status = 'completed'
                    generated_report.save()
                    
                    # Track analytics
                    ReportAnalytics.objects.create(
                        report=generated_report,
                        user=user,
                        action='generated',
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
                    # Send email if requested
                    if form.cleaned_data['send_email']:
                        send_report_email(generated_report, user.email)
                        messages.info(request, 'Report has been sent to your email.')
                    
                    messages.success(request, f'Report "{generated_report.title}" has been generated successfully.')
                    return redirect('reports:view_report', report_id=generated_report.id)
                    
            except Exception as e:
                messages.error(request, f'Error generating report: {str(e)}')
                return redirect('reports:generate')
    else:
        form = ReportGenerationForm(user=user)
    
    report_types = ReportType.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'report_types': report_types,
    }
    
    return render(request, 'reports/generate.html', context)


@login_required
def quick_generate_report(request, report_type_id):
    """Quick generate a report with default parameters."""
    user = request.user
    report_type = get_object_or_404(ReportType, id=report_type_id, is_active=True)
    
    # Check permission
    if not can_generate_report(user, report_type):
        messages.error(request, 'You do not have permission to generate this report.')
        return redirect('reports:dashboard')
    
    # Determine date range based on frequency
    today = timezone.now().date()
    
    if report_type.is_daily:
        date_from = today
        date_to = today
        period = 'today'
    elif report_type.is_weekly:
        date_from = today - timedelta(days=today.weekday())
        date_to = date_from + timedelta(days=6)
        period = 'this_week'
    elif report_type.is_monthly:
        date_from = today.replace(day=1)
        if today.month == 12:
            date_to = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            date_to = today.replace(month=today.month+1, day=1) - timedelta(days=1)
        period = 'this_month'
    else:
        date_from = today - timedelta(days=30)
        date_to = today
        period = 'custom'
    
    try:
        with transaction.atomic():
            # Create GeneratedReport record
            generated_report = GeneratedReport.objects.create(
                report_type=report_type,
                title=f"{report_type.name} - {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}",
                description=f"Quick report generated by {user.get_full_name()}",
                generated_by=user,
                period_start=date_from,
                period_end=date_to,
                file_format='pdf',
                parameters={
                    'period': period,
                    'date_from': date_from.isoformat(),
                    'date_to': date_to.isoformat(),
                    'include_charts': True,
                    'include_details': True,
                    'quick_generate': True,
                }
            )
            
            # Generate report data
            report_data = generate_report_data(
                report_type.category,
                date_from,
                date_to,
                {},
                user
            )
            
            # Create PDF report
            file_content = create_report_file(generated_report, report_data, 'pdf', True)
            
            # Save file
            filename = f"quick_{report_type.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            generated_report.file.save(filename, file_content)
            generated_report.status = 'completed'
            generated_report.save()
            
            # Track analytics
            ReportAnalytics.objects.create(
                report=generated_report,
                user=user,
                action='generated',
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, f'Quick report "{generated_report.title}" has been generated.')
            return redirect('reports:view_report', report_id=generated_report.id)
            
    except Exception as e:
        messages.error(request, f'Error generating quick report: {str(e)}')
        return redirect('reports:dashboard')


@login_required
def compliance_report(request):
    """Generate a compliance-specific report."""
    user = request.user
    
    if request.method == 'POST':
        form = ComplianceReportForm(request.POST)
        
        if form.is_valid():
            try:
                # Get report type
                report_type = ReportType.objects.filter(
                    category='compliance',
                    is_active=True,
                    allowed_roles__contains=[user.role]
                ).first()
                
                if not report_type:
                    messages.error(request, 'No compliance report type available for your role.')
                    return redirect('reports:dashboard')
                
                # Get form data
                date_from = form.cleaned_data['date_from']
                date_to = form.cleaned_data['date_to']
                
                # Create GeneratedReport record
                generated_report = GeneratedReport.objects.create(
                    report_type=report_type,
                    title=f"Compliance Report - {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}",
                    description=f"Compliance report generated by {user.get_full_name()}",
                    generated_by=user,
                    period_start=date_from,
                    period_end=date_to,
                    file_format='pdf',
                    parameters={
                        'group_by': form.cleaned_data['group_by'],
                        'officer': form.cleaned_data.get('officer', ''),
                        'min_compliance': form.cleaned_data.get('min_compliance', ''),
                        'include_checkins': form.cleaned_data['include_checkins'],
                        'include_gps': form.cleaned_data['include_gps'],
                        'include_drug_tests': form.cleaned_data['include_drug_tests'],
                        'include_employment': form.cleaned_data['include_employment'],
                    }
                )
                
                # Generate compliance data
                report_data = generate_compliance_data(
                    date_from,
                    date_to,
                    form.cleaned_data,
                    user
                )
                
                # Create PDF report
                file_content = create_compliance_pdf(generated_report, report_data)
                
                # Save file
                filename = f"compliance_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.pdf"
                generated_report.file.save(filename, file_content)
                generated_report.status = 'completed'
                generated_report.save()
                
                messages.success(request, f'Compliance report "{generated_report.title}" has been generated.')
                return redirect('reports:view_report', report_id=generated_report.id)
                
            except Exception as e:
                messages.error(request, f'Error generating compliance report: {str(e)}')
                return redirect('reports:compliance_report')
    else:
        form = ComplianceReportForm()
    
    context = {
        'form': form,
        'title': 'Compliance Report',
    }
    
    return render(request, 'reports/compliance_report.html', context)


@login_required
def performance_report(request):
    """Generate a performance-specific report."""
    user = request.user
    
    if request.method == 'POST':
        form = PerformanceReportForm(request.POST)
        
        if form.is_valid():
            try:
                # Get report type
                report_type = ReportType.objects.filter(
                    category='performance',
                    is_active=True,
                    allowed_roles__contains=[user.role]
                ).first()
                
                if not report_type:
                    messages.error(request, 'No performance report type available for your role.')
                    return redirect('reports:dashboard')
                
                # Create GeneratedReport record
                generated_report = GeneratedReport.objects.create(
                    report_type=report_type,
                    title=f"Performance Report - {form.cleaned_data['report_type']}",
                    description=f"Performance report generated by {user.get_full_name()}",
                    generated_by=user,
                    period_start=timezone.now().date() - timedelta(days=365),
                    period_end=timezone.now().date(),
                    file_format='pdf',
                    parameters=form.cleaned_data
                )
                
                # Generate performance data
                report_data = generate_performance_data(
                    form.cleaned_data,
                    user
                )
                
                # Create PDF report
                file_content = create_performance_pdf(generated_report, report_data)
                
                # Save file
                filename = f"performance_{form.cleaned_data['report_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                generated_report.file.save(filename, file_content)
                generated_report.status = 'completed'
                generated_report.save()
                
                messages.success(request, f'Performance report "{generated_report.title}" has been generated.')
                return redirect('reports:view_report', report_id=generated_report.id)
                
            except Exception as e:
                messages.error(request, f'Error generating performance report: {str(e)}')
                return redirect('reports:performance_report')
    else:
        form = PerformanceReportForm()
    
    context = {
        'form': form,
        'title': 'Performance Report',
    }
    
    return render(request, 'reports/performance_report.html', context)

# ============================================================================
# GENERATED REPORTS MANAGEMENT VIEWS
# ============================================================================

class ReportListView(LoginRequiredMixin, ListView):
    """List all generated reports."""
    model = GeneratedReport
    template_name = 'reports/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        user_role = user.role
        
        # Base queryset
        if user_role in ['admin', 'supervisor']:
            queryset = GeneratedReport.objects.all()
        else:
            queryset = GeneratedReport.objects.filter(generated_by=user)
        
        # Apply filters
        report_type = self.request.GET.get('report_type', '')
        status = self.request.GET.get('status', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        search = self.request.GET.get('search', '')
        
        if report_type:
            queryset = queryset.filter(report_type_id=report_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_from:
            queryset = queryset.filter(generation_date__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(generation_date__date__lte=date_to)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-generation_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_types'] = ReportType.objects.filter(is_active=True)
        context['status_choices'] = GeneratedReport.Status.choices
        context['filters'] = {
            'report_type': self.request.GET.get('report_type', ''),
            'status': self.request.GET.get('status', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', ''),
        }
        return context


@login_required
def view_report(request, report_id):
    """View a generated report."""
    report = get_object_or_404(GeneratedReport, id=report_id)
    
    # Check permission
    user = request.user
    user_role = user.role
    if report.generated_by != user and user_role not in ['admin', 'supervisor']:
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('reports:report_list')
    
    # Track view analytics
    ReportAnalytics.objects.create(
        report=report,
        user=user,
        action='viewed',
        ip_address=request.META.get('REMOTE_ADDR', ''),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # For HTML reports, display directly
    if report.file_format == 'html' and report.file:
        try:
            content = report.file.read().decode('utf-8')
            return HttpResponse(content)
        except:
            pass
    
    context = {
        'report': report,
        'file_size_display': report.get_file_size_display(),
    }
    
    return render(request, 'reports/view_report.html', context)


@login_required
def download_report(request, report_id):
    """Download a generated report."""
    report = get_object_or_404(GeneratedReport, id=report_id)
    
    # Check permission
    user = request.user
    user_role = user.role
    if report.generated_by != user and user_role not in ['admin', 'supervisor']:
        messages.error(request, 'You do not have permission to download this report.')
        return redirect('reports:report_list')
    
    if not report.file:
        messages.error(request, 'Report file not found.')
        return redirect('reports:view_report', report_id=report_id)
    
    # Increment download count
    report.increment_download_count()
    
    # Track download analytics
    ReportAnalytics.objects.create(
        report=report,
        user=user,
        action='downloaded',
        ip_address=request.META.get('REMOTE_ADDR', ''),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Determine content type
    content_types = {
        'pdf': 'application/pdf',
        'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
        'html': 'text/html',
        'json': 'application/json',
    }
    
    content_type = content_types.get(report.file_format, 'application/octet-stream')
    filename = report.file.name.split('/')[-1]
    
    response = HttpResponse(report.file.read(), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


class ReportDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a generated report."""
    model = GeneratedReport
    template_name = 'reports/delete_report.html'
    success_url = reverse_lazy('reports:report_list')
    
    def test_func(self):
        report = self.get_object()
        user = self.request.user
        user_role = user.role
        return report.generated_by == user or user_role == 'admin'
    
    def delete(self, request, *args, **kwargs):
        report = self.get_object()
        messages.success(request, f'Report "{report.title}" has been deleted.')
        return super().delete(request, *args, **kwargs)

# ============================================================================
# REPORT SCHEDULING VIEWS
# ============================================================================

class ScheduleListView(LoginRequiredMixin, ListView):
    """List all report schedules."""
    model = ReportSchedule
    template_name = 'reports/schedule_list.html'
    context_object_name = 'schedules'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        user_role = user.role
        
        # Base queryset
        if user_role in ['admin', 'supervisor']:
            queryset = ReportSchedule.objects.all()
        else:
            queryset = ReportSchedule.objects.filter(created_by=user)
        
        # Apply filters
        status = self.request.GET.get('status', '')
        frequency = self.request.GET.get('frequency', '')
        report_type = self.request.GET.get('report_type', '')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if frequency:
            queryset = queryset.filter(frequency=frequency)
        
        if report_type:
            queryset = queryset.filter(report_type_id=report_type)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ReportSchedule.Status.choices
        context['frequency_choices'] = ReportSchedule.Frequency.choices
        context['report_types'] = ReportType.objects.filter(is_active=True)
        context['filters'] = {
            'status': self.request.GET.get('status', ''),
            'frequency': self.request.GET.get('frequency', ''),
            'report_type': self.request.GET.get('report_type', ''),
        }
        return context


@login_required
def create_schedule(request):
    """Create a new report schedule."""
    user = request.user
    
    if request.method == 'POST':
        form = ReportScheduleForm(request.POST, user=user)
        
        if form.is_valid():
            try:
                schedule = form.save(commit=False)
                schedule.created_by = user
                schedule.next_run = schedule.calculate_next_run()
                schedule.save()
                
                # Save many-to-many fields
                form.save_m2m()
                
                messages.success(request, f'Report schedule "{schedule.name}" has been created.')
                return redirect('reports:schedule_list')
                
            except Exception as e:
                messages.error(request, f'Error creating schedule: {str(e)}')
                return redirect('reports:create_schedule')
    else:
        form = ReportScheduleForm(user=user)
    
    context = {
        'form': form,
        'title': 'Create Report Schedule',
    }
    
    return render(request, 'reports/schedule_form.html', context)


@login_required
def update_schedule(request, pk):
    """Update an existing report schedule."""
    schedule = get_object_or_404(ReportSchedule, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if schedule.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to edit this schedule.')
        return redirect('reports:schedule_list')
    
    if request.method == 'POST':
        form = ReportScheduleForm(request.POST, instance=schedule, user=user)
        
        if form.is_valid():
            try:
                updated_schedule = form.save()
                
                # Recalculate next run if needed
                if any(field in form.changed_data for field in ['frequency', 'start_date', 'scheduled_time', 'last_run']):
                    updated_schedule.next_run = updated_schedule.calculate_next_run()
                    updated_schedule.save()
                
                messages.success(request, f'Schedule "{updated_schedule.name}" has been updated.')
                return redirect('reports:schedule_list')
                
            except Exception as e:
                messages.error(request, f'Error updating schedule: {str(e)}')
                return redirect('reports:update_schedule', pk=pk)
    else:
        form = ReportScheduleForm(instance=schedule, user=user)
    
    context = {
        'form': form,
        'title': 'Update Report Schedule',
        'schedule': schedule,
    }
    
    return render(request, 'reports/schedule_form.html', context)


@login_required
@require_POST
def toggle_schedule_status(request, pk):
    """Toggle schedule status (active/paused)."""
    schedule = get_object_or_404(ReportSchedule, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if schedule.created_by != user and user_role != 'admin':
        return JsonResponse({'error': 'No permission'}, status=403)
    
    if schedule.status == 'active':
        schedule.status = 'paused'
    else:
        schedule.status = 'active'
    
    schedule.save()
    
    return JsonResponse({
        'success': True,
        'new_status': schedule.status,
        'status_display': schedule.get_status_display(),
    })


@login_required
def delete_schedule(request, pk):
    """Delete a report schedule."""
    schedule = get_object_or_404(ReportSchedule, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if schedule.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to delete this schedule.')
        return redirect('reports:schedule_list')
    
    if request.method == 'POST':
        schedule_name = schedule.name
        schedule.delete()
        messages.success(request, f'Schedule "{schedule_name}" has been deleted.')
        return redirect('reports:schedule_list')
    
    context = {
        'schedule': schedule,
    }
    
    return render(request, 'reports/delete_schedule.html', context)

# ============================================================================
# REPORT DASHBOARDS VIEWS
# ============================================================================

class DashboardListView(LoginRequiredMixin, ListView):
    """List all report dashboards."""
    model = ReportDashboard
    template_name = 'reports/dashboard_list.html'
    context_object_name = 'dashboards'
    
    def get_queryset(self):
        user = self.request.user
        user_role = user.role
        
        # Get dashboards based on user role
        if user_role in ['admin', 'supervisor']:
            queryset = ReportDashboard.objects.all()
        else:
            queryset = ReportDashboard.objects.filter(
                Q(is_public=True) | Q(allowed_users=user) | Q(created_by=user)
            ).distinct()
        
        return queryset.order_by('-created_at')


@login_required
def view_dashboard(request, pk):
    """View a report dashboard."""
    dashboard = get_object_or_404(ReportDashboard, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if not dashboard.is_public and user not in dashboard.allowed_users.all() and dashboard.created_by != user and user_role not in ['admin', 'supervisor']:
        messages.error(request, 'You do not have permission to view this dashboard.')
        return redirect('reports:dashboard_list')
    
    # Get dashboard reports with positions
    dashboard_reports = DashboardReport.objects.filter(
        dashboard=dashboard
    ).select_related('report_type').order_by('position_y', 'position_x')
    
    # Get layout config
    try:
        layout_config = json.loads(dashboard.layout_config) if dashboard.layout_config else {}
    except:
        layout_config = {}
    
    # Default layout config
    if not layout_config:
        layout_config = {
            'columns': 12,
            'rowHeight': 100,
            'margin': [10, 10]
        }
    
    context = {
        'dashboard': dashboard,
        'dashboard_reports': dashboard_reports,
        'layout_config': layout_config,
        'layout_config_json': json.dumps(layout_config),
    }
    
    return render(request, 'reports/view_dashboard.html', context)


@login_required
def create_dashboard(request):
    """Create a new report dashboard."""
    user = request.user
    
    if request.method == 'POST':
        form = DashboardForm(request.POST, user=user)
        
        if form.is_valid():
            try:
                dashboard = form.save(commit=False)
                dashboard.created_by = user
                dashboard.save()
                
                # Save many-to-many fields
                form.save_m2m()
                
                messages.success(request, f'Dashboard "{dashboard.name}" has been created.')
                return redirect('reports:edit_dashboard', pk=dashboard.pk)
                
            except Exception as e:
                messages.error(request, f'Error creating dashboard: {str(e)}')
                return redirect('reports:create_dashboard')
    else:
        form = DashboardForm(user=user)
    
    context = {
        'form': form,
        'title': 'Create Dashboard',
    }
    
    return render(request, 'reports/dashboard_form.html', context)


@login_required
def edit_dashboard(request, pk):
    """Edit a report dashboard."""
    dashboard = get_object_or_404(ReportDashboard, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if dashboard.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to edit this dashboard.')
        return redirect('reports:dashboard_list')
    
    if request.method == 'POST':
        form = DashboardForm(request.POST, instance=dashboard, user=user)
        
        if form.is_valid():
            try:
                updated_dashboard = form.save()
                messages.success(request, f'Dashboard "{updated_dashboard.name}" has been updated.')
                return redirect('reports:view_dashboard', pk=updated_dashboard.pk)
                
            except Exception as e:
                messages.error(request, f'Error updating dashboard: {str(e)}')
                return redirect('reports:edit_dashboard', pk=pk)
    else:
        form = DashboardForm(instance=dashboard, user=user)
    
    # Get current dashboard reports
    dashboard_reports = DashboardReport.objects.filter(dashboard=dashboard)
    
    # Get available report types
    available_reports = ReportType.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'dashboard': dashboard,
        'dashboard_reports': dashboard_reports,
        'available_reports': available_reports,
        'title': 'Edit Dashboard',
    }
    
    return render(request, 'reports/dashboard_form.html', context)


@login_required
def add_dashboard_report(request, pk):
    """Add a report to a dashboard."""
    dashboard = get_object_or_404(ReportDashboard, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if dashboard.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to modify this dashboard.')
        return redirect('reports:view_dashboard', pk=dashboard.pk)
    
    if request.method == 'POST':
        form = DashboardReportForm(request.POST)
        
        if form.is_valid():
            try:
                dashboard_report = form.save(commit=False)
                dashboard_report.dashboard = dashboard
                
                # Check if report type already exists in dashboard
                if DashboardReport.objects.filter(
                    dashboard=dashboard,
                    report_type=dashboard_report.report_type
                ).exists():
                    messages.error(request, 'This report type is already in the dashboard.')
                else:
                    dashboard_report.save()
                    messages.success(request, f'Report "{dashboard_report.report_type.name}" has been added to the dashboard.')
                
                return redirect('reports:edit_dashboard', pk=dashboard.pk)
                
            except Exception as e:
                messages.error(request, f'Error adding report to dashboard: {str(e)}')
                return redirect('reports:add_dashboard_report', pk=pk)
    else:
        form = DashboardReportForm()
    
    context = {
        'form': form,
        'dashboard': dashboard,
        'title': 'Add Report to Dashboard',
    }
    
    return render(request, 'reports/dashboard_report_form.html', context)


@login_required
def update_dashboard_report(request, pk, report_pk):
    """Update a report in a dashboard."""
    dashboard = get_object_or_404(ReportDashboard, pk=pk)
    dashboard_report = get_object_or_404(DashboardReport, pk=report_pk, dashboard=dashboard)
    
    # Check permission
    user = request.user
    user_role = user.role
    if dashboard.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to modify this dashboard.')
        return redirect('reports:view_dashboard', pk=dashboard.pk)
    
    if request.method == 'POST':
        form = DashboardReportForm(request.POST, instance=dashboard_report)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Dashboard report has been updated.')
                return redirect('reports:edit_dashboard', pk=dashboard.pk)
                
            except Exception as e:
                messages.error(request, f'Error updating dashboard report: {str(e)}')
                return redirect('reports:update_dashboard_report', pk=pk, report_pk=report_pk)
    else:
        form = DashboardReportForm(instance=dashboard_report)
    
    context = {
        'form': form,
        'dashboard': dashboard,
        'dashboard_report': dashboard_report,
        'title': 'Update Dashboard Report',
    }
    
    return render(request, 'reports/dashboard_report_form.html', context)


@login_required
def delete_dashboard_report(request, pk, report_pk):
    """Remove a report from a dashboard."""
    dashboard = get_object_or_404(ReportDashboard, pk=pk)
    dashboard_report = get_object_or_404(DashboardReport, pk=report_pk, dashboard=dashboard)
    
    # Check permission
    user = request.user
    user_role = user.role
    if dashboard.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to modify this dashboard.')
        return redirect('reports:view_dashboard', pk=dashboard.pk)
    
    if request.method == 'POST':
        report_name = dashboard_report.report_type.name
        dashboard_report.delete()
        messages.success(request, f'Report "{report_name}" has been removed from the dashboard.')
        return redirect('reports:edit_dashboard', pk=dashboard.pk)
    
    context = {
        'dashboard': dashboard,
        'dashboard_report': dashboard_report,
    }
    
    return render(request, 'reports/delete_dashboard_report.html', context)


@login_required
def delete_dashboard(request, pk):
    """Delete a report dashboard."""
    dashboard = get_object_or_404(ReportDashboard, pk=pk)
    
    # Check permission
    user = request.user
    user_role = user.role
    if dashboard.created_by != user and user_role != 'admin':
        messages.error(request, 'You do not have permission to delete this dashboard.')
        return redirect('reports:dashboard_list')
    
    if request.method == 'POST':
        dashboard_name = dashboard.name
        dashboard.delete()
        messages.success(request, f'Dashboard "{dashboard_name}" has been deleted.')
        return redirect('reports:dashboard_list')
    
    context = {
        'dashboard': dashboard,
    }
    
    return render(request, 'reports/delete_dashboard.html', context)

# ============================================================================
# REPORT ANALYTICS VIEWS
# ============================================================================

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'supervisor'])
def report_analytics(request):
    """View report usage analytics."""
    # Time period
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)
        period = 'month'
    
    # Get analytics data
    analytics = ReportAnalytics.objects.filter(
        action_time__date__gte=start_date
    )
    
    # Popular reports
    popular_reports = GeneratedReport.objects.filter(
        analytics__action_time__gte=start_date
    ).annotate(
        view_count=Count('analytics', filter=Q(analytics__action='viewed')),
        download_count=Count('analytics', filter=Q(analytics__action='downloaded'))
    ).order_by('-view_count')[:10]
    
    # User activity
    user_activity = analytics.values(
        'user__username', 'user__first_name', 'user__last_name'
    ).annotate(
        total_actions=Count('id'),
        views=Count('id', filter=Q(action='viewed')),
        downloads=Count('id', filter=Q(action='downloaded'))
    ).order_by('-total_actions')[:10]
    
    # Report type distribution
    report_type_distribution = analytics.values(
        'report__report_type__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Daily activity
    daily_activity = analytics.extra(
        select={'day': "DATE(action_time)"}
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    context = {
        'period': period,
        'start_date': start_date,
        'end_date': today,
        'popular_reports': popular_reports,
        'user_activity': user_activity,
        'report_type_distribution': report_type_distribution,
        'daily_activity': daily_activity,
        'total_views': analytics.filter(action='viewed').count(),
        'total_downloads': analytics.filter(action='downloaded').count(),
        'total_users': analytics.values('user').distinct().count(),
    }
    
    return render(request, 'reports/analytics.html', context)

# ============================================================================
# API VIEWS
# ============================================================================

@login_required
def api_report_data(request, report_type_id):
    """API endpoint for report data (for dashboards)."""
    report_type = get_object_or_404(ReportType, id=report_type_id)
    
    # Check permission
    user_role = request.user.role
    if user_role not in report_type.allowed_roles:
        return JsonResponse({'error': 'No permission'}, status=403)
    
    # Get parameters
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).date().isoformat())
    date_to = request.GET.get('date_to', timezone.now().date().isoformat())
    
    try:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    except:
        date_from = timezone.now().date() - timedelta(days=30)
        date_to = timezone.now().date()
    
    # Generate report data based on type
    report_data = generate_report_data(
        report_type.category,
        date_from,
        date_to,
        {},
        request.user
    )
    
    return JsonResponse(report_data, safe=False)


@login_required
def api_dashboard_data(request, dashboard_id):
    """API endpoint for dashboard data."""
    dashboard = get_object_or_404(ReportDashboard, id=dashboard_id)
    
    # Check permission
    user = request.user
    user_role = user.role
    if not dashboard.is_public and user not in dashboard.allowed_users.all() and dashboard.created_by != user and user_role not in ['admin', 'supervisor']:
        return JsonResponse({'error': 'No permission'}, status=403)
    
    # Get dashboard reports
    dashboard_reports = DashboardReport.objects.filter(
        dashboard=dashboard
    ).select_related('report_type')
    
    data = []
    for dashboard_report in dashboard_reports:
        report_data = {
            'id': dashboard_report.id,
            'report_type_id': dashboard_report.report_type.id,
            'report_type_name': dashboard_report.report_type.name,
            'title': dashboard_report.title or dashboard_report.report_type.name,
            'position_x': dashboard_report.position_x,
            'position_y': dashboard_report.position_y,
            'width': dashboard_report.width,
            'height': dashboard_report.height,
            'show_title': dashboard_report.show_title,
            'refresh_interval': dashboard_report.refresh_interval,
            'parameters': dashboard_report.parameters,
        }
        data.append(report_data)
    
    return JsonResponse({
        'dashboard_id': dashboard.id,
        'dashboard_name': dashboard.name,
        'reports': data,
    })

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_date_range(form):
    """Calculate date range based on form data."""
    period = form.cleaned_data['period']
    date_from = form.cleaned_data.get('date_from')
    date_to = form.cleaned_data.get('date_to')
    
    today = timezone.now().date()
    
    if period == 'today':
        return today, today
    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == 'this_week':
        date_from = today - timedelta(days=today.weekday())
        date_to = date_from + timedelta(days=6)
        return date_from, date_to
    elif period == 'last_week':
        date_from = today - timedelta(days=today.weekday() + 7)
        date_to = date_from + timedelta(days=6)
        return date_from, date_to
    elif period == 'this_month':
        date_from = today.replace(day=1)
        if today.month == 12:
            date_to = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            date_to = today.replace(month=today.month+1, day=1) - timedelta(days=1)
        return date_from, date_to
    elif period == 'last_month':
        if today.month == 1:
            date_from = today.replace(year=today.year-1, month=12, day=1)
        else:
            date_from = today.replace(month=today.month-1, day=1)
        date_to = today.replace(day=1) - timedelta(days=1)
        return date_from, date_to
    elif period == 'this_quarter':
        quarter = (today.month - 1) // 3 + 1
        date_from = today.replace(month=3*(quarter-1)+1, day=1)
        if quarter == 4:
            date_to = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            date_to = today.replace(month=3*quarter+1, day=1) - timedelta(days=1)
        return date_from, date_to
    elif period == 'this_year':
        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)
        return date_from, date_to
    else:  # custom
        return date_from, date_to


def generate_report_data(category, date_from, date_to, params, user):
    """Generate report data based on category."""
    if category == 'compliance':
        return generate_compliance_data(date_from, date_to, params, user)
    elif category == 'performance':
        return generate_performance_data(params, user)
    elif category == 'statistical':
        return generate_statistical_data(date_from, date_to, params, user)
    elif category == 'operational':
        return generate_operational_data(date_from, date_to, params, user)
    elif category == 'analytical':
        return generate_analytical_data(date_from, date_to, params, user)
    else:
        return generate_general_data(date_from, date_to, params, user)


def generate_compliance_data(date_from, date_to, params, user):
    """Generate compliance report data."""
    # Base query for check-ins
    checkins = CheckIn.objects.filter(
        scheduled_time__date__range=[date_from, date_to]
    )
    
    # Apply filters
    if params.get('officer'):
        officer_cases = Case.objects.filter(
            probation_officer__username__icontains=params['officer']
        )
        offender_ids = officer_cases.values_list('offender_id', flat=True)
        checkins = checkins.filter(offender_id__in=offender_ids)
    
    if params.get('offender'):
        checkins = checkins.filter(offender__name__icontains=params['offender'])
    
    if params.get('location'):
        checkins = checkins.filter(location__icontains=params['location'])
    
    # Calculate check-in statistics
    checkin_stats = checkins.aggregate(
        total=Count('id'),
        on_time=Count('id', filter=Q(status='on_time')),
        late=Count('id', filter=Q(status='late')),
        missed=Count('id', filter=Q(status='missed')),
        excused=Count('id', filter=Q(status='excused')),
    )
    
    # Calculate compliance rate
    total_checkins = checkin_stats['total'] or 0
    compliant_checkins = (checkin_stats['on_time'] or 0) + (checkin_stats['excused'] or 0)
    compliance_rate = (compliant_checkins / total_checkins * 100) if total_checkins > 0 else 0
    
    # Get GPS monitoring data
    gps_data = GPSMonitoring.objects.filter(
        last_update__date__range=[date_from, date_to]
    )
    
    gps_stats = gps_data.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        violations=Count('id', filter=Q(violation_flag=True)),
    )
    
    # Get drug test data
    drug_tests = DrugTest.objects.filter(
        test_date__range=[date_from, date_to]
    )
    
    drug_stats = drug_tests.aggregate(
        total=Count('id'),
        positive=Count('id', filter=Q(result='positive')),
        negative=Count('id', filter=Q(result='negative')),
        missed=Count('id', filter=Q(status='missed')),
    )
    
    # Get offenders with compliance data
    offenders = Offender.objects.all()
    offender_compliance = []
    
    for offender in offenders[:50]:  # Limit to 50 offenders
        offender_checkins = checkins.filter(offender=offender)
        offender_total = offender_checkins.count()
        offender_compliant = offender_checkins.filter(
            status__in=['on_time', 'excused']
        ).count()
        offender_rate = (offender_compliant / offender_total * 100) if offender_total > 0 else 0
        
        # Apply minimum compliance filter if specified
        if params.get('min_compliance'):
            min_compliance = int(params['min_compliance'])
            if offender_rate < min_compliance:
                continue
        
        offender_compliance.append({
            'offender': offender,
            'total_checkins': offender_total,
            'compliant_checkins': offender_compliant,
            'compliance_rate': round(offender_rate, 1),
        })
    
    # Sort by compliance rate
    offender_compliance.sort(key=lambda x: x['compliance_rate'], reverse=True)
    
    return {
        'date_from': date_from,
        'date_to': date_to,
        'checkin_stats': checkin_stats,
        'gps_stats': gps_stats,
        'drug_stats': drug_stats,
        'overall_compliance': round(compliance_rate, 1),
        'offender_compliance': offender_compliance[:20],  # Return top 20
        'params': params,
    }


def generate_performance_data(params, user):
    """Generate performance report data."""
    report_type = params.get('report_type', 'officer_performance')
    
    if report_type == 'officer_performance':
        # Get officer performance data
        from accounts.models import User
        officers = User.objects.filter(role='officer')
        
        officer_performance = []
        for officer in officers:
            cases = Case.objects.filter(probation_officer=officer)
            offender_ids = cases.values_list('offender_id', flat=True)
            
            # Check-in performance
            checkins = CheckIn.objects.filter(
                offender_id__in=offender_ids,
                scheduled_time__date__gte=timezone.now().date() - timedelta(days=30)
            )
            
            checkin_stats = checkins.aggregate(
                total=Count('id'),
                compliant=Count('id', filter=Q(status__in=['on_time', 'excused'])),
            )
            
            total_checkins = checkin_stats['total'] or 0
            compliant_checkins = checkin_stats['compliant'] or 0
            compliance_rate = (compliant_checkins / total_checkins * 100) if total_checkins > 0 else 0
            
            officer_performance.append({
                'officer': officer,
                'total_cases': cases.count(),
                'total_checkins': total_checkins,
                'compliant_checkins': compliant_checkins,
                'compliance_rate': round(compliance_rate, 1),
            })
        
        # Sort by compliance rate
        officer_performance.sort(key=lambda x: x['compliance_rate'], reverse=True)
        
        return {
            'report_type': 'Officer Performance',
            'officer_performance': officer_performance,
            'params': params,
        }
    
    elif report_type == 'program_effectiveness':
        # Get program effectiveness data
        programs = Program.objects.filter(is_active=True)
        
        program_effectiveness = []
        for program in programs:
            participants = ProgramParticipation.objects.filter(program=program)
            
            program_effectiveness.append({
                'program': program,
                'total_participants': participants.count(),
                'active_participants': participants.filter(status='active').count(),
                'completed': participants.filter(status='completed').count(),
                'dropout_rate': round(
                    (participants.filter(status='dropped').count() / participants.count() * 100)
                    if participants.count() > 0 else 0, 1
                ),
            })
        
        return {
            'report_type': 'Program Effectiveness',
            'program_effectiveness': program_effectiveness,
            'params': params,
        }
    
    return {}


def generate_statistical_data(date_from, date_to, params, user):
    """Generate statistical report data."""
    # Demographic statistics
    demographics = Offender.objects.aggregate(
        total=Count('id'),
        male=Count('id', filter=Q(gender='M')),
        female=Count('id', filter=Q(gender='F')),
        avg_age=Avg('age'),
        min_age=Min('age'),
        max_age=Max('age'),
    )
    
    # Offense type distribution
    offense_types = Case.objects.values('offense_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Risk level distribution
    risk_levels = Offender.objects.values('risk_level').annotate(
        count=Count('id')
    ).order_by('risk_level')
    
    # Geographic distribution
    locations = Offender.objects.values('county').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Monthly trend
    monthly_trend = []
    current = date_from.replace(day=1)
    while current <= date_to:
        month_end = current.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        month_cases = Case.objects.filter(
            date_opened__range=[current, month_end]
        ).count()
        
        monthly_trend.append({
            'month': current.strftime('%b %Y'),
            'cases': month_cases,
        })
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)
    
    return {
        'date_from': date_from,
        'date_to': date_to,
        'demographics': demographics,
        'offense_types': list(offense_types),
        'risk_levels': list(risk_levels),
        'locations': list(locations),
        'monthly_trend': monthly_trend,
        'params': params,
    }


def generate_operational_data(date_from, date_to, params, user):
    """Generate operational report data."""
    # Case statistics
    case_stats = Case.objects.filter(
        date_opened__date__range=[date_from, date_to]
    ).aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        closed=Count('id', filter=Q(status='closed')),
        suspended=Count('id', filter=Q(status='suspended')),
    )
    
    # Check-in statistics
    checkin_stats = CheckIn.objects.filter(
        scheduled_time__date__range=[date_from, date_to]
    ).aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status__in=['on_time', 'late', 'excused'])),
        missed=Count('id', filter=Q(status='missed')),
    )
    
    # Alert statistics
    alert_stats = Alert.objects.filter(
        created_at__date__range=[date_from, date_to]
    ).aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        resolved=Count('id', filter=Q(status='resolved')),
        critical=Count('id', filter=Q(severity='critical')),
    )
    
    return {
        'date_from': date_from,
        'date_to': date_to,
        'case_stats': case_stats,
        'checkin_stats': checkin_stats,
        'alert_stats': alert_stats,
        'params': params,
    }


def generate_analytical_data(date_from, date_to, params, user):
    """Generate analytical report data."""
    # Recidivism analysis (simplified)
    closed_cases = Case.objects.filter(
        status='closed',
        date_closed__date__range=[date_from, date_to]
    )
    
    recidivism_stats = {
        'total_closed': closed_cases.count(),
        'reopened': closed_cases.filter(reopened=True).count(),
        'recidivism_rate': round(
            (closed_cases.filter(reopened=True).count() / closed_cases.count() * 100)
            if closed_cases.count() > 0 else 0, 1
        ),
    }
    
    # Risk assessment accuracy (simplified)
    offenders = Offender.objects.all()
    risk_assessment_accuracy = []
    
    for offender in offenders[:50]:
        # This is a simplified example - in reality, you'd compare predicted vs actual outcomes
        risk_assessment_accuracy.append({
            'offender': offender,
            'risk_level': offender.risk_level,
            'compliance_score': offender.compliance_score or 0,
            'alerts_count': Alert.objects.filter(offender=offender).count(),
        })
    
    return {
        'date_from': date_from,
        'date_to': date_to,
        'recidivism_stats': recidivism_stats,
        'risk_assessment_accuracy': risk_assessment_accuracy[:20],
        'params': params,
    }


def generate_general_data(date_from, date_to, params, user):
    """Generate general report data."""
    # Basic system statistics
    stats = {
        'total_offenders': Offender.objects.count(),
        'active_cases': Case.objects.filter(status='active').count(),
        'total_checkins': CheckIn.objects.filter(
            scheduled_time__date__range=[date_from, date_to]
        ).count(),
        'active_gps': GPSMonitoring.objects.filter(status='active').count(),
        'pending_alerts': Alert.objects.filter(status='pending').count(),
        'active_programs': Program.objects.filter(is_active=True).count(),
    }
    
    return {
        'date_from': date_from,
        'date_to': date_to,
        'stats': stats,
        'params': params,
    }


def create_report_file(generated_report, report_data, format_type, include_charts=False):
    """Create report file in specified format."""
    if format_type == 'pdf':
        return create_pdf_report(generated_report, report_data, include_charts)
    elif format_type == 'excel':
        return create_excel_report(generated_report, report_data)
    elif format_type == 'csv':
        return create_csv_report(generated_report, report_data)
    elif format_type == 'html':
        return create_html_report(generated_report, report_data, include_charts)
    else:
        return create_pdf_report(generated_report, report_data, include_charts)


def create_pdf_report(generated_report, report_data, include_charts=False):
    """Create PDF report."""
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Content
    content = []
    
    # Title
    title = Paragraph(generated_report.title, title_style)
    content.append(title)
    
    # Report info
    info_data = [
        ['Generated By:', generated_report.generated_by.get_full_name()],
        ['Generation Date:', generated_report.generation_date.strftime('%Y-%m-%d %H:%M')],
        ['Period:', f"{generated_report.period_start} to {generated_report.period_end}"],
        ['Report Type:', generated_report.report_type.name],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    content.append(info_table)
    content.append(Spacer(1, 20))
    
    # Add report-specific content based on category
    category = generated_report.report_type.category
    
    if category == 'compliance':
        content.extend(create_compliance_pdf_content(report_data, heading_style, normal_style))
    elif category == 'performance':
        content.extend(create_performance_pdf_content(report_data, heading_style, normal_style))
    elif category == 'statistical':
        content.extend(create_statistical_pdf_content(report_data, heading_style, normal_style))
    elif category == 'operational':
        content.extend(create_operational_pdf_content(report_data, heading_style, normal_style))
    else:
        content.extend(create_general_pdf_content(report_data, heading_style, normal_style))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    return buffer


def create_compliance_pdf_content(report_data, heading_style, normal_style):
    """Create compliance report PDF content."""
    content = []
    
    # Overall compliance
    content.append(Paragraph("Overall Compliance", heading_style))
    content.append(Paragraph(f"Compliance Rate: {report_data.get('overall_compliance', 0)}%", normal_style))
    
    # Check-in statistics
    content.append(Paragraph("Check-in Statistics", heading_style))
    checkin_stats = report_data.get('checkin_stats', {})
    
    checkin_data = [
        ['Metric', 'Count'],
        ['Total Check-ins', checkin_stats.get('total', 0)],
        ['On Time', checkin_stats.get('on_time', 0)],
        ['Late', checkin_stats.get('late', 0)],
        ['Missed', checkin_stats.get('missed', 0)],
        ['Excused', checkin_stats.get('excused', 0)],
    ]
    
    checkin_table = Table(checkin_data, colWidths=[2.5*inch, 1.5*inch])
    checkin_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e73df')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
    ]))
    
    content.append(checkin_table)
    content.append(Spacer(1, 15))
    
    # Offender compliance
    content.append(Paragraph("Top Offenders by Compliance", heading_style))
    offender_compliance = report_data.get('offender_compliance', [])
    
    if offender_compliance:
        offender_data = [['Offender', 'Total Check-ins', 'Compliant', 'Compliance Rate']]
        for offender in offender_compliance[:10]:  # Top 10
            offender_data.append([
                offender['offender'].name,
                offender['total_checkins'],
                offender['compliant_checkins'],
                f"{offender['compliance_rate']}%",
            ])
        
        offender_table = Table(offender_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        offender_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1cc88a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
        ]))
        
        content.append(offender_table)
    
    return content


def create_performance_pdf_content(report_data, heading_style, normal_style):
    """Create performance report PDF content."""
    content = []
    
    report_type = report_data.get('report_type', '')
    content.append(Paragraph(report_type, heading_style))
    
    if report_type == 'Officer Performance':
        officer_performance = report_data.get('officer_performance', [])
        
        if officer_performance:
            officer_data = [['Officer', 'Total Cases', 'Check-ins', 'Compliant', 'Rate']]
            for officer in officer_performance:
                officer_data.append([
                    officer['officer'].get_full_name(),
                    officer['total_cases'],
                    officer['total_checkins'],
                    officer['compliant_checkins'],
                    f"{officer['compliance_rate']}%",
                ])
            
            officer_table = Table(officer_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 1*inch])
            officer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#36b9cc')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
            ]))
            
            content.append(officer_table)
    
    return content


def create_statistical_pdf_content(report_data, heading_style, normal_style):
    """Create statistical report PDF content."""
    content = []
    
    # Demographics
    content.append(Paragraph("Demographics", heading_style))
    demographics = report_data.get('demographics', {})
    
    demo_data = [
        ['Total Offenders', demographics.get('total', 0)],
        ['Male', demographics.get('male', 0)],
        ['Female', demographics.get('female', 0)],
        ['Average Age', f"{demographics.get('avg_age', 0):.1f}"],
        ['Age Range', f"{demographics.get('min_age', 0)} - {demographics.get('max_age', 0)}"],
    ]
    
    demo_table = Table(demo_data, colWidths=[2.5*inch, 1.5*inch])
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e73df')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
    ]))
    
    content.append(demo_table)
    content.append(Spacer(1, 15))
    
    # Offense types
    content.append(Paragraph("Top Offense Types", heading_style))
    offense_types = report_data.get('offense_types', [])
    
    if offense_types:
        offense_data = [['Offense Type', 'Count']]
        for offense in offense_types[:10]:
            offense_data.append([offense.get('offense_type', 'Unknown'), offense.get('count', 0)])
        
        offense_table = Table(offense_data, colWidths=[3*inch, 1.5*inch])
        offense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1cc88a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
        ]))
        
        content.append(offense_table)
    
    return content


def create_operational_pdf_content(report_data, heading_style, normal_style):
    """Create operational report PDF content."""
    content = []
    
    # Case statistics
    content.append(Paragraph("Case Statistics", heading_style))
    case_stats = report_data.get('case_stats', {})
    
    case_data = [
        ['Metric', 'Count'],
        ['Total Cases', case_stats.get('total', 0)],
        ['Active', case_stats.get('active', 0)],
        ['Closed', case_stats.get('closed', 0)],
        ['Suspended', case_stats.get('suspended', 0)],
    ]
    
    case_table = Table(case_data, colWidths=[2.5*inch, 1.5*inch])
    case_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e73df')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
    ]))
    
    content.append(case_table)
    content.append(Spacer(1, 15))
    
    # Alert statistics
    content.append(Paragraph("Alert Statistics", heading_style))
    alert_stats = report_data.get('alert_stats', {})
    
    alert_data = [
        ['Metric', 'Count'],
        ['Total Alerts', alert_stats.get('total', 0)],
        ['Pending', alert_stats.get('pending', 0)],
        ['Resolved', alert_stats.get('resolved', 0)],
        ['Critical', alert_stats.get('critical', 0)],
    ]
    
    alert_table = Table(alert_data, colWidths=[2.5*inch, 1.5*inch])
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#36b9cc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
    ]))
    
    content.append(alert_table)
    
    return content


def create_general_pdf_content(report_data, heading_style, normal_style):
    """Create general report PDF content."""
    content = []
    
    content.append(Paragraph("System Statistics", heading_style))
    stats = report_data.get('stats', {})
    
    stats_data = [
        ['Metric', 'Count'],
        ['Total Offenders', stats.get('total_offenders', 0)],
        ['Active Cases', stats.get('active_cases', 0)],
        ['Total Check-ins', stats.get('total_checkins', 0)],
        ['Active GPS Monitors', stats.get('active_gps', 0)],
        ['Pending Alerts', stats.get('pending_alerts', 0)],
        ['Active Programs', stats.get('active_programs', 0)],
    ]
    
    stats_table = Table(stats_data, colWidths=[2.5*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4e73df')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e3e6f0')),
    ]))
    
    content.append(stats_table)
    
    return content


def create_excel_report(generated_report, report_data):
    """Create Excel report."""
    from io import BytesIO
    
    buffer = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    
    # Add headers
    ws.append(['Report:', generated_report.title])
    ws.append(['Generated By:', generated_report.generated_by.get_full_name()])
    ws.append(['Generation Date:', generated_report.generation_date.strftime('%Y-%m-%d %H:%M')])
    ws.append(['Period:', f"{generated_report.period_start} to {generated_report.period_end}"])
    ws.append(['Report Type:', generated_report.report_type.name])
    ws.append([])
    
    # Add report data based on category
    category = generated_report.report_type.category
    
    if category == 'compliance':
        # Overall compliance
        ws.append(['Overall Compliance'])
        ws.append(['Compliance Rate:', f"{report_data.get('overall_compliance', 0)}%"])
        ws.append([])
        
        # Check-in statistics
        ws.append(['Check-in Statistics'])
        checkin_stats = report_data.get('checkin_stats', {})
        ws.append(['Metric', 'Count'])
        ws.append(['Total Check-ins', checkin_stats.get('total', 0)])
        ws.append(['On Time', checkin_stats.get('on_time', 0)])
        ws.append(['Late', checkin_stats.get('late', 0)])
        ws.append(['Missed', checkin_stats.get('missed', 0)])
        ws.append(['Excused', checkin_stats.get('excused', 0)])
        ws.append([])
        
        # Offender compliance
        ws.append(['Top Offenders by Compliance'])
        offender_compliance = report_data.get('offerder_compliance', [])
        if offender_compliance:
            ws.append(['Offender', 'Total Check-ins', 'Compliant', 'Compliance Rate'])
            for offender in offender_compliance[:20]:
                ws.append([
                    offender['offender'].name,
                    offender['total_checkins'],
                    offender['compliant_checkins'],
                    f"{offender['compliance_rate']}%",
                ])
    
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer


def create_csv_report(generated_report, report_data):
    """Create CSV report."""
    from io import StringIO
    
    buffer = StringIO()
    writer = csv.writer(buffer)
    
    # Write headers
    writer.writerow(['Report:', generated_report.title])
    writer.writerow(['Generated By:', generated_report.generated_by.get_full_name()])
    writer.writerow(['Generation Date:', generated_report.generation_date.strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Period:', f"{generated_report.period_start} to {generated_report.period_end}"])
    writer.writerow(['Report Type:', generated_report.report_type.name])
    writer.writerow([])
    
    # Write data based on category
    category = generated_report.report_type.category
    
    if category == 'compliance':
        writer.writerow(['Overall Compliance'])
        writer.writerow(['Compliance Rate:', f"{report_data.get('overall_compliance', 0)}%"])
        writer.writerow([])
        
        writer.writerow(['Check-in Statistics'])
        checkin_stats = report_data.get('checkin_stats', {})
        writer.writerow(['Metric', 'Count'])
        writer.writerow(['Total Check-ins', checkin_stats.get('total', 0)])
        writer.writerow(['On Time', checkin_stats.get('on_time', 0)])
        writer.writerow(['Late', checkin_stats.get('late', 0)])
        writer.writerow(['Missed', checkin_stats.get('missed', 0)])
        writer.writerow(['Excused', checkin_stats.get('excused', 0)])
    
    # Convert StringIO to BytesIO
    from io import BytesIO
    bytes_buffer = BytesIO(buffer.getvalue().encode('utf-8'))
    bytes_buffer.seek(0)
    
    return bytes_buffer


def create_html_report(generated_report, report_data, include_charts=False):
    """Create HTML report."""
    from io import BytesIO
    
    # Render HTML template
    html_content = render_to_string('reports/html_report_template.html', {
        'report': generated_report,
        'report_data': report_data,
        'include_charts': include_charts,
        'generated_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    })
    
    buffer = BytesIO(html_content.encode('utf-8'))
    buffer.seek(0)
    
    return buffer


def create_compliance_pdf(generated_report, report_data):
    """Create compliance-specific PDF report."""
    return create_pdf_report(generated_report, report_data, True)


def create_performance_pdf(generated_report, report_data):
    """Create performance-specific PDF report."""
    return create_pdf_report(generated_report, report_data, True)


def get_file_extension(format_type):
    """Get file extension for format type."""
    extensions = {
        'pdf': 'pdf',
        'excel': 'xlsx',
        'csv': 'csv',
        'html': 'html',
        'json': 'json',
    }
    return extensions.get(format_type, 'pdf')


def send_report_email(generated_report, recipient_email):
    """Send report via email (placeholder)."""
    # In a real implementation, you would use Django's email system
    # For example:
    # from django.core.mail import EmailMessage
    # email = EmailMessage(
    #     subject=f'Report: {generated_report.title}',
    #     body='Please find the attached report.',
    #     from_email='reports@probation-system.com',
    #     to=[recipient_email],
    # )
    # email.attach_file(generated_report.file.path)
    # email.send()
    pass


# ============================================================================
# CRON JOB VIEWS (For scheduled reports)
# ============================================================================

@csrf_exempt
def process_scheduled_reports(request):
    """Process scheduled reports (to be called by cron job)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Verify cron secret (in production, use proper authentication)
    secret = request.POST.get('secret')
    if secret != getattr(settings, 'CRON_SECRET', 'default_secret'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    now = timezone.now()
    today = now.date()
    
    # Get active schedules that are due
    schedules = ReportSchedule.objects.filter(
        Q(status='active'),
        Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gte=today),
        Q(next_run__lte=now) | Q(next_run__isnull=True)
    )
    
    processed = 0
    errors = []
    
    for schedule in schedules:
        try:
            # Generate report for each recipient
            for recipient in schedule.recipients.all():
                # Create GeneratedReport record
                generated_report = GeneratedReport.objects.create(
                    report_type=schedule.report_type,
                    title=f"{schedule.report_type.name} - {schedule.frequency} - {today}",
                    description=f"Scheduled report generated for {recipient.get_full_name()}",
                    generated_by=schedule.created_by,
                    period_start=today - timedelta(days=1),  # Yesterday
                    period_end=today,
                    file_format='pdf',
                    parameters=schedule.parameters,
                    schedule=schedule,
                )
                
                # Generate report data
                report_data = generate_report_data(
                    schedule.report_type.category,
                    generated_report.period_start,
                    generated_report.period_end,
                    schedule.parameters,
                    schedule.created_by
                )
                
                # Create PDF report
                file_content = create_pdf_report(generated_report, report_data, True)
                
                # Save file
                filename = f"scheduled_{schedule.id}_{today.strftime('%Y%m%d')}.pdf"
                generated_report.file.save(filename, file_content)
                generated_report.status = 'completed'
                generated_report.save()
                
                # Send email if configured
                if schedule.send_email:
                    send_report_email(generated_report, recipient.email)
            
            # Update schedule
            schedule.last_run = now
            schedule.next_run = schedule.calculate_next_run()
            schedule.save()
            
            processed += 1
            
        except Exception as e:
            errors.append(f"Schedule {schedule.id}: {str(e)}")
    
    return JsonResponse({
        'processed': processed,
        'errors': errors,
        'total_schedules': schedules.count(),
    })
