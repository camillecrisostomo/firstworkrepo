from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from .forms import RegistrationForm, VerifyCodeForm, ForgotPasswordForm, LoginForm
from .forms import UserUserForm, UserProfileForm, ChangePasswordForm
from .models import EmailVerification, UserProfile
from django.contrib.auth.models import User
import random
import string
from django.core.mail import send_mail
from django.urls import reverse

#ADDED FOR JOB POSTING
from staff_app.models import JobPost

#added for submission of CV
from staff_app.models import JobApplication
from .forms import JobApplicationForm
from datetime import date

# helper
def generate_code(n=6):
    return ''.join(random.choices(string.digits, k=n))

def _make_username(first, last):
    base = f"{first.strip()}_{last.strip()}".lower().replace(' ', '')
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{i}"
        i += 1
    return username

def send_verification_email(user, code):
    subject = "Your verification code"
    message = f"Hello {user.username},\n\nYour verification code is: {code}\nIt expires in 10 minutes.\n\nIf you didn't request this, ignore."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first = form.cleaned_data['first_name'].strip()
            middle = form.cleaned_data.get('middle_name', '').strip()
            last = form.cleaned_data['last_name'].strip()
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            
            # Generate username from first and last name
            username = _make_username(first, last)
            
            # create inactive user
            user = User.objects.create_user(
                username=username,
                first_name=first,
                last_name=last,
                email=email,
                password=password,
                is_active=False
            )
            
            # create user profile with middle name
            UserProfile.objects.create(
                user=user,
                middle_name=middle
            )
            
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
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email').lower()
            password = form.cleaned_data.get('password')
            
            # Find user by email
            try:
                user_obj = User.objects.get(email=email)
                username = user_obj.username
                user = authenticate(request, username=username, password=password)
            except User.DoesNotExist:
                user = None
            
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

# =======================
# Profile View
# =======================

@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    View to show and edit user profile (User + UserProfile).
    Save button is disabled by default in template; client-side JS enables it when any change occurs.
    """
    user = request.user

    # Ensure profile exists; if not, create one with default image
    profile, created = UserProfile.objects.get_or_create(user=user)
    # (created True means newly created -- default image will be used)

    if request.method == 'POST':
        user_form = UserUserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        password_form = ChangePasswordForm(request.POST)
        
        # Validate all forms
        user_valid = user_form.is_valid()
        profile_valid = profile_form.is_valid()
        password_valid = password_form.is_valid()
        
        if user_valid and profile_valid and password_valid:
            # Validate email uniqueness (if user changed email)
            new_email = user_form.cleaned_data.get('email').lower()
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                user_form.add_error('email', 'This email is already used by another account.')
            else:
                # Save user fields
                u = user_form.save(commit=False)
                u.email = new_email
                u.save()
                
                # Save profile (handles profile_image)
                profile_form.save()
                
                # Handle password change (if provided)
                new_password = password_form.cleaned_data.get('password')
                if new_password:
                    u.set_password(new_password)
                    u.save()
                    messages.success(request, "Profile and password updated successfully.")
                else:
                    messages.success(request, "Profile updated successfully.")
                
                # Redirect to avoid resubmission and to reflect new image url
                return redirect('user:profile')
        else:
            # Let template show form errors
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = UserUserForm(instance=user)
        profile_form = UserProfileForm(instance=profile)
        password_form = ChangePasswordForm()

    return render(request, 'user/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': profile,  # for template convenience
    })


#ADDED FOR JOB POSTING
def career_search(request):
    # show only non-archived posts
    query = request.GET.get('q', '')
    posts = JobPost.objects.filter(archived=False).order_by('-post_date')
    if query:
        posts = posts.filter(title__icontains=query)  # simple search; extend as needed

    # Only show brief fields in the list
    return render(request, 'user/career_search.html', {'posts': posts, 'query': query})


def job_detail(request, job_number):
    post = get_object_or_404(JobPost, job_number=job_number, archived=False)
    return render(request, 'user/job_detail.html', {'post': post})


#added for submission of CV
@login_required
def job_detail(request, job_number):
    job = get_object_or_404(JobPost, job_number=job_number, archived=False)
    # show existing application status if any
    existing = JobApplication.objects.filter(job=job, applicant=request.user).first()
    return render(request, 'user/job_detail.html', {'job': job, 'existing': existing})

@login_required
def apply_job(request, job_number):
    job = get_object_or_404(JobPost, job_number=job_number, archived=False)

    # optional: prevent duplicate application for the same job (moved above)
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.info(request, "You have already applied for this job.")
        return redirect('user:job_detail', job_number=job_number)

    # Check if user currently blocked by rejection from ANY job
    # (rejected applicants can't apply for 6 months)
    active_rejection = JobApplication.objects.filter(
        applicant=request.user,
        status=JobApplication.STATUS_REJECTED,
        rejection_until__gte=timezone.now().date()
    ).exists()

    if active_rejection:
        # find the soonest date they can apply again
        last_block = JobApplication.objects.filter(
            applicant=request.user,
            status=JobApplication.STATUS_REJECTED
        ).order_by('-rejection_until').first()
        can_apply_on = last_block.rejection_until if last_block else None
        messages.error(request, f"You cannot apply until {can_apply_on}. Please wait 6 months from rejection.")
        return redirect('user:job_detail', job_number=job_number)

    # Submit new application
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.job = job
            app.applicant = request.user
            app.save()
            messages.success(request, "Application submitted successfully.")
            # optional: notify staff via email
            return redirect('user:job_detail', job_number=job_number)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = JobApplicationForm()

    return render(request, 'user/apply_job.html', {'form': form, 'job': job})