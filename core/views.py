from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from files.models import FileItem, FileCategory
from django.db.models import Count, Sum

def home(request):
    """Landing page view"""
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return render(request, 'core/dashboard.html')
    
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    """User dashboard view"""
    # Get user's files stats
    total_files = FileItem.objects.filter(user=request.user).count()
    favorites = FileItem.objects.filter(user=request.user, is_favorite=True).count()
    
    # Get file categories with counts
    categories = FileCategory.objects.annotate(
        file_count=Count('fileitem', filter=FileItem.objects.filter(user=request.user).values('id'))
    )
    
    # Get recent files
    recent_files = FileItem.objects.filter(user=request.user).order_by('-updated_at')[:5]
    
    context = {
        'total_files': total_files,
        'favorites': favorites,
        'categories': categories,
        'recent_files': recent_files,
    }
    
    return render(request, 'core/dashboard.html', context)

def about(request):
    """About page view"""
    return render(request, 'core/about.html')

def features(request):
    """Features page view"""
    return render(request, 'core/features.html')

def pricing(request):
    """Pricing page view"""
    return render(request, 'core/pricing.html')

def contact(request):
    """Contact page view"""
    return render(request, 'core/contact.html')
