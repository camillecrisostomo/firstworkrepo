from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main_app.urls')),
    path('admin_app/', include('admin_app.urls')),
    path('user/', include('user_app.urls')),
    path('staff/', include('staff_app.urls')),
]
