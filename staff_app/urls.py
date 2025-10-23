from django.urls import path
from . import views

app_name = 'staff_url'

urlpatterns = [
    path('register/', views.register_view, name='register'),
]