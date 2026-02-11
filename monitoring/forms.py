"""
Forms for monitoring app.
"""
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import (
    CheckIn, CheckInType, GPSMonitoring, GPSLocation, 
    DrugTest, EmploymentVerification, Alert
)
from offenders.models import Case

class CheckInTypeForm(forms.ModelForm):
    class Meta:
        model = CheckInType
        fields = ['name', 'description', 'icon', 'color', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'icon': forms.TextInput(attrs={'placeholder': 'fas fa-icon-name'}),
            'color': forms.Select(choices=[
                ('primary', 'Primary (Blue)'),
                ('secondary', 'Secondary (Gray)'),
                ('success', 'Success (Green)'),
                ('danger', 'Danger (Red)'),
                ('warning', 'Warning (Yellow)'),
                ('info', 'Info (Cyan)'),
                ('light', 'Light'),
                ('dark', 'Dark')
            ])
        }

class CheckInForm(forms.ModelForm):
    class Meta:
        model = CheckIn
        fields = [
            'case', 'offender', 'probation_officer', 'checkin_type',
            'scheduled_date', 'location', 'purpose', 'status',
            'compliance_level', 'risk_assessment', 'behavior_notes',
            'progress_notes', 'concerns_issues', 'recommendations',
            'next_steps', 'next_checkin_date', 'officer_signature',
            'offender_signature', 'witness_name'
        ]
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'actual_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'next_checkin_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
            'risk_assessment': forms.Textarea(attrs={'rows': 3}),
            'behavior_notes': forms.Textarea(attrs={'rows': 3}),
            'progress_notes': forms.Textarea(attrs={'rows': 3}),
            'concerns_issues': forms.Textarea(attrs={'rows': 3}),
            'recommendations': forms.Textarea(attrs={'rows': 3}),
            'next_steps': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter cases to active ones only
        self.fields['case'].queryset = Case.objects.filter(status='active')
        
        # Set initial offender based on case if case is selected
        if 'case' in self.data:
            try:
                case_id = int(self.data.get('case'))
                case = Case.objects.get(pk=case_id)
                self.fields['offender'].initial = case.offender
            except (ValueError, TypeError, Case.DoesNotExist):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        actual_date = cleaned_data.get('actual_date')
        status = cleaned_data.get('status')
        
        # If status is completed, actual date is required
        if status == 'completed' and not actual_date:
            self.add_error('actual_date', 'Actual date is required for completed check-ins.')
        
        # If actual date is provided, it should be after scheduled date
        if scheduled_date and actual_date and actual_date < scheduled_date:
            self.add_error('actual_date', 'Actual date cannot be before scheduled date.')
        
        return cleaned_data

class GPSMonitoringForm(forms.ModelForm):
    class Meta:
        model = GPSMonitoring
        fields = [
            'offender', 'case', 'device_id', 'device_type', 'device_status',
            'issued_date', 'expected_return_date', 'monitoring_start_date',
            'monitoring_end_date', 'checkin_frequency_hours', 'restricted_zones',
            'curfew_start', 'curfew_end', 'battery_level', 'notes'
        ]
        widgets = {
            'issued_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_return_date': forms.DateInput(attrs={'type': 'date'}),
            'monitoring_start_date': forms.DateInput(attrs={'type': 'date'}),
            'monitoring_end_date': forms.DateInput(attrs={'type': 'date'}),
            'curfew_start': forms.TimeInput(attrs={'type': 'time'}),
            'curfew_end': forms.TimeInput(attrs={'type': 'time'}),
            'restricted_zones': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter JSON format of restricted areas'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        monitoring_start_date = cleaned_data.get('monitoring_start_date')
        monitoring_end_date = cleaned_data.get('monitoring_end_date')
        
        if monitoring_start_date and monitoring_end_date and monitoring_end_date < monitoring_start_date:
            self.add_error('monitoring_end_date', 'Monitoring end date must be after start date.')
        
        return cleaned_data

class GPSLocationForm(forms.ModelForm):
    class Meta:
        model = GPSLocation
        fields = [
            'gps_monitoring', 'latitude', 'longitude', 'accuracy',
            'altitude', 'speed', 'timestamp', 'is_in_restricted_zone',
            'is_curfew_violation', 'battery_level', 'address',
            'provider', 'notes'
        ]
        widgets = {
            'timestamp': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude and (latitude < -90 or latitude > 90):
            raise forms.ValidationError("Latitude must be between -90 and 90 degrees.")
        return latitude
    
    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude and (longitude < -180 or longitude > 180):
            raise forms.ValidationError("Longitude must be between -180 and 180 degrees.")
        return longitude

class DrugTestForm(forms.ModelForm):
    class Meta:
        model = DrugTest
        fields = [
            'offender', 'case', 'conducted_by', 'test_type',
            'test_date', 'location', 'result', 'substances_tested',
            'substances_detected', 'concentration_levels', 'observations',
            'offender_comments', 'follow_up_required', 'follow_up_date',
            'recommendations', 'witness_name', 'lab_reference'
        ]
        widgets = {
            'test_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'substances_tested': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., THC, Cocaine, Alcohol, Opiates'}),
            'substances_detected': forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g., THC: Positive, Alcohol: Negative'}),
            'concentration_levels': forms.Textarea(attrs={'rows': 3, 'placeholder': 'JSON format: {"THC": "50 ng/ml", "Alcohol": "0.02%"}'}),
            'observations': forms.Textarea(attrs={'rows': 3}),
            'offender_comments': forms.Textarea(attrs={'rows': 2}),
            'recommendations': forms.Textarea(attrs={'rows': 3}),
        }

class EmploymentVerificationForm(forms.ModelForm):
    class Meta:
        model = EmploymentVerification
        fields = [
            'offender', 'case', 'employer_name', 'employer_address',
            'employer_phone', 'employer_email', 'position', 'employment_type',
            'start_date', 'end_date', 'verification_status', 'verified_by',
            'verification_date', 'verification_method', 'hours_per_week',
            'salary', 'pay_frequency', 'supervisor_name', 'supervisor_phone',
            'notes'
        ]
        widgets = {
            'employer_address': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'verification_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date must be after start date.')
        
        return cleaned_data

class AlertForm(forms.ModelForm):
    class Meta:
        model = Alert
        fields = [
            'alert_type', 'priority', 'status', 'offender', 'case',
            'related_checkin', 'related_gps', 'title', 'description',
            'location', 'resolution_notes', 'action_taken'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'resolution_notes': forms.Textarea(attrs={'rows': 3}),
            'action_taken': forms.Textarea(attrs={'rows': 3}),
        }

class CheckInSearchForm(forms.Form):
    """Form for searching check-ins."""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(CheckIn.CheckInStatus.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    offender = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by offender name...',
            'class': 'form-control'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    officer = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields['officer'].queryset = User.objects.filter(role='officer')

class ComplianceReportForm(forms.Form):
    """Form for generating compliance reports."""
    REPORT_CHOICES = [
        ('monthly', 'Monthly Compliance Report'),
        ('quarterly', 'Quarterly Compliance Report'),
        ('yearly', 'Yearly Compliance Report'),
        ('custom', 'Custom Date Range'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_CHOICES,
        widget=forms.RadioSelect,
        initial='monthly'
    )
    year = forms.IntegerField(
        min_value=2000,
        max_value=2100,
        initial=2024,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    month = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 13)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quarter = forms.ChoiceField(
        choices=[(1, 'Q1 (Jan-Mar)'), (2, 'Q2 (Apr-Jun)'), (3, 'Q3 (Jul-Sep)'), (4, 'Q4 (Oct-Dec)')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    officer = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields['officer'].queryset = User.objects.filter(role='officer')