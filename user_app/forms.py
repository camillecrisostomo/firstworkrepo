from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
import re
from .models import UserProfile
from staff_app.models import JobApplication
from django.core.exceptions import ValidationError


class RegistrationForm(forms.Form):
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
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

class VerifyCodeForm(forms.Form):
    code = forms.CharField(max_length=10)

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

class LoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

# ADDED: UserModelForm to edit User fields (first_name, last_name, email)
class UserUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': False}),
        }

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

# ADDED: ModelForm for UserProfile (middle_name, profile_image)
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['middle_name', 'profile_image']
        widgets = {
            'middle_name': forms.TextInput(),
        }


#added for submission of CV
ALLOWED_MIME = ['application/pdf', 'image/png', 'image/jpeg']
ALLOWED_EXT = ['.pdf', '.png', '.jpg', '.jpeg']
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['cv']

    def clean_cv(self):
        f = self.cleaned_data.get('cv')
        if not f:
            raise ValidationError("CV is required.")
        # size
        if f.size > MAX_SIZE:
            raise ValidationError("File too large. Max 5 MB.")
        # content_type check (safe but not 100% foolproof)
        content_type = f.content_type
        if content_type not in ALLOWED_MIME:
            raise ValidationError("Invalid file type. Allowed: pdf, png, jpeg.")
        # extension check
        import os
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_EXT:
            raise ValidationError("Invalid file extension. Allowed: pdf, png, jpeg.")
        return f