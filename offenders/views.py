"""
Views for offender management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Offender, Case, Assessment
from .forms import OffenderForm, CaseForm, AssessmentForm, OffenderSearchForm
from accounts.models import User
from datetime import date, timedelta  # Add this import

@login_required
def offender_list(request):
    """List all offenders with search and filter."""
    
    offenders = Offender.objects.all().order_by('-date_created')
    search_form = OffenderSearchForm(request.GET or None)
    
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        risk_level = search_form.cleaned_data.get('risk_level')
        status = search_form.cleaned_data.get('status')
        county = search_form.cleaned_data.get('county')
        
        # Apply filters
        if search:
            offenders = offenders.filter(
                Q(offender_id__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(id_number__icontains=search) |
                Q(user__username__icontains=search)
            )
        
        if risk_level:
            offenders = offenders.filter(risk_level=risk_level)
        
        if status == 'active':
            offenders = offenders.filter(is_active=True)
        elif status == 'inactive':
            offenders = offenders.filter(is_active=False)
        
        if county:
            offenders = offenders.filter(county__icontains=county)
    
    # Pagination
    paginator = Paginator(offenders, 10)  # Show 10 offenders per page
    page = request.GET.get('page')
    
    try:
        offenders_page = paginator.page(page)
    except PageNotAnInteger:
        offenders_page = paginator.page(1)
    except EmptyPage:
        offenders_page = paginator.page(paginator.num_pages)
    
    # Get counts for dashboard
    total_offenders = Offender.objects.count()
    active_offenders = Offender.objects.filter(is_active=True).count()
    high_risk_offenders = Offender.objects.filter(risk_level='high').count()
    
    context = {
        'offenders': offenders_page,
        'search_form': search_form,
        'total_offenders': total_offenders,
        'active_offenders': active_offenders,
        'high_risk_offenders': high_risk_offenders,
    }
    
    return render(request, 'offenders/list.html', context)

@login_required
def offender_detail(request, pk):
    """View offender details."""
    
    offender = get_object_or_404(Offender, pk=pk)
    cases = offender.cases.all().order_by('-date_created')
    assessments = offender.assessments.all().order_by('-assessment_date')
    
    # Get latest assessment
    latest_assessment = assessments.first() if assessments.exists() else None
    
    context = {
        'offender': offender,
        'cases': cases,
        'assessments': assessments,
        'latest_assessment': latest_assessment,
    }
    
    return render(request, 'offenders/detail.html', context)

@login_required
def offender_create(request):
    """Create a new offender."""
    
    if not request.user.is_admin() and not request.user.is_officer():
        messages.error(request, 'You do not have permission to create offenders.')
        return redirect('offender_list')
    
    if request.method == 'POST':
        form = OffenderForm(request.POST)
        if form.is_valid():
            offender = form.save()
            messages.success(request, f'Offender {offender.offender_id} created successfully!')
            return redirect('offender_detail', pk=offender.pk)
    else:
        form = OffenderForm()
    
    context = {
        'form': form,
        'title': 'Add New Offender'
    }
    
    return render(request, 'offenders/form.html', context)

@login_required
def offender_update(request, pk):
    """Update an existing offender."""
    
    if not request.user.is_admin() and not request.user.is_officer():
        messages.error(request, 'You do not have permission to update offenders.')
        return redirect('offender_list')
    
    offender = get_object_or_404(Offender, pk=pk)
    
    if request.method == 'POST':
        form = OffenderForm(request.POST, instance=offender)
        if form.is_valid():
            offender = form.save()
            messages.success(request, f'Offender {offender.offender_id} updated successfully!')
            return redirect('offender_detail', pk=offender.pk)
    else:
        form = OffenderForm(instance=offender)
    
    context = {
        'form': form,
        'offender': offender,
        'title': f'Edit Offender: {offender.offender_id}'
    }
    
    return render(request, 'offenders/form.html', context)

@login_required
def offender_delete(request, pk):
    """Delete an offender (soft delete)."""
    
    if not request.user.is_admin():
        messages.error(request, 'Only administrators can delete offenders.')
        return redirect('offender_list')
    
    offender = get_object_or_404(Offender, pk=pk)
    
    if request.method == 'POST':
        offender.is_active = False
        offender.save()
        messages.success(request, f'Offender {offender.offender_id} deactivated.')
        return redirect('offender_list')
    
    context = {
        'offender': offender
    }
    
    return render(request, 'offenders/delete.html', context)

@login_required
def case_create(request, offender_pk):
    """Create a case for an offender."""
    
    if not request.user.is_admin() and not request.user.is_officer():
        messages.error(request, 'You do not have permission to create cases.')
        return redirect('offender_detail', pk=offender_pk)
    
    offender = get_object_or_404(Offender, pk=offender_pk)
    
    if request.method == 'POST':
        form = CaseForm(request.POST)
        if form.is_valid():
            case = form.save(commit=False)
            case.offender = offender
            case.save()
            messages.success(request, f'Case {case.case_number} created successfully!')
            return redirect('offender_detail', pk=offender.pk)
    else:
        form = CaseForm(initial={'offender': offender})
    
    context = {
        'form': form,
        'offender': offender,
        'title': f'Add Case for {offender.offender_id}'
    }
    
    return render(request, 'offenders/case_form.html', context)

@login_required
def assessment_create(request, offender_pk):
    """Create an assessment for an offender."""
    
    if not request.user.is_admin() and not request.user.is_officer():
        messages.error(request, 'You do not have permission to create assessments.')
        return redirect('offender_detail', pk=offender_pk)
    
    offender = get_object_or_404(Offender, pk=offender_pk)
    
    if request.method == 'POST':
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.offender = offender
            if not assessment.assessed_by:
                assessment.assessed_by = request.user
            assessment.save()
            
            # Update offender's risk level based on assessment
            score = assessment.overall_risk_score or 0
            if score < 30:
                offender.risk_level = Offender.RiskLevel.LOW
            elif score < 70:
                offender.risk_level = Offender.RiskLevel.MEDIUM
            else:
                offender.risk_level = Offender.RiskLevel.HIGH
            offender.save()
            
            messages.success(request, f'Assessment created successfully! Risk score: {score:.1f}')
            return redirect('offender_detail', pk=offender.pk)
    else:
        form = AssessmentForm(initial={
            'offender': offender,
            'assessed_by': request.user
        })
    
    context = {
        'form': form,
        'offender': offender,
        'title': f'Create Assessment for {offender.offender_id}'
    }
    
    return render(request, 'offenders/assessment_form.html', context)

@login_required
def dashboard_stats(request):
    """Get dashboard statistics for offenders."""
    
    from django.db.models import Count, Q
    
    if request.user.is_offender():
        return redirect('offender_detail', pk=request.user.offender_profile.pk)
    
    # Basic stats
    total_offenders = Offender.objects.count()
    active_offenders = Offender.objects.filter(is_active=True).count()
    
    # Risk level breakdown
    risk_stats = Offender.objects.values('risk_level').annotate(
        count=Count('risk_level')
    ).order_by('risk_level')
    
    # Offense category breakdown
    offense_stats = Case.objects.values('offense_category').annotate(
        count=Count('offense_category')
    ).order_by('-count')
    
    # Recent assessments
    recent_assessments = Assessment.objects.select_related(
        'offender', 'assessed_by'
    ).order_by('-assessment_date')[:5]
    
    # Upcoming sentence completions (next 30 days)
    from datetime import date, timedelta
    upcoming_completions = Case.objects.filter(
        status='active',
        sentence_end__range=[date.today(), date.today() + timedelta(days=30)]
    ).select_related('offender').order_by('sentence_end')[:10]
    
    context = {
        'total_offenders': total_offenders,
        'active_offenders': active_offenders,
        'risk_stats': risk_stats,
        'offense_stats': offense_stats,
        'recent_assessments': recent_assessments,
        'upcoming_completions': upcoming_completions,
    }
    
    return render(request, 'offenders/dashboard_stats.html', context)
@login_required
def assessment_list(request):
    """List all assessments with search and filter."""
    
    assessments = Assessment.objects.all().select_related(
        'offender', 'assessed_by'
    ).order_by('-assessment_date')
    
    # Apply filters if provided
    offender_id = request.GET.get('offender_id')
    assessed_by = request.GET.get('assessed_by')
    risk_level = request.GET.get('risk_level')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if offender_id:
        assessments = assessments.filter(offender__offender_id__icontains=offender_id)
    
    if assessed_by:
        assessments = assessments.filter(
            Q(assessed_by__first_name__icontains=assessed_by) |
            Q(assessed_by__last_name__icontains=assessed_by) |
            Q(assessed_by__username__icontains=assessed_by)
        )
    
    if risk_level:
        if risk_level == 'low':
            assessments = assessments.filter(overall_risk_score__lt=30)
        elif risk_level == 'medium':
            assessments = assessments.filter(
                overall_risk_score__gte=30,
                overall_risk_score__lt=70
            )
        elif risk_level == 'high':
            assessments = assessments.filter(overall_risk_score__gte=70)
    
    if date_from:
        assessments = assessments.filter(assessment_date__gte=date_from)
    
    if date_to:
        assessments = assessments.filter(assessment_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(assessments, 20)  # Show 20 assessments per page
    page = request.GET.get('page')
    
    try:
        assessments_page = paginator.page(page)
    except PageNotAnInteger:
        assessments_page = paginator.page(1)
    except EmptyPage:
        assessments_page = paginator.page(paginator.num_pages)
    
    # Get statistics
    total_assessments = Assessment.objects.count()
    high_risk_count = Assessment.objects.filter(overall_risk_score__gte=70).count()
    recent_assessments = Assessment.objects.filter(
        assessment_date__gte=date.today() - timedelta(days=7)
    ).count()
    
    context = {
        'assessments': assessments_page,
        'total_assessments': total_assessments,
        'high_risk_count': high_risk_count,
        'recent_assessments': recent_assessments,
        'filter_values': {
            'offender_id': offender_id or '',
            'assessed_by': assessed_by or '',
            'risk_level': risk_level or '',
            'date_from': date_from or '',
            'date_to': date_to or '',
        }
    }
    
    return render(request, 'offenders/assessment_list.html', context)
