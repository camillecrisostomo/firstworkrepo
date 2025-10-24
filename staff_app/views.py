from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random, string

from .models import StaffProfile
from .forms import StaffRegisterForm, VerificationForm, StaffLoginForm, ForgotPasswordForm


# Helper: Generate 6-digit code
def generate_code():
    return ''.join(random.choices(string.digits, k=6))


# REGISTER STAFF
def register_staff(request):
    if request.method == 'POST':
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()

            code = generate_code()
            StaffProfile.objects.create(user=user, verification_code=code)

            send_mail(
                "Staff Verification Code",
                f"Your verification code is: {code}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )

            messages.success(request, "A verification code has been sent to your email.")
            return redirect('staff_url:verify_email', user_id=user.id)
    else:
        form = StaffRegisterForm()

    return render(request, 'staff_design/register.html', {'form': form})


# VERIFY EMAIL
def verify_email(request, user_id):
    user = get_object_or_404(User, id=user_id)
    staff = get_object_or_404(StaffProfile, user=user)

    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['code'] == staff.verification_code:
                staff.is_verified = True
                user.is_active = True
                staff.save()
                user.save()
                messages.success(request, "Email verified successfully! Awaiting admin approval.")
                return redirect('staff_url:login')
            else:
                messages.error(request, "Invalid verification code.")
    else:
        form = VerificationForm()

    return render(request, 'staff_design/verify_email.html', {'form': form, 'user': user})


# LOGIN
def staff_login(request):
    if request.method == 'POST':
        form = StaffLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user:
                staff = StaffProfile.objects.get(user=user)
                if not staff.is_verified:
                    messages.error(request, "Please verify your email first.")
                elif staff.status == 'Pending':
                    messages.error(request, "Your account is still pending admin approval.")
                elif staff.status == 'Rejected':
                    messages.error(request, "Your account has been rejected by the admin.")
                else:
                    login(request, user)
                    return redirect('staff_url:dashboard')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = StaffLoginForm()
    return render(request, 'staff_design/login.html', {'form': form})


# LOGOUT
def staff_logout(request):
    logout(request)
    return redirect('staff_url:login')


# DASHBOARD
def staff_dashboard(request):
    return render(request, 'staff_design/dashboard.html')


# FORGOT PASSWORD
def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                temp_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                user.set_password(temp_pass)
                user.save()
                send_mail(
                    "Temporary Password",
                    f"Your temporary password is: {temp_pass}\nPlease login and change your password immediately.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                messages.success(request, "Temporary password sent to your email.")
                return redirect('staff_url:reset_success')
            except User.DoesNotExist:
                messages.error(request, "Email not found.")
    else:
        form = ForgotPasswordForm()
    return render(request, 'staff_design/forgot_password.html', {'form': form})


def reset_success(request):
    return render(request, 'staf_design/reset_success.html')
