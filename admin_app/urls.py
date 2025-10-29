# admin_app/urls.py
from django.urls import path
from . import views

app_name = 'admin_url'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('dashboard/', views.admin_dashboard, name='dashboard'),
    path('staff-approvals/', views.staff_approval_list, name='staff_approvals'),
    path('staff-approvals/action/', views.staff_approval_action, name='staff_approval_action'),
    path('logout/', views.admin_logout, name='logout'),
]
