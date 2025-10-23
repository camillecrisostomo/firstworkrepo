from django.shortcuts import render

def register_admin(request):
    # pwede itong custom admin user creation page or redirect to staff creation
    return render(request, 'admin/register.html')