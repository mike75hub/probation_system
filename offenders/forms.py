"""
Forms for offender management.
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import Offender, Case, Assessment

User = get_user_model()

class OffenderForm(forms.ModelForm):
    """Form for creating/editing offenders."""
    
    # Additional user fields
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)
    
    class Meta:
        model = Offender
        fields = [
            'first_name', 'last_name', 'username', 'email', 'phone',
            'offender_id', 'date_of_birth', 'gender', 'nationality', 'id_number',
            'address', 'county', 'sub_county', 'phone_alternative', 'email',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship', 'risk_level', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'risk_level': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing an existing offender
        if self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['phone'].initial = self.instance.user.phone
            
            # Make username read-only when editing
            self.fields['username'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        offender = super().save(commit=False)
        
        # Get or create user
        if self.instance.pk:
            user = offender.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.phone = self.cleaned_data['phone']
        else:
            # Create new user
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                password='offender123',  # Default password
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                phone=self.cleaned_data['phone'],
                role=User.Role.OFFENDER
            )
            offender.user = user
        
        if commit:
            user.save()
            offender.save()
        
        return offender

class CaseForm(forms.ModelForm):
    """Form for creating/editing cases."""
    
    class Meta:
        model = Case
        fields = [
            'offender', 'case_number', 'court_name', 'court_location',
            'offense', 'offense_category', 'offense_date',
            'sentence_start', 'sentence_end', 'sentence_duration', 'sentence_type',
            'probation_officer', 'status', 'special_conditions', 'notes'
        ]
        widgets = {
            'offense_date': forms.DateInput(attrs={'type': 'date'}),
            'sentence_start': forms.DateInput(attrs={'type': 'date'}),
            'sentence_end': forms.DateInput(attrs={'type': 'date'}),
            'special_conditions': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit offender choices to active offenders
        self.fields['offender'].queryset = Offender.objects.filter(is_active=True)
        # Limit officer choices to probation officers
        self.fields['probation_officer'].queryset = User.objects.filter(role=User.Role.OFFICER)
    
    def clean(self):
        cleaned_data = super().clean()
        sentence_start = cleaned_data.get('sentence_start')
        sentence_end = cleaned_data.get('sentence_end')
        
        if sentence_start and sentence_end:
            if sentence_end <= sentence_start:
                raise forms.ValidationError(
                    'Sentence end date must be after start date.'
                )
        
        return cleaned_data

class AssessmentForm(forms.ModelForm):
    """Form for creating/editing assessments."""
    
    class Meta:
        model = Assessment
        fields = [
            'offender', 'assessment_date', 'assessed_by',
            'criminal_history', 'education_level', 'employment_status', 'employment_duration',
            'substance_abuse', 'mental_health_issues', 'anger_issues',
            'family_support', 'peer_support', 'community_ties',
            'financial_stability', 'housing_stability',
            'recommended_interventions', 'notes'
        ]
        widgets = {
            'assessment_date': forms.DateInput(attrs={'type': 'date'}),
            'recommended_interventions': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit offender choices to active offenders
        self.fields['offender'].queryset = Offender.objects.filter(is_active=True)
        # Limit assessor choices to officers
        self.fields['assessed_by'].queryset = User.objects.filter(role=User.Role.OFFICER)
    
    def clean_criminal_history(self):
        history = self.cleaned_data['criminal_history']
        if history < 0 or history > 10:
            raise forms.ValidationError('Criminal history must be between 0 and 10.')
        return history

class OffenderSearchForm(forms.Form):
    """Form for searching offenders."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by ID, name, or ID number...',
            'class': 'form-control'
        })
    )
    
    risk_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Risk Levels')] + list(Offender.RiskLevel.choices),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + [
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    county = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Filter by county...',
            'class': 'form-control'
        })
    )