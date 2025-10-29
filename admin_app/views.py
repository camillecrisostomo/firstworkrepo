# admin_app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.core.mail import send_mail

from .forms import AdminLoginForm, ApprovalActionForm
from .models import AdminLog

# Import StaffProfile from staff_app (this is the single source of truth)
from staff_app.models import StaffProfile

def _is_superuser(user):
    return user.is_superuser

def admin_login(request):
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_superuser:
                login(request, user)
                messages.success(request, "Welcome, Admin!")
                return redirect('admin_url:dashboard')
            else:
                messages.error(request, "Invalid admin credentials.")
    else:
        form = AdminLoginForm()
    return render(request, 'admin_design/login.html', {'form': form})

@login_required
@user_passes_test(_is_superuser)
def admin_dashboard(request):
    stats = {
        'pending_verification': StaffProfile.objects.filter(status=StaffProfile.STATUS_PENDING_VERIFICATION).count(),
        'pending_approval': StaffProfile.objects.filter(status=StaffProfile.STATUS_PENDING_APPROVAL).count(),
        'approved': StaffProfile.objects.filter(status=StaffProfile.STATUS_APPROVED).count(),
        'rejected': StaffProfile.objects.filter(status=StaffProfile.STATUS_REJECTED).count(),
    }
    return render(request, 'admin_design/dashboard.html', stats)

@login_required
@user_passes_test(_is_superuser)
def staff_approval_list(request):
    # filter by exact status if q provided
    q = request.GET.get('q')
    if q:
        profiles = StaffProfile.objects.filter(status__iexact=q).order_by('-created_at')
    else:
        profiles = StaffProfile.objects.all().order_by('-created_at')

    form = ApprovalActionForm()
    return render(request, 'admin_design/staff_approvals.html', {'profiles': profiles, 'form': form, 'filter': q or ''})

@login_required
@user_passes_test(_is_superuser)
def staff_approval_action(request):
    if request.method != 'POST':
        return redirect('admin_url:staff_approvals')

    form = ApprovalActionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid form submission.")
        return redirect('admin_url:staff_approvals')

    profile_id = form.cleaned_data['profile_id']
    action = form.cleaned_data['action']
    note = form.cleaned_data.get('admin_note', '')

    profile = get_object_or_404(StaffProfile, id=profile_id)

    if action == 'approve':
        profile.status = StaffProfile.STATUS_APPROVED
        profile.admin_note = note
        profile.save()

        # notify staff
        try:
            send_mail(
                "Staff Account Approved",
                f"Hi {profile.user.get_full_name()},\n\nYour staff account has been approved. You can now log in.",
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                fail_silently=True
            )
        except Exception:
            pass

        AdminLog.objects.create(action='approve', admin_username=request.user.username, target_user_email=profile.user.email, note=note)
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
        except Exception:
            pass

        AdminLog.objects.create(action='reject', admin_username=request.user.username, target_user_email=profile.user.email, note=note)
        messages.success(request, f"{profile.user.get_full_name()} rejected.")
    else:
        messages.error(request, "Unknown action.")

    return redirect('admin_url:staff_approvals')

@login_required
@user_passes_test(_is_superuser)
def admin_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('admin_url:login')
