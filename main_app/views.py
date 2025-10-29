from django.shortcuts import render

def landing_page(request):
    return render(request, 'main/landing.html')

def about_page(request):
    return render(request, 'main/about.html')