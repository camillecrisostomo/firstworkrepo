# staff_app/urls.py
from django.urls import path
from . import views

app_name = 'staff_url'

urlpatterns = [
    path('register/', views.register_staff, name='register'),
    path('verify/', views.verify_code, name='verify'),
    path('resend-code/', views.resend_code, name='resend_code'),
    path('login/', views.staff_login, name='login'),
    path('logout/', views.staff_logout, name='logout'),
    path('dashboard/', views.staff_dashboard, name='dashboard'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-success/', views.reset_success, name='reset_success'),
    # Admin approval views
    path('approvals/', views.staff_approvals, name='approvals'),  # list + filter
    path('approvals/action/', views.staff_approval_action, name='approval_action'),  # approve / reject
]
