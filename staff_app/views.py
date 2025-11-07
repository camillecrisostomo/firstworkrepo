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
from django.views.decorators.http import require_http_methods


from .models import StaffProfile
from .forms import StaffRegisterForm, VerifyCodeForm, LoginForm, ForgotPasswordForm
from .forms import StaffUserForm, StaffProfileForm, ChangePasswordForm

#ADDED FOR JOB POSTING
from .forms import JobPostForm, ArchiveForm, DeleteForm
from .models import JobPost, ArchivedJob, DeletionLog

#added for submission of CV
from .models import JobApplication
from django.db.models import Q
from django.http import HttpResponseForbidden

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
        wait = max(wait, 1)
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


@login_required
@user_passes_test(_is_superuser)
def staff_approvals(request):
    q = request.GET.get('q')
    if q:
        profiles = StaffProfile.objects.filter(status__iexact=q).order_by('-created_at')
    else:
        profiles = StaffProfile.objects.all().order_by('-created_at')
    return render(request, 'staff_design/approval_list.html', {'profiles': profiles, 'filter': q})


@login_required
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

# =======================
# Profile Views
# =======================

@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    View to show and edit staff profile (User + StaffProfile).
    Includes change password functionality.
    """
    user = request.user
    profile, created = StaffProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = StaffUserForm(request.POST, instance=user)
        profile_form = StaffProfileForm(request.POST, request.FILES, instance=profile)
        password_form = ChangePasswordForm(request.POST)  # ✅ added

        # Validate all three
        if user_form.is_valid() and profile_form.is_valid() and password_form.is_valid():
            # Check for email duplication
            new_email = user_form.cleaned_data.get('email').lower()
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                user_form.add_error('email', 'This email is already used by another account.')
            else:
                # Save user info
                u = user_form.save(commit=False)
                u.email = new_email
                u.save()

                # Save profile info
                profile_form.save()

                # ✅ Handle password change (only if provided)
                new_password = password_form.cleaned_data.get('password')
                if new_password:
                    u.set_password(new_password)
                    u.save()
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, u)  # stay logged in
                    messages.success(request, "Password updated successfully.")

                messages.success(request, "Profile updated successfully.")
                return redirect('staff_url:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = StaffUserForm(instance=user)
        profile_form = StaffProfileForm(instance=profile)
        password_form = ChangePasswordForm()  # ✅ added

    return render(request, 'staff_design/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,  # ✅ added
        'profile': profile,
    })

#ADDED FOR JOB POSTING
# NOTE: Adjust permission check depending on your StaffProfile/admin approval system.
def staff_permission_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('user:login')  # adjust namespace if different
        # If you have StaffProfile with status field, use it here:
        # if not hasattr(request.user, 'staffprofile') or request.user.staffprofile.status != 'approved':
        #     messages.error(request, 'You are not allowed to access this page.')
        #     return redirect('staff_url:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@login_required
@staff_permission_required
def post_list(request):
    posts = JobPost.objects.filter(staff=request.user, archived=False).order_by('-post_date')
    return render(request, 'job/post_list.html', {'posts': posts})


@login_required
@staff_permission_required
def post_create(request):
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.staff = request.user
            post.save()
            messages.success(request, 'Job post created.')
            return redirect('staff_url:post_list')
    else:
        form = JobPostForm()
    return render(request, 'job/post_form.html', {'form': form, 'create': True})


@login_required
@staff_permission_required
def post_edit(request, pk):
    post = get_object_or_404(JobPost, pk=pk, staff=request.user)
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job post updated.')
            return redirect('staff_url:post_list')
    else:
        form = JobPostForm(instance=post)
    return render(request, 'job/post_form.html', {'form': form, 'create': False, 'post': post})


@login_required
@staff_permission_required
def post_archive(request, pk):
    post = get_object_or_404(JobPost, pk=pk, staff=request.user, archived=False)
    if request.method == 'POST':
        form = ArchiveForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            other = form.cleaned_data['other_reason']
            # create ArchivedJob
            archived = ArchivedJob.objects.create(
                original_id=post.id,
                staff=post.staff,
                title=post.title,
                position_title=post.position_title,
                job_type=post.job_type,
                experience=post.experience,
                job_number=post.job_number,
                job_description=post.job_description,
                qualification=post.qualification,
                location=post.location,
                additional_info=post.additional_info,
                about_company=post.about_company,
                post_date=post.post_date,
                archive_reason=reason,
                archive_reason_other=other if reason == 'other' else ''
            )
            post.archived = True
            post.save()
            messages.success(request, 'Job archived.')
            return redirect('staff_url:post_list')
    else:
        form = ArchiveForm()
    return render(request, 'job/post_confirm_archive.html', {'form': form, 'post': post})


@login_required
@staff_permission_required
def post_delete(request, pk):
    post = get_object_or_404(JobPost, pk=pk, staff=request.user)
    if request.method == 'POST':
        form = DeleteForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            other = form.cleaned_data['other_reason']
            # save deletion log
            DeletionLog.objects.create(
                job_number=post.job_number,
                title=post.title,
                staff_username=post.staff.username,
                delete_reason=reason,
                delete_reason_other=other if reason == 'other' else ''
            )
            post.delete()
            messages.success(request, 'Job post deleted.')
            return redirect('staff_url:post_list')
    else:
        form = DeleteForm()
    return render(request, 'job/post_confirm_delete.html', {'form': form, 'post': post})


@login_required
@staff_permission_required
def archived_list(request):
    archives = ArchivedJob.objects.filter(staff=request.user).order_by('-archived_date')
    return render(request, 'job/archived_list.html', {'archives': archives})

@login_required
@staff_permission_required
def post_unarchive(request, pk):

    archived = get_object_or_404(ArchivedJob, pk=pk, staff=request.user)

    try:
        post = JobPost.objects.get(id=archived.original_id, staff=request.user)
        post.archived = False
        post.save()

        # Optional cleanup: remove record from ArchivedJob
        archived.delete()

        messages.success(request, "Job post successfully unarchived.")
    except JobPost.DoesNotExist:
        messages.error(request, "Original job post not found. Cannot unarchive.")

    return redirect('staff_url:archived_list')


#Added for submission of CV

@login_required
def staff_job_list(request):
    # list of staff's own job posts (you likely already have this)
    posts = JobPost.objects.filter(staff=request.user, archived=False)
    return render(request, 'job/post_list.html', {'posts': posts})

@login_required
def view_applicants(request, job_number):
    job = get_object_or_404(JobPost, job_number=job_number, staff=request.user)
    applicants = JobApplication.objects.filter(job=job).order_by('-applied_at')
    return render(request, 'job/applicant_list.html', {'job': job, 'applicants': applicants})

@login_required
def review_applicant(request, app_id, action):
    """
    action: 'accept' or 'reject'
    Only staff who posted the job can do this.
    """
    application = get_object_or_404(JobApplication, id=app_id)
    if application.job.staff != request.user:
        return HttpResponseForbidden("Not allowed")

    if action == 'accept':
        application.mark_accepted()
        messages.success(request, f"{application.applicant.username} accepted.")
    elif action == 'reject':
        application.mark_rejected()
        messages.success(request, f"{application.applicant.username} rejected and blocked for 6 months.")
    else:
        messages.error(request, "Unknown action.")
    return redirect('staff:view_applicants', job_number=application.job.job_number)

@login_required
def accepted_applicants(request):
    # show all accepted applicants for this staff's jobs, with search by name/job_number
    qs = JobApplication.objects.filter(job__staff=request.user, status=JobApplication.STATUS_ACCEPTED)
    q = request.GET.get('q')
    if q:
        qs = qs.filter(
            Q(applicant__username__icontains=q) |
            Q(job__job_number__icontains=q) |
            Q(job__title__icontains=q)
        )
    return render(request, 'job/accepted_applicants.html', {'applications': qs, 'q': q})