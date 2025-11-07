# staff_app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os
import random, string

# ADDED: helper for profile upload path
def staff_profile_upload_path(instance, filename):
    # media/staff_profiles/user_<id>/<filename>
    return os.path.join('staff_profiles', f'user_{instance.user.id}', filename)

# ADDED: default profile image path function
def default_profile_image():
    return 'defaults/default_profile.png'  # make sure this file exists in MEDIA_ROOT/defaults/

class StaffProfile(models.Model):
    STATUS_PENDING_VERIFICATION = 'PV'
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


#ADDED FOR JOB POSTING
JOB_TYPE_CHOICES = [
    ('part_time', 'Part Time'),
    ('full_time', 'Full Time'),
    ('other', 'Other'),
]

REASON_CHOICES = [
    ('filled', 'Position Filled'),
    ('expired', 'Expired'),
    ('company_closed', 'Company Closed'),
    ('other', 'Other (specify)'),
]

def generate_job_number():
    date = timezone.now().strftime('%Y%m%d')
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f'JOB-{date}-{rand}'


class JobPost(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_posts')
    title = models.CharField(max_length=255)
    position_title = models.CharField(max_length=255)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    experience = models.CharField(max_length=100, help_text='e.g. 2 years')
    job_number = models.CharField(max_length=50, unique=True, blank=True)
    job_description = models.TextField()
    qualification = models.TextField()
    location = models.CharField(max_length=255)
    additional_info = models.TextField(blank=True, null=True)
    about_company = models.TextField(blank=True, null=True)
    post_date = models.DateTimeField(auto_now_add=True)
    archived = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.job_number:
            # ensure unique job number
            val = generate_job_number()
            while JobPost.objects.filter(job_number=val).exists():
                val = generate_job_number()
            self.job_number = val
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.job_number} - {self.title}'


class ArchivedJob(models.Model):
    original_id = models.IntegerField()  # store original JobPost id for reference
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    position_title = models.CharField(max_length=255)
    job_type = models.CharField(max_length=20)
    experience = models.CharField(max_length=100)
    job_number = models.CharField(max_length=50)
    job_description = models.TextField()
    qualification = models.TextField()
    location = models.CharField(max_length=255)
    additional_info = models.TextField(blank=True, null=True)
    about_company = models.TextField(blank=True, null=True)
    post_date = models.DateTimeField()
    archived_date = models.DateTimeField(auto_now_add=True)
    archive_reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    archive_reason_other = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'ARCHIVE {self.job_number} - {self.title}'


class DeletionLog(models.Model):
    job_number = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    staff_username = models.CharField(max_length=150, blank=True, null=True)
    deleted_date = models.DateTimeField(auto_now_add=True)
    delete_reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    delete_reason_other = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'DELETED {self.job_number}'