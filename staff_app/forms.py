# staff_app/forms.py
from django import forms
from django.contrib.auth.models import User
import re

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
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

class VerifyCodeForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput())
    code = forms.CharField(max_length=6, required=True)

class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(required=True)
