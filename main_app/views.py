from django.shortcuts import render
from staff_app.models import JobPost

def landing_page(request):
    # Get all non-archived jobs ordered by most recent
    jobs = JobPost.objects.filter(archived=False).order_by('-post_date')
    return render(request, 'main/landing.html', {'jobs': jobs})

def about_page(request):
    return render(request, 'main/about.html')