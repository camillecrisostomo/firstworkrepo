from django.contrib import admin
from .models import UserProfile, EmailVerification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'middle_name', 'created_at']
    search_fields = ['user__username', 'user__email', 'middle_name']

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'resend_count']
    readonly_fields = ['created_at']
    search_fields = ['user__username', 'user__email', 'code']
