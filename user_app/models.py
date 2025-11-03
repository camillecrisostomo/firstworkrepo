from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import os

# ADDED: helper for user profile upload path
def user_profile_upload_path(instance, filename):
    # media/user_profiles/user_<id>/<filename>
    return os.path.join('user_profiles', f'user_{instance.user.id}', filename)

# ADDED: default profile image path function
def default_profile_image():
    return 'defaults/default_profile.png'  # make sure this file exists in MEDIA_ROOT/defaults/

class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    resend_count = models.IntegerField(default=0)

    def is_expired(self):
        # expiry: 10 minutes
        expire_at = self.created_at + timezone.timedelta(minutes=10)
        return timezone.now() > expire_at

    def __str__(self):
        return f"{self.user.email} - {self.code}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    middle_name = models.CharField(max_length=50, blank=True)
    
    # ADDED: profile image field with default
    profile_image = models.ImageField(
        upload_to=user_profile_upload_path,
        default=default_profile_image,
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"
