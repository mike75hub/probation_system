"""
Views for monitoring app.
"""
import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Avg, Q, Sum, Case, When, Value, IntegerField
from django.db.models.functions import TruncMonth, TruncWeek
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
import csv
from io import StringIO

from .models import (
    CheckIn, CheckInType, GPSMonitoring, GPSLocation, 
    DrugTest, EmploymentVerification, Alert
)
from .forms import (
    CheckInForm, CheckInTypeForm, GPSMonitoringForm, GPSLocationForm,
    DrugTestForm, EmploymentVerificationForm, AlertForm,
    CheckInSearchForm, ComplianceReportForm
)
from offenders.models import Offender, Case
from accounts.models import User

# Check-in Type Views
@method_decorator(login_required, name='dispatch')
class CheckInTypeListView(ListView):
    model = CheckInType
    template_name = 'monitoring/checkintype_list.html'
    context_object_name = 'checkin_types'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Check-in Types'
        return context

@method_decorator(login_required, name='dispatch')
class CheckInTypeCreateView(CreateView):
    model = CheckInType
    form_class = CheckInTypeForm
    template_name = 'monitoring/checkintype_form.html'
    success_url = reverse_lazy('monitoring:checkintype_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Check-in type created successfully!')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class CheckInTypeUpdateView(UpdateView):
    model = CheckInType
    form_class = CheckInTypeForm
    template_name = 'monitoring/checkintype_form.html'
    success_url = reverse_lazy('monitoring:checkintype_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Check-in type updated successfully!')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class CheckInTypeDeleteView(DeleteView):
    model = CheckInType
    template_name = 'monitoring/checkintype_delete.html'
    success_url = reverse_lazy('monitoring:checkintype_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Check-in type deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Check-in Views
@method_decorator(login_required, name='dispatch')
class CheckInListView(ListView):
    model = CheckIn
    template_name = 'monitoring/checkin_list.html'
    context_object_name = 'checkins'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply filters
        status = self.request.GET.get('status')
        offender = self.request.GET.get('offender')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        officer = self.request.GET.get('officer')
        
        if status:
            queryset = queryset.filter(status=status)
        if offender:
            queryset = queryset.filter(
                Q(offender__user__first_name__icontains=offender) |
                Q(offender__user__last_name__icontains=offender)
            )
        if date_from:
            queryset = queryset.filter(scheduled_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__date__lte=date_to)
        if officer:
            queryset = queryset.filter(probation_officer_id=officer)
        
        # For officers, show only their check-ins
        if self.request.user.is_officer:
            queryset = queryset.filter(probation_officer=self.request.user)
        
        return queryset.order_by('-scheduled_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Check-ins'
        context['search_form'] = CheckInSearchForm(self.request.GET or None)
        
        # Statistics
        context['total_checkins'] = CheckIn.objects.count()
        context['completed_checkins'] = CheckIn.objects.filter(status='completed').count()
        context['missed_checkins'] = CheckIn.objects.filter(status='missed').count()
        context['upcoming_checkins'] = CheckIn.objects.filter(
            status='scheduled',
            scheduled_date__gte=timezone.now()
        ).count()
        
        # Overdue check-ins
        context['overdue_checkins'] = CheckIn.objects.filter(
            status='scheduled',
            scheduled_date__lt=timezone.now()
        ).count()
        
        return context

@method_decorator(login_required, name='dispatch')
class CheckInDetailView(DetailView):
    model = CheckIn
    template_name = 'monitoring/checkin_detail.html'
    context_object_name = 'checkin'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        checkin = self.object
        context['title'] = f'Check-in: {checkin.offender}'
        
        # Get previous check-ins for this offender
        context['previous_checkins'] = CheckIn.objects.filter(
            offender=checkin.offender
        ).exclude(pk=checkin.pk).order_by('-scheduled_date')[:5]
        
        return context

@method_decorator(login_required, name='dispatch')
class CheckInCreateView(CreateView):
    model = CheckIn
    form_class = CheckInForm
    template_name = 'monitoring/checkin_form.html'
    success_url = reverse_lazy('monitoring:checkin_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Set initial probation officer to current user if they're an officer
        if self.request.user.is_officer:
            initial['probation_officer'] = self.request.user
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Check-in created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Schedule Check-in'
        return context

@method_decorator(login_required, name='dispatch')
class CheckInUpdateView(UpdateView):
    model = CheckIn
    form_class = CheckInForm
    template_name = 'monitoring/checkin_form.html'
    
    def get_success_url(self):
        return reverse_lazy('monitoring:checkin_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # If marking as completed, set actual date to now if not set
        if form.instance.status == 'completed' and not form.instance.actual_date:
            form.instance.actual_date = timezone.now()
        
        messages.success(self.request, 'Check-in updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Check-in'
        return context

@method_decorator(login_required, name='dispatch')
class CheckInDeleteView(DeleteView):
    model = CheckIn
    template_name = 'monitoring/checkin_delete.html'
    success_url = reverse_lazy('monitoring:checkin_list')
    
    def delete(self, request, *args, **kwargs):
        checkin = self.get_object()
        messages.success(request, f'Check-in deleted successfully!')
        return super().delete(request, *args, **kwargs)

# GPS Monitoring Views
@method_decorator(login_required, name='dispatch')
class GPSMonitoringListView(ListView):
    model = GPSMonitoring
    template_name = 'monitoring/gps_list.html'
    context_object_name = 'gps_monitorings'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by device status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(device_status=status)
        
        # Filter by offender if provided
        offender = self.request.GET.get('offender')
        if offender:
            queryset = queryset.filter(
                Q(offender__user__first_name__icontains=offender) |
                Q(offender__user__last_name__icontains=offender)
            )
        
        return queryset.order_by('-issued_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'GPS Monitoring'
        
        # Statistics
        context['total_devices'] = GPSMonitoring.objects.count()
        context['active_devices'] = GPSMonitoring.objects.filter(device_status='active').count()
        context['expired_devices'] = GPSMonitoring.objects.filter(
            monitoring_end_date__lt=timezone.now().date(),
            device_status='active'
        ).count()
        
        return context

@method_decorator(login_required, name='dispatch')
class GPSMonitoringDetailView(DetailView):
    model = GPSMonitoring
    template_name = 'monitoring/gps_detail.html'
    context_object_name = 'gps_monitoring'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gps = self.object
        
        context['title'] = f'GPS Monitoring: {gps.device_id}'
        
        # Get recent locations
        context['recent_locations'] = gps.locations.order_by('-timestamp')[:50]
        
        # Get statistics
        context['total_locations'] = gps.locations.count()
        context['restricted_zone_violations'] = gps.locations.filter(
            is_in_restricted_zone=True
        ).count()
        context['curfew_violations'] = gps.locations.filter(
            is_curfew_violation=True
        ).count()
        
        # Get last 24 hours locations for map
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        context['recent_locations_map'] = gps.locations.filter(
            timestamp__gte=twenty_four_hours_ago
        ).order_by('timestamp')
        
        return context

@method_decorator(login_required, name='dispatch')
class GPSMonitoringCreateView(CreateView):
    model = GPSMonitoring
    form_class = GPSMonitoringForm
    template_name = 'monitoring/gps_form.html'
    success_url = reverse_lazy('monitoring:gps_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'GPS monitoring created successfully!')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class GPSMonitoringUpdateView(UpdateView):
    model = GPSMonitoring
    form_class = GPSMonitoringForm
    template_name = 'monitoring/gps_form.html'
    
    def get_success_url(self):
        return reverse_lazy('monitoring:gps_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'GPS monitoring updated successfully!')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class GPSMonitoringDeleteView(DeleteView):
    model = GPSMonitoring
    template_name = 'monitoring/gps_delete.html'
    success_url = reverse_lazy('monitoring:gps_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'GPS monitoring deleted successfully!')
        return super().delete(request, *args, **kwargs)

# Drug Test Views
@method_decorator(login_required, name='dispatch')
class DrugTestListView(ListView):
    model = DrugTest
    template_name = 'monitoring/drugtest_list.html'
    context_object_name = 'drug_tests'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by result if provided
        result = self.request.GET.get('result')
        if result:
            queryset = queryset.filter(result=result)
        
        # Filter by offender if provided
        offender = self.request.GET.get('offender')
        if offender:
            queryset = queryset.filter(
                Q(offender__user__first_name__icontains=offender) |
                Q(offender__user__last_name__icontains=offender)
            )
        
        # Filter by date range if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(test_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(test_date__date__lte=date_to)
        
        return queryset.order_by('-test_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Drug Tests'
        
        # Statistics
        context['total_tests'] = DrugTest.objects.count()
        context['positive_tests'] = DrugTest.objects.filter(result='positive').count()
        context['negative_tests'] = DrugTest.objects.filter(result='negative').count()
        context['positive_rate'] = (
            context['positive_tests'] / context['total_tests'] * 100 
            if context['total_tests'] > 0 else 0
        )
        
        return context

@method_decorator(login_required, name='dispatch')
class DrugTestDetailView(DetailView):
    model = DrugTest
    template_name = 'monitoring/drugtest_detail.html'
    context_object_name = 'drug_test'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        drug_test = self.object
        context['title'] = f'Drug Test: {drug_test.offender} - {drug_test.test_date.strftime("%Y-%m-%d")}'
        
        # Get previous drug tests for this offender
        context['previous_tests'] = DrugTest.objects.filter(
            offender=drug_test.offender
        ).exclude(pk=drug_test.pk).order_by('-test_date')[:5]
        
        # Get statistics for this offender
        context['offender_total_tests'] = DrugTest.objects.filter(
            offender=drug_test.offender
        ).count()
        context['offender_positive_tests'] = DrugTest.objects.filter(
            offender=drug_test.offender,
            result='positive'
        ).count()
        
        # Calculate positive percentage
        if context['offender_total_tests'] > 0:
            context['offender_positive_percentage'] = (
                context['offender_positive_tests'] / context['offender_total_tests'] * 100
            )
        else:
            context['offender_positive_percentage'] = 0
        
        return context

@method_decorator(login_required, name='dispatch')
class DrugTestCreateView(CreateView):
    model = DrugTest
    form_class = DrugTestForm
    template_name = 'monitoring/drugtest_form.html'
    success_url = reverse_lazy('monitoring:drugtest_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Set conducted by to current user
        initial['conducted_by'] = self.request.user
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, 'Drug test recorded successfully!')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class DrugTestUpdateView(UpdateView):
    model = DrugTest
    form_class = DrugTestForm
    template_name = 'monitoring/drugtest_form.html'
    
    def get_success_url(self):
        return reverse_lazy('monitoring:drugtest_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Drug test updated successfully!')
        return super().form_valid(form)

# Employment Verification Views
@method_decorator(login_required, name='dispatch')
class EmploymentVerificationListView(ListView):
    model = EmploymentVerification
    template_name = 'monitoring/employment_list.html'
    context_object_name = 'employments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(verification_status=status)
        
        # Filter by offender if provided
        offender = self.request.GET.get('offender')
        if offender:
            queryset = queryset.filter(
                Q(offender__user__first_name__icontains=offender) |
                Q(offender__user__last_name__icontains=offender)
            )
        
        return queryset.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Employment Verification'
        
        # Statistics
        context['total_employments'] = EmploymentVerification.objects.count()
        context['verified_employments'] = EmploymentVerification.objects.filter(
            verification_status='verified'
        ).count()
        context['current_employments'] = EmploymentVerification.objects.filter(
            verification_status='verified',
            end_date__gte=timezone.now().date()
        ).count()
        
        return context

@method_decorator(login_required, name='dispatch')
class EmploymentVerificationDetailView(DetailView):
    model = EmploymentVerification
    template_name = 'monitoring/employment_detail.html'
    context_object_name = 'employment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employment = self.object
        context['title'] = f'Employment Verification: {employment.employer_name}'
        
        # Get related data
        context['offender'] = employment.offender
        context['case'] = employment.case
        
        # Get verification history for this offender
        context['verification_history'] = EmploymentVerification.objects.filter(
            offender=employment.offender
        ).exclude(pk=employment.pk).order_by('-start_date')[:5]
        
        # Get all employment records for this offender
        context['total_employments'] = EmploymentVerification.objects.filter(
            offender=employment.offender
        ).count()
        
        # Get current employment (if any)
        context['current_employment'] = EmploymentVerification.objects.filter(
            offender=employment.offender,
            verification_status='verified',
            end_date__gte=timezone.now().date()
        ).exclude(pk=employment.pk).first()
        
        # Get verification statistics
        context['verified_count'] = EmploymentVerification.objects.filter(
            offender=employment.offender,
            verification_status='verified'
        ).count()
        
        return context

@method_decorator(login_required, name='dispatch')
class EmploymentVerificationCreateView(CreateView):
    model = EmploymentVerification
    form_class = EmploymentVerificationForm
    template_name = 'monitoring/employment_form.html'
    success_url = reverse_lazy('monitoring:employment_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Set created by to current user
        initial['created_by'] = self.request.user
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, 'Employment verification created successfully!')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class EmploymentVerificationUpdateView(UpdateView):
    model = EmploymentVerification
    form_class = EmploymentVerificationForm
    template_name = 'monitoring/employment_form.html'
    
    def get_success_url(self):
        return reverse_lazy('monitoring:employment_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Employment verification updated successfully!')
        return super().form_valid(form)

# Alert Views
@method_decorator(login_required, name='dispatch')
class AlertListView(ListView):
    model = Alert
    template_name = 'monitoring/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by priority if provided
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by offender if provided
        offender = self.request.GET.get('offender')
        if offender:
            queryset = queryset.filter(
                Q(offender__user__first_name__icontains=offender) |
                Q(offender__user__last_name__icontains=offender)
            )
        
        # Show only new and in-progress alerts by default
        if not status:
            queryset = queryset.filter(status__in=['new', 'in_progress'])
        
        return queryset.order_by('-alert_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Alerts'
        
        # Statistics
        context['total_alerts'] = Alert.objects.count()
        context['new_alerts'] = Alert.objects.filter(status='new').count()
        context['critical_alerts'] = Alert.objects.filter(priority='critical').count()
        context['resolved_alerts'] = Alert.objects.filter(status='resolved').count()
        
        return context

@method_decorator(login_required, name='dispatch')
class AlertDetailView(DetailView):
    model = Alert
    template_name = 'monitoring/alert_detail.html'
    context_object_name = 'alert'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Alert: {self.object.title}'
        
        # Get related data
        context['offender'] = self.object.offender
        context['created_by_user'] = self.object.created_by
        
        # Get similar alerts for this offender
        context['similar_alerts'] = Alert.objects.filter(
            offender=self.object.offender,
            alert_type=self.object.alert_type
        ).exclude(pk=self.object.pk).order_by('-alert_time')[:5]
        
        return context

@method_decorator(login_required, name='dispatch')
class AlertUpdateView(UpdateView):
    model = Alert
    form_class = AlertForm
    template_name = 'monitoring/alert_form.html'
    
    def get_success_url(self):
        return reverse_lazy('monitoring:alert_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # If marking as acknowledged, set acknowledged time and user
        if form.instance.status == 'acknowledged' and not form.instance.acknowledged_time:
            form.instance.acknowledged_time = timezone.now()
            form.instance.acknowledged_by = self.request.user
        
        # If marking as resolved, set resolved time and user
        if form.instance.status == 'resolved' and not form.instance.resolved_time:
            form.instance.resolved_time = timezone.now()
            form.instance.resolved_by = self.request.user
        
        messages.success(self.request, 'Alert updated successfully!')
        return super().form_valid(form)

# Function-based Views
@login_required
def monitoring_dashboard(request):
    """Monitoring dashboard view."""
    # Check-in statistics
    total_checkins = CheckIn.objects.count()
    completed_checkins = CheckIn.objects.filter(status='completed').count()
    missed_checkins = CheckIn.objects.filter(status='missed').count()
    compliance_rate = (completed_checkins / total_checkins * 100) if total_checkins > 0 else 0
    
    # GPS statistics
    active_gps_devices = GPSMonitoring.objects.filter(device_status='active').count()
    gps_violations = GPSLocation.objects.filter(
        Q(is_in_restricted_zone=True) | Q(is_curfew_violation=True)
    ).count()
    
    # Drug test statistics
    recent_drug_tests = DrugTest.objects.filter(
        test_date__gte=timezone.now() - timedelta(days=30)
    ).count()
    positive_tests = DrugTest.objects.filter(result='positive').count()
    
    # Alert statistics
    new_alerts = Alert.objects.filter(status='new').count()
    critical_alerts = Alert.objects.filter(priority='critical', status__in=['new', 'in_progress']).count()
    
    # Recent check-ins
    recent_checkins = CheckIn.objects.order_by('-scheduled_date')[:10]
    
    # Recent alerts
    recent_alerts = Alert.objects.filter(status__in=['new', 'in_progress']).order_by('-alert_time')[:10]
    
    # Overdue check-ins
    overdue_checkins = CheckIn.objects.filter(
        status='scheduled',
        scheduled_date__lt=timezone.now()
    ).order_by('scheduled_date')[:10]
    
    context = {
        'title': 'Monitoring Dashboard',
        'total_checkins': total_checkins,
        'completed_checkins': completed_checkins,
        'missed_checkins': missed_checkins,
        'compliance_rate': compliance_rate,
        'active_gps_devices': active_gps_devices,
        'gps_violations': gps_violations,
        'recent_drug_tests': recent_drug_tests,
        'positive_tests': positive_tests,
        'new_alerts': new_alerts,
        'critical_alerts': critical_alerts,
        'recent_checkins': recent_checkins,
        'recent_alerts': recent_alerts,
        'overdue_checkins': overdue_checkins,
    }
    
    return render(request, 'monitoring/dashboard.html', context)

@login_required
def offender_monitoring_summary(request, offender_id):
    """Get monitoring summary for a specific offender."""
    offender = get_object_or_404(Offender, pk=offender_id)
    
    # Check-ins
    checkins = CheckIn.objects.filter(offender=offender).order_by('-scheduled_date')
    completed_checkins = checkins.filter(status='completed').count()
    missed_checkins = checkins.filter(status='missed').count()
    
    # GPS monitoring
    gps_monitoring = GPSMonitoring.objects.filter(offender=offender, device_status='active').first()
    
    # Drug tests
    drug_tests = DrugTest.objects.filter(offender=offender).order_by('-test_date')[:5]
    
    # Employment
    current_employment = EmploymentVerification.objects.filter(
        offender=offender,
        verification_status='verified',
        end_date__gte=timezone.now().date()
    ).first()
    
    # Alerts
    recent_alerts = Alert.objects.filter(offender=offender).order_by('-alert_time')[:5]
    
    context = {
        'title': f'Monitoring Summary: {offender}',
        'offender': offender,
        'checkins': checkins[:10],
        'completed_checkins': completed_checkins,
        'missed_checkins': missed_checkins,
        'gps_monitoring': gps_monitoring,
        'drug_tests': drug_tests,
        'current_employment': current_employment,
        'recent_alerts': recent_alerts,
    }
    
    return render(request, 'monitoring/offender_summary.html', context)

@login_required
def compliance_report(request):
    """Generate compliance report."""
    if request.method == 'POST':
        form = ComplianceReportForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            officer = form.cleaned_data['officer']
            
            # Calculate date range based on report type
            today = timezone.now().date()
            
            if report_type == 'monthly':
                year = form.cleaned_data['year']
                month = form.cleaned_data['month']
                date_from = datetime(year, month, 1).date()
                date_to = datetime(year, month, 1).replace(day=28) + timedelta(days=4)
                date_to = min(date_to.date(), datetime(year, month, 1).replace(day=31).date())
                
            elif report_type == 'quarterly':
                year = form.cleaned_data['year']
                quarter = form.cleaned_data['quarter']
                if quarter == 1:
                    date_from = datetime(year, 1, 1).date()
                    date_to = datetime(year, 3, 31).date()
                elif quarter == 2:
                    date_from = datetime(year, 4, 1).date()
                    date_to = datetime(year, 6, 30).date()
                elif quarter == 3:
                    date_from = datetime(year, 7, 1).date()
                    date_to = datetime(year, 9, 30).date()
                else:  # quarter 4
                    date_from = datetime(year, 10, 1).date()
                    date_to = datetime(year, 12, 31).date()
                    
            elif report_type == 'yearly':
                year = form.cleaned_data['year']
                date_from = datetime(year, 1, 1).date()
                date_to = datetime(year, 12, 31).date()
                
            else:  # custom
                date_from = form.cleaned_data['date_from']
                date_to = form.cleaned_data['date_to']
            
            # Get check-ins for the period
            checkins = CheckIn.objects.filter(
                scheduled_date__date__range=[date_from, date_to]
            )
            
            if officer:
                checkins = checkins.filter(probation_officer=officer)
            
            # Calculate statistics
            total_checkins = checkins.count()
            completed = checkins.filter(status='completed').count()
            missed = checkins.filter(status='missed').count()
            scheduled = checkins.filter(status='scheduled').count()
            
            compliance_rate = (completed / total_checkins * 100) if total_checkins > 0 else 0
            
            # Get check-ins by officer
            checkins_by_officer = checkins.values('probation_officer__first_name', 'probation_officer__last_name').annotate(
                total=Count('id'),
                completed=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
                missed=Count(Case(When(status='missed', then=1), output_field=IntegerField())),
            ).order_by('-total')
            
            # Get check-ins by offender
            top_offenders = checkins.values('offender__user__first_name', 'offender__user__last_name').annotate(
                total=Count('id'),
                completed=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
                missed=Count(Case(When(status='missed', then=1), output_field=IntegerField())),
            ).order_by('-total')[:10]
            
            context = {
                'title': 'Compliance Report',
                'report_type': report_type,
                'date_from': date_from,
                'date_to': date_to,
                'officer': officer,
                'total_checkins': total_checkins,
                'completed': completed,
                'missed': missed,
                'scheduled': scheduled,
                'compliance_rate': compliance_rate,
                'checkins_by_officer': checkins_by_officer,
                'top_offenders': top_offenders,
                'checkins': checkins.order_by('-scheduled_date')[:50],
                'form': form,
            }
            
            return render(request, 'monitoring/compliance_report.html', context)
    
    else:
        form = ComplianceReportForm()
    
    context = {
        'title': 'Generate Compliance Report',
        'form': form,
    }
    
    return render(request, 'monitoring/generate_report.html', context)

@login_required
def export_compliance_report(request):
    """Export compliance report as CSV."""
    # Get parameters from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    officer_id = request.GET.get('officer')
    
    # Get check-ins
    checkins = CheckIn.objects.filter(
        scheduled_date__date__range=[date_from, date_to]
    )
    
    if officer_id:
        checkins = checkins.filter(probation_officer_id=officer_id)
    
    checkins = checkins.select_related('offender', 'probation_officer', 'checkin_type')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="compliance_report_{date_from}_to_{date_to}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Date', 'Time', 'Offender', 'Officer', 'Check-in Type',
        'Status', 'Compliance', 'Location', 'Notes'
    ])
    
    # Write data
    for checkin in checkins:
        writer.writerow([
            checkin.scheduled_date.strftime('%Y-%m-%d'),
            checkin.scheduled_date.strftime('%H:%M'),
            str(checkin.offender),
            f"{checkin.probation_officer.first_name} {checkin.probation_officer.last_name}",
            checkin.checkin_type.name if checkin.checkin_type else '',
            checkin.get_status_display(),
            checkin.get_compliance_level_display() if checkin.compliance_level else '',
            checkin.location,
            checkin.progress_notes[:100]  # First 100 characters
        ])
    
    return response

@login_required
def mark_checkin_completed(request, checkin_id):
    """Mark a check-in as completed."""
    checkin = get_object_or_404(CheckIn, pk=checkin_id)
    
    if request.method == 'POST':
        checkin.status = 'completed'
        checkin.actual_date = timezone.now()
        checkin.save()
        
        messages.success(request, 'Check-in marked as completed!')
        return redirect('monitoring:checkin_detail', pk=checkin_id)
    
    return redirect('monitoring:checkin_list')

@login_required
def quick_checkin(request):
    """Quick check-in creation."""
    if request.method == 'POST':
        offender_id = request.POST.get('offender')
        case_id = request.POST.get('case')
        purpose = request.POST.get('purpose')
        
        if offender_id and case_id and purpose:
            offender = get_object_or_404(Offender, pk=offender_id)
            case = get_object_or_404(Case, pk=case_id)
            
            # Create check-in for tomorrow at 10 AM
            tomorrow = timezone.now() + timedelta(days=1)
            scheduled_date = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
            
            checkin = CheckIn.objects.create(
                offender=offender,
                case=case,
                probation_officer=request.user,
                purpose=purpose,
                scheduled_date=scheduled_date,
                created_by=request.user
            )
            
            messages.success(request, 'Quick check-in scheduled successfully!')
            return redirect('monitoring:checkin_detail', pk=checkin.pk)
    
    # Get active cases for current user if they're an officer
    if request.user.is_officer:
        cases = Case.objects.filter(
            probation_officer=request.user,
            status='active'
        ).select_related('offender')
    else:
        cases = Case.objects.filter(status='active').select_related('offender')
    
    context = {
        'title': 'Quick Check-in',
        'cases': cases,
    }
    
    return render(request, 'monitoring/quick_checkin.html', context)

@login_required
def monitoring_statistics(request):
    """Get monitoring statistics (AJAX)."""
    # Check-in statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    stats = {
        'today_checkins': CheckIn.objects.filter(scheduled_date__date=today).count(),
        'week_checkins': CheckIn.objects.filter(scheduled_date__date__gte=week_ago).count(),
        'month_checkins': CheckIn.objects.filter(scheduled_date__date__gte=month_ago).count(),
        'completion_rate': CheckIn.objects.filter(status='completed').count() / max(CheckIn.objects.count(), 1) * 100,
        'active_gps': GPSMonitoring.objects.filter(device_status='active').count(),
        'new_alerts': Alert.objects.filter(status='new').count(),
        'positive_tests': DrugTest.objects.filter(result='positive').count(),
    }
    
    return JsonResponse(stats)

@login_required
def create_alert(request):
    """Create a new alert."""
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            alert = form.save()
            
            messages.success(request, 'Alert created successfully!')
            return redirect('monitoring:alert_detail', pk=alert.pk)
    
    else:
        form = AlertForm()
    
    context = {
        'title': 'Create Alert',
        'form': form,
    }
    
    return render(request, 'monitoring/alert_form.html', context)

@login_required
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert."""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    if request.method == 'POST':
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_time = timezone.now()
        alert.save()
        
        messages.success(request, 'Alert acknowledged!')
    
    return redirect('monitoring:alert_list')

@login_required
def resolve_alert(request, alert_id):
    """Resolve an alert."""
    alert = get_object_or_404(Alert, pk=alert_id)
    
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes', '')
        action_taken = request.POST.get('action_taken', '')
        
        alert.status = 'resolved'
        alert.resolution_notes = resolution_notes
        alert.action_taken = action_taken
        alert.resolved_by = request.user
        alert.resolved_time = timezone.now()
        alert.save()
        
        messages.success(request, 'Alert resolved!')
    
    return redirect('monitoring:alert_detail', pk=alert_id)