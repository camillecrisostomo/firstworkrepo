import random
import string
from datetime import timedelta
from django.urls import reverse

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import StaffProfile
from .forms import StaffRegisterForm, VerifyCodeForm, LoginForm, ForgotPasswordForm

# =======================
# Configuration constants
# =======================
VERIFICATION_CODE_LENGTH = 6
RESEND_LIMIT = 5
RESEND_COOLDOWN_SECONDS = 60  # seconds cooldown between sends


# =======================
# Utility functions
# =======================
def _generate_code(length=VERIFICATION_CODE_LENGTH):
    return ''.join(random.choices(string.digits, k=length))


def _make_username(first, last):
    base = f"{first.strip()}_{last.strip()}".lower().replace(' ', '')
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{i}"
        i += 1
    return username


def _send_verification_email(user_email, full_name, code):
    subject = "Staff Verification Code"
    message = (
        f"Hi {full_name},\n\n"
        f"Your verification code is: {code}\n\n"
        f"Enter this code on the verification page to complete registration.\n\n"
        f"If you didn't request this, ignore this email."
    )
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [user_email], fail_silently=False)


# =======================
# Registration + Verification
# =======================
def register_staff(request):
    if request.method == 'POST':
        form = StaffRegisterForm(request.POST)
        if form.is_valid():
            first = form.cleaned_data['first_name'].strip()
            last = form.cleaned_data['last_name'].strip()
            middle = form.cleaned_data.get('middle_name', '').strip()
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']

            username = _make_username(first, last)

            user = User.objects.create_user(
                username=username,
                first_name=first,
                last_name=last,
                email=email,
                password=password,
                is_active=True,
            )

            # create staff profile
            code = _generate_code()
            now = timezone.now()
            StaffProfile.objects.create(
                user=user,
                middle_name=middle,
                verification_code=code,
                is_verified=False,
                resend_count=0,
                code_sent_at=now,
                status=StaffProfile.STATUS_PENDING_VERIFICATION,
            )

            # send email
            try:
                _send_verification_email(email, f"{first} {last}", code)
            except Exception as e:
                messages.error(request, f"Failed to send verification email: {e}")

            messages.success(request, "Registered successfully. A verification code was sent to your email.")
            return redirect(f"{reverse('staff_url:verify')}?email={email}")
    else:
        form = StaffRegisterForm()

    return render(request, 'staff_design/register.html', {'form': form})


def verify_code(request):
    email = request.GET.get('email') or request.POST.get('email')
    if not email:
        messages.error(request, "Missing email to verify.")
        return redirect('staff_url:register')

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "No registration found for that email.")
        return redirect('staff_url:register')

    profile = getattr(user, 'staff_profile', None)
    if not profile:
        messages.error(request, "Staff profile not found. Please register first.")
        return redirect('staff_url:register')

    if request.method == 'POST':
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].strip()
            if profile.verification_code == code:
                profile.is_verified = True
                profile.status = StaffProfile.STATUS_PENDING_APPROVAL
                profile.verification_code = ''
                profile.save()
                messages.success(request, "Email verified. Your account is now pending admin approval.")
                return redirect('staff_url:login')
            else:
                messages.error(request, "Invalid verification code.")
    else:
        form = VerifyCodeForm(initial={'email': email})

    return render(request, 'staff_design/verify_email.html', {'form': form, 'email': email})


def resend_code(request):
    if request.method != 'POST':
        return redirect('staff_url:register')

    email = request.POST.get('email')
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "No account with that email.")
        return redirect('staff_url:register')

    profile = getattr(user, 'staff_profile', None)
    if not profile:
        messages.error(request, "Profile not found.")
        return redirect('staff_url:register')

    # resend limits
    if profile.resend_count >= RESEND_LIMIT:
        messages.error(request, "You have reached the maximum number of resend attempts.")
        return redirect(f"{reverse('staff_url:verify')}?email={email}")

    now = timezone.now()
    if profile.code_sent_at and (now - profile.code_sent_at) < timedelta(seconds=RESEND_COOLDOWN_SECONDS):
        wait = RESEND_COOLDOWN_SECONDS - int((now - profile.code_sent_at).total_seconds())
        messages.error(request, f"Please wait {wait} more seconds before resending.")
        return redirect(f"{reverse('staff_url:verify')}?email={email}")

    code = _generate_code()
    profile.verification_code = code
    profile.resend_count += 1
    profile.code_sent_at = now
    profile.save()

    try:
        _send_verification_email(user.email, user.get_full_name(), code)
        messages.success(request, "Verification code resent to your email.")
    except Exception as e:
        messages.error(request, f"Failed to resend email: {e}")

    return redirect(f"{reverse('staff_url:verify')}?email={email}")


# =======================
# Login / Logout / Dashboard
# =======================
def staff_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, "Invalid credentials.")
                return redirect('staff_url:login')

            profile = getattr(user, 'staff_profile', None)
            if not profile:
                messages.error(request, "This email is not registered as staff.")
                return redirect('staff_url:login')

            if not profile.is_verified:
                messages.error(request, "Your email is not verified yet. Please verify via the code sent to your email.")
                return redirect(f"{reverse('staff_url:verify')}?email={email}")

            if profile.status != StaffProfile.STATUS_APPROVED:
                if profile.status == StaffProfile.STATUS_PENDING_APPROVAL:
                    messages.error(request, "Your account is still pending admin approval.")
                elif profile.status == StaffProfile.STATUS_REJECTED:
                    messages.error(request, "Your account has been rejected. Contact administrator.")
                else:
                    messages.error(request, "You cannot log in at this time.")
                return redirect('staff_url:login')

            user_auth = authenticate(request, username=user.username, password=password)
            if user_auth is None:
                messages.error(request, "Invalid credentials.")
                return redirect('staff_url:login')

            login(request, user_auth)
            messages.success(request, "Logged in as staff.")
            return redirect('staff_url:dashboard')

    else:
        form = LoginForm()
    return render(request, 'staff_design/login.html', {'form': form})


@login_required
def staff_logout(request):
    logout(request)
    messages.success(request, "Logged out.")
    return redirect('staff_url:login')


@login_required
def staff_dashboard(request):
    profile = getattr(request.user, 'staff_profile', None)
    if not profile or profile.status != StaffProfile.STATUS_APPROVED:
        messages.error(request, "You are not allowed to access the staff dashboard.")
        return redirect('staff_url:login')
    return render(request, 'staff_design/dashboard.html', {'profile': profile})


# =======================
# Password Reset
# =======================
def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, "No account found with that email.")
                return redirect('staff_url:forgot_password')

            profile = getattr(user, 'staff_profile', None)
            if not profile:
                messages.error(request, "This email is not registered as staff.")
                return redirect('staff_url:forgot_password')

            temp_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user.set_password(temp_pw)
            user.save()

            subject = "Staff Password Reset"
            message = (
                f"Hi {user.get_full_name()},\n\n"
                f"A temporary password has been generated for your staff account:\n\n"
                f"Temporary password: {temp_pw}\n\n"
                f"Please log in and change your password immediately."
            )
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                messages.success(request, "A temporary password has been sent to your email.")
                return redirect('staff_url:reset_success')
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")
                return redirect('staff_url:forgot_password')
    else:
        form = ForgotPasswordForm()

    return render(request, 'staff_design/forgot_password.html', {'form': form})


def reset_success(request):
    return render(request, 'staff_design/reset_success.html')


# =======================
# Admin Approval Views
# =======================
def _is_superuser(user):
    return user.is_superuser


@user_passes_test(_is_superuser)
def staff_approvals(request):
    q = request.GET.get('q')
    if q:
        profiles = StaffProfile.objects.filter(status__iexact=q).order_by('-created_at')
    else:
        profiles = StaffProfile.objects.all().order_by('-created_at')
    return render(request, 'staff_design/approval_list.html', {'profiles': profiles, 'filter': q})


@user_passes_test(_is_superuser)
def staff_approval_action(request):
    if request.method != 'POST':
        return redirect('staff_url:approvals')

    profile_id = request.POST.get('profile_id')
    action = request.POST.get('action')
    note = request.POST.get('admin_note', '')

    profile = get_object_or_404(StaffProfile, id=profile_id)
    if action == 'approve':
        profile.status = StaffProfile.STATUS_APPROVED
        profile.admin_note = note
        profile.save()
        try:
            send_mail(
                "Staff Account Approved",
                f"Hi {profile.user.get_full_name()},\n\nYour staff account has been approved. You can now log in.",
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                fail_silently=True
            )
        except:
            pass
        messages.success(request, f"{profile.user.get_full_name()} approved.")
    elif action == 'reject':
        profile.status = StaffProfile.STATUS_REJECTED
        profile.admin_note = note
        profile.save()
        try:
            send_mail(
                "Staff Account Rejected",
                f"Hi {profile.user.get_full_name()},\n\nYour staff account has been rejected. Note: {note}",
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                fail_silently=True
            )
        except:
            pass
        messages.success(request, f"{profile.user.get_full_name()} rejected.")
    else:
        messages.error(request, "Unknown action.")

    return redirect('staff_url:approvals')