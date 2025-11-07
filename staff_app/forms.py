# staff_app/forms.py
from django import forms
from django.contrib.auth.models import User
import re
from .models import StaffProfile, JobPost, REASON_CHOICES

class StaffRegisterForm(forms.Form):
    first_name = forms.CharField(max_length=30, required=True)
    middle_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already in use.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        # Password strength: at least 8 chars, 1 uppercase, 1 lowercase, 1 digit
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'\d', password):
            raise forms.ValidationError("Password must contain at least one digit.")
        return password

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned

class VerifyCodeForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput())
    code = forms.CharField(max_length=6, required=True)

class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(required=True)

# ADDED: UserModelForm to edit User fields (first_name, last_name, email)
class StaffUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': False}),
        }
        # You can add custom clean_email to prevent duplicates if you want

# ADDED: Form for changing password in profile
class ChangePasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        # If password is provided, validate it
        if password:
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters.")
            if not re.search(r'[A-Z]', password):
                raise forms.ValidationError("Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password):
                raise forms.ValidationError("Password must contain at least one lowercase letter.")
            if not re.search(r'\d', password):
                raise forms.ValidationError("Password must contain at least one digit.")
        return password
    
    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        # Only validate if at least one password field is filled
        if pw or cpw:
            if not pw or not cpw:
                raise forms.ValidationError("Both password fields must be filled.")
            if pw != cpw:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned

# ADDED: ModelForm for StaffProfile (middle_name, profile_image)
class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = StaffProfile
        fields = ['middle_name', 'profile_image']
        widgets = {
            'middle_name': forms.TextInput(),
        }

class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
            'title', 'position_title', 'job_type', 'experience',
            'job_description', 'qualification', 'location',
            'additional_info', 'about_company'
        ]
        widgets = {
            'job_description': forms.Textarea(attrs={'rows':4}),
            'qualification': forms.Textarea(attrs={'rows':3}),
            'additional_info': forms.Textarea(attrs={'rows':2}),
            'about_company': forms.Textarea(attrs={'rows':3}),
        }


class ArchiveForm(forms.Form):
    reason = forms.ChoiceField(choices=REASON_CHOICES)
    other_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':2}))

    def clean(self):
        cleaned = super().clean()
        r = cleaned.get('reason')
        other = cleaned.get('other_reason')
        if r == 'other' and not other:
            raise forms.ValidationError('Please specify the reason for "Other".')
        return cleaned

#ADDED FOR JOB POSTING
class DeleteForm(forms.Form):
    reason = forms.ChoiceField(choices=REASON_CHOICES)
    other_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows':2}))

    def clean(self):
        cleaned = super().clean()
        r = cleaned.get('reason')
        other = cleaned.get('other_reason')
        if r == 'other' and not other:
            raise forms.ValidationError('Please specify the reason for "Other".')
        return cleaned