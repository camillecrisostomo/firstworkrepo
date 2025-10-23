from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseRedirect
from .forms import RegistrationForm, VerifyCodeForm, ForgotPasswordForm, LoginForm
from .models import EmailVerification
from django.contrib.auth.models import User
import random
import string
from django.core.mail import send_mail
from django.urls import reverse

# helper
def generate_code(n=6):
    return ''.join(random.choices(string.digits, k=n))

def send_verification_email(user, code):
    subject = "Your verification code"
    message = f"Hello {user.username},\n\nYour verification code is: {code}\nIt expires in 10 minutes.\n\nIf you didn't request this, ignore."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            # create inactive user
            user = User.objects.create_user(username=username, email=email, password=password, is_active=False)
            # create code
            code = generate_code()
            verif = EmailVerification.objects.create(user=user, code=code)
            # send email
            send_verification_email(user, code)
            messages.success(request, "Account created. A verification code has been sent to your email.")
            # render register with show_modal True and the user id
            context = {'form': RegistrationForm(), 'show_modal': True, 'user_id': user.id}
            return render(request, 'user/register.html', context)
    else:
        form = RegistrationForm()
    return render(request, 'user/register.html', {'form': form})

def verify_code_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].strip()
            # get latest verification
            verifs = user.verifications.order_by('-created_at')
            if not verifs.exists():
                messages.error(request, "No verification code found. Please request resend.")
                return redirect('user:register')
            verif = verifs[0]
            if verif.is_expired():
                messages.error(request, "Code expired. Please resend.")
                return redirect('user:register')
            if verif.code != code:
                messages.error(request, "Invalid code. Try again.")
                # re-open modal
                context = {'form': RegistrationForm(), 'show_modal': True, 'user_id': user.id}
                return render(request, 'user/register.html', context)
            # success
            user.is_active = True
            user.save()
            messages.success(request, "Email verified. You can now log in.")
            return redirect('user:login')
    return redirect('user:register')

def resend_code_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    # limit resend to 3 times
    verif = user.verifications.order_by('-created_at').first()
    if verif and verif.resend_count >= 3:
        messages.error(request, "Resend limit reached. Try again later.")
        return redirect('user:register')
    # create new code
    code = generate_code()
    new_verif = EmailVerification.objects.create(user=user, code=code)
    # increment previous count if present
    if verif:
        new_verif.resend_count = verif.resend_count + 1
        new_verif.save()
    send_verification_email(user, code)
    messages.success(request, "New code sent to your email.")
    # render register with modal again
    context = {'form': RegistrationForm(), 'show_modal': True, 'user_id': user.id}
    return render(request, 'user/register.html', context)

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username_input = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # allow login by email too
            user = None
            if '@' in username_input:
                try:
                    user_obj = User.objects.get(email=username_input.lower())
                    username = user_obj.username
                    user = authenticate(request, username=username, password=password)
                except User.DoesNotExist:
                    user = None
            else:
                user = authenticate(request, username=username_input, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, "Account not verified. Please verify your email first.")
                    return redirect('user:login')
                login(request, user)
                return redirect('user:dashboard')
            else:
                messages.error(request, "Invalid credentials.")
    else:
        form = LoginForm()
    return render(request, 'user/login.html', {'form': form})

@login_required
def dashboard_view(request):
    return render(request, 'user/dashboard.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('user:login')

def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No account with that email.")
                return redirect('user:login')
            # create temp password
            temp_pw = ''.join(random.choices(string.ascii_letters + string.digits + '!@#$', k=10))
            user.set_password(temp_pw)
            user.save()
            # send email
            subject = "Your temporary password"
            message = f"Hello {user.username},\n\nYour temporary password is: {temp_pw}\nPlease login and change it immediately."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            messages.success(request, "A temporary password has been sent to your email.")
            return redirect('user:login')
    return redirect('user:login')
