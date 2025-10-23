from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

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
