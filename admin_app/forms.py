# admin_app/forms.py
from django import forms

class AdminLoginForm(forms.Form):
    username = forms.CharField(max_length=150, label='Username')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')

class ApprovalActionForm(forms.Form):
    profile_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(choices=[('approve','Approve'),('reject','Reject')])
    admin_note = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), required=False)
