# staff_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

# ADDED: helper for profile upload path
def staff_profile_upload_path(instance, filename):
    # media/staff_profiles/user_<id>/<filename>
    return os.path.join('staff_profiles', f'user_{instance.user.id}', filename)

# ADDED: default profile image path function
def default_profile_image():
    return 'defaults/default_profile.png'  # make sure this file exists in MEDIA_ROOT/defaults/

class StaffProfile(models.Model):
    STATUS_PENDING_VERIFICATION = 'Pending Verification'
    STATUS_PENDING_APPROVAL = 'Pending Admin Approval'
    STATUS_APPROVED = 'Approved'
    STATUS_REJECTED = 'Rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING_VERIFICATION, 'Pending Verification'),
        (STATUS_PENDING_APPROVAL, 'Pending Admin Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    middle_name = models.CharField(max_length=50, blank=True)

    # ADDED: profile image field with default
    profile_image = models.ImageField(
        upload_to=staff_profile_upload_path,
        default=default_profile_image,
        blank=True,
        null=True
    )

    verification_code = models.CharField(max_length=6, blank=True, null=True)
    is_verified = models.BooleanField(default=False)  # email verification
    resend_count = models.IntegerField(default=0)
    code_sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING_VERIFICATION)
    # Optional: reason for rejection
    admin_note = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email}) - {self.status}"
