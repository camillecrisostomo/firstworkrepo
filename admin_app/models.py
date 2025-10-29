# admin_app/models.py
from django.db import models
from django.utils import timezone

class AdminLog(models.Model):
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]

    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    admin_username = models.CharField(max_length=150)
    target_user_email = models.EmailField(blank=True, null=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.action} by {self.admin_username} -> {self.target_user_email} at {self.created_at}"
