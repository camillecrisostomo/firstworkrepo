from django.urls import path
from . import views

app_name = 'admin_app'   # namespace: 'adminreg' para hindi mag-conflict sa django 'admin'
urlpatterns = [
    path('register/', views.register_admin, name='register'),
]
