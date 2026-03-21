"""
Forms for programs app.
"""
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Program, ProgramCategory, Enrollment, Session, Attendance

class ProgramCategoryForm(forms.ModelForm):
    class Meta:
        model = ProgramCategory
        fields = ['name', 'slug', 'description', 'icon', 'color', 'is_active', 'display_order']
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

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            'code', 'name', 'description', 'program_type', 'category',
            'frequency', 'objectives', 'curriculum', 'duration_weeks', 'hours_per_week',
            'max_participants', 'eligibility_criteria', 'target_risk_level',
            'referral_required', 'prerequisites', 'completion_criteria', 'expected_outcomes',
            'facilitator', 'co_facilitator', 'facilitator_notes',
            'delivery_method', 'location', 'schedule_description', 'start_date', 'end_date', 'enrollment_deadline',
            'cost_per_participant', 'resources_required', 'status', 'is_featured'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'E.g., VTC-001'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'objectives': forms.Textarea(attrs={'rows': 3}),
            'curriculum': forms.Textarea(attrs={'rows': 5}),
            'eligibility_criteria': forms.Textarea(attrs={'rows': 3}),
            'prerequisites': forms.Textarea(attrs={'rows': 3}),
            'completion_criteria': forms.Textarea(attrs={'rows': 3}),
            'expected_outcomes': forms.Textarea(attrs={'rows': 3}),
            'facilitator_notes': forms.Textarea(attrs={'rows': 3}),
            'schedule_description': forms.Textarea(attrs={'rows': 2}),
            'resources_required': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'enrollment_deadline': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = [
            'program', 'offender', 'referred_by', 'referral_notes',
            'status', 'actual_start_date', 'actual_end_date'
        ]
        widgets = {
            'referral_notes': forms.Textarea(attrs={'rows': 3}),
            'actual_start_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active programs
        self.fields['program'].queryset = Program.objects.filter(status='active')

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            'program', 'session_number', 'title', 'description',
            'learning_objectives', 'date', 'start_time', 'end_time',
            'location', 'facilitator', 'materials_required',
            'reference_materials', 'is_completed', 'completion_notes'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'learning_objectives': forms.Textarea(attrs={'rows': 2}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'materials_required': forms.Textarea(attrs={'rows': 2}),
            'reference_materials': forms.Textarea(attrs={'rows': 2}),
            'completion_notes': forms.Textarea(attrs={'rows': 3}),
        }

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['status', 'check_in_time', 'check_out_time', 'participation_score', 'notes']
        widgets = {
            'check_in_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'check_out_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class ProgramSearchForm(forms.Form):
    """Form for searching programs."""
    program_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Program.ProgramType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Program.ProgramStatus.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=ProgramCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search program name or description...',
            'class': 'form-control'
        })
    )
