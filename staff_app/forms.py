from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re

# Password validation
def validate_password_strength(value):
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', value):
        raise ValidationError("Password must include at least one uppercase letter.")
    if not re.search(r'[a-z]', value):
        raise ValidationError("Password must include at least one lowercase letter.")
    if not re.search(r'[0-9]', value):
        raise ValidationError("Password must include at least one number.")


class StaffRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, validators=[validate_password_strength])
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise ValidationError("Passwords do not match.")
        return cleaned


class VerificationForm(forms.Form):
    code = forms.CharField(max_length=6, label="Enter Verification Code")


class StaffLoginForm(forms.Form):
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="Registered Email")
