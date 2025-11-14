from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('verify/<int:user_id>/', views.verify_code_view, name='verify'),
    path('resend/<int:user_id>/', views.resend_code_view, name='resend'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('profile/', views.profile_view, name='profile'),
    
    path('career/', views.career_search, name='career_search'),
    path('career/<str:job_number>/', views.job_detail, name='job_detail'),

    #added for submission of CV
    path('career/<str:job_number>/', views.job_detail, name='job_detail'),
    path('career/<str:job_number>/apply/', views.apply_job, name='apply_job'),
    path('applications/<int:app_id>/remove/', views.remove_application, name='remove_application'),
]
