from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password", min_length=8)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already in use.")
        return email

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        pw2 = cleaned.get('password2')
        if pw and pw2 and pw != pw2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned

class VerifyCodeForm(forms.Form):
    code = forms.CharField(max_length=10)

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")
