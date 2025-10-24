from django.urls import path
from . import views

app_name = 'staff_url'

urlpatterns = [
    path('register/', views.register_staff, name='register'),
    path('verify/<int:user_id>/', views.verify_email, name='verify_email'),
    path('login/', views.staff_login, name='login'),
    path('logout/', views.staff_logout, name='logout'),
    path('dashboard/', views.staff_dashboard, name='dashboard'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-success/', views.reset_success, name='reset_success'),
]