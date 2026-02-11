"""
Forms for reports app.
"""
from django import forms
from django.utils import timezone
from .models import (
    ReportType, ReportSchedule, GeneratedReport, 
    ReportTemplate, ReportDashboard, DashboardReport
)

class ReportTypeForm(forms.ModelForm):
    class Meta:
        model = ReportType
        fields = [
            'name', 'description', 'category',
            'is_daily', 'is_weekly', 'is_monthly', 
            'is_quarterly', 'is_yearly',
            'allowed_roles', 'template_path',
            'parameters_schema', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'parameters_schema': forms.Textarea(attrs={'rows': 4}),
            'allowed_roles': forms.CheckboxSelectMultiple(
                choices=[
                    ('admin', 'Administrator'),
                    ('officer', 'Probation Officer'),
                    ('judiciary', 'Judiciary Staff'),
                    ('ngo', 'NGO Staff'),
                ]
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template_path'].help_text = 'Path to HTML template file (optional)'

class ReportScheduleForm(forms.ModelForm):
    class Meta:
        model = ReportSchedule
        fields = [
            'name', 'report_type', 'frequency',
            'start_date', 'end_date', 'scheduled_time',
            'recipients', 'send_email', 'email_subject',
            'email_message', 'status', 'parameters'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'email_message': forms.Textarea(attrs={'rows': 4}),
            'parameters': forms.Textarea(attrs={'rows': 3}),
            'recipients': forms.SelectMultiple(attrs={'class': 'select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default start date to tomorrow
        if not self.instance.pk:
            self.initial['start_date'] = timezone.now().date()
        
        # Set default email subject
        if not self.instance.email_subject:
            self.initial['email_subject'] = 'Automated Report: {report_name} - {date}'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if end_date and start_date and end_date < start_date:
            self.add_error('end_date', 'End date must be after start date')
        
        return cleaned_data

class ReportGenerationForm(forms.Form):
    """Form for generating a report."""
    
    # Report selection
    report_type = forms.ModelChoiceField(
        queryset=ReportType.objects.filter(is_active=True),
        label="Select Report Type",
        help_text="Choose the type of report to generate"
    )
    
    # Date range
    PERIOD_CHOICES = [
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('last_week', 'Last Week'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_quarter', 'This Quarter'),
        ('this_year', 'This Year'),
        ('custom', 'Custom Range'),
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        initial='this_month',
        label="Time Period"
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="From Date"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="To Date"
    )
    
    # Output format
    FORMAT_CHOICES = [
        ('pdf', 'PDF Document'),
        ('excel', 'Excel Spreadsheet'),
        ('csv', 'CSV File'),
        ('html', 'HTML Report'),
    ]
    
    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='pdf',
        label="Output Format"
    )
    
    # Filters (dynamically loaded based on report type)
    officer = forms.CharField(
        required=False,
        label="Probation Officer",
        help_text="Filter by officer (leave blank for all)"
    )
    offender = forms.CharField(
        required=False,
        label="Offender",
        help_text="Filter by offender name or ID"
    )
    location = forms.CharField(
        required=False,
        label="Location",
        help_text="Filter by location/county"
    )
    
    # Options
    include_charts = forms.BooleanField(
        required=False,
        initial=True,
        label="Include Charts and Graphs"
    )
    include_details = forms.BooleanField(
        required=False,
        initial=True,
        label="Include Detailed Data"
    )
    send_email = forms.BooleanField(
        required=False,
        initial=False,
        label="Send via Email when Complete"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default dates
        today = timezone.now().date()
        self.initial['date_from'] = today.replace(day=1)  # First day of current month
        self.initial['date_to'] = today
    
    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if period == 'custom':
            if not date_from or not date_to:
                self.add_error(None, 'Please select both start and end dates for custom period')
            elif date_to < date_from:
                self.add_error('date_to', 'End date must be after start date')
        
        return cleaned_data

class ComplianceReportForm(forms.Form):
    """Form for generating compliance reports."""
    
    # Date range
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Start Date"
    )
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="End Date"
    )
    
    # Grouping
    GROUP_BY_CHOICES = [
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('officer', 'By Officer'),
        ('offender', 'By Offender'),
        ('location', 'By Location'),
    ]
    
    group_by = forms.ChoiceField(
        choices=GROUP_BY_CHOICES,
        initial='week',
        label="Group Results By"
    )
    
    # Filters
    officer = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Probation Officer",
        help_text="Filter by specific officer"
    )
    min_compliance = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={'placeholder': '0-100'}),
        label="Minimum Compliance %",
        help_text="Show only offenders/offices above this compliance rate"
    )
    
    # Metrics to include
    include_checkins = forms.BooleanField(
        initial=True,
        label="Include Check-in Statistics"
    )
    include_gps = forms.BooleanField(
        initial=True,
        label="Include GPS Monitoring"
    )
    include_drug_tests = forms.BooleanField(
        initial=True,
        label="Include Drug Test Results"
    )
    include_employment = forms.BooleanField(
        initial=False,
        label="Include Employment Verification"
    )
    
    def __init__(self, *args, **kwargs):
        from accounts.models import User
        super().__init__(*args, **kwargs)
        
        # Set default dates (last 30 days)
        today = timezone.now().date()
        thirty_days_ago = today - timezone.timedelta(days=30)
        
        self.initial['date_from'] = thirty_days_ago
        self.initial['date_to'] = today
        
        # Set officers queryset
        self.fields['officer'].queryset = User.objects.filter(role='officer')

class PerformanceReportForm(forms.Form):
    """Form for generating performance reports."""
    
    REPORT_TYPE_CHOICES = [
        ('officer_performance', 'Officer Performance'),
        ('program_effectiveness', 'Program Effectiveness'),
        ('recidivism_analysis', 'Recidivism Analysis'),
        ('risk_assessment', 'Risk Assessment Accuracy'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        label="Report Type"
    )
    
    # Time period
    YEAR_CHOICES = [(y, y) for y in range(2020, timezone.now().year + 1)]
    YEAR_CHOICES.reverse()
    
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        initial=str(timezone.now().year),
        label="Year"
    )
    
    quarter = forms.ChoiceField(
        choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')],
        required=False,
        label="Quarter (optional)"
    )
    
    month = forms.ChoiceField(
        choices=[(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        required=False,
        label="Month (optional)"
    )
    
    # Comparison options
    compare_with_previous = forms.BooleanField(
        initial=True,
        label="Compare with Previous Period"
    )
    show_trends = forms.BooleanField(
        initial=True,
        label="Show Trends Over Time"
    )
    
    # Metrics
    include_kpis = forms.BooleanField(
        initial=True,
        label="Include Key Performance Indicators"
    )
    include_benchmarks = forms.BooleanField(
        initial=True,
        label="Include Benchmark Comparisons"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        quarter = cleaned_data.get('quarter')
        month = cleaned_data.get('month')
        
        if quarter and month:
            self.add_error(None, 'Please select either quarter or month, not both')
        
        return cleaned_data

class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ['name', 'description', 'template_file', 'report_types', 'version', 'is_default']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'report_types': forms.SelectMultiple(attrs={'class': 'select2'}),
        }

class DashboardForm(forms.ModelForm):
    class Meta:
        model = ReportDashboard
        fields = ['name', 'description', 'layout_config', 'is_public', 'allowed_users', 'refresh_interval']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'layout_config': forms.Textarea(attrs={'rows': 4}),
            'allowed_users': forms.SelectMultiple(attrs={'class': 'select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default layout config
        if not self.instance.layout_config:
            self.initial['layout_config'] = '{"columns": 12, "rowHeight": 100}'

class DashboardReportForm(forms.ModelForm):
    class Meta:
        model = DashboardReport
        fields = ['report_type', 'position_x', 'position_y', 'width', 'height', 
                 'title', 'show_title', 'refresh_interval', 'parameters']
        widgets = {
            'parameters': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        width = cleaned_data.get('width')
        height = cleaned_data.get('height')
        
        if width and (width < 1 or width > 12):
            self.add_error('width', 'Width must be between 1 and 12 columns')
        
        if height and height < 1:
            self.add_error('height', 'Height must be at least 1 row')
        
        return cleaned_data