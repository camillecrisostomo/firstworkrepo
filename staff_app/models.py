from django.db import models
from django.contrib.auth.models import User
import uuid

class StaffProfile(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=10, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    resend_count = models.PositiveIntegerField(default=0)
    last_resend_time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.user.username
