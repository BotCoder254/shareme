from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from files.models import FileItem, FileCategory, Folder
from accounts.models import UserProfile
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

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

@login_required
def stats(request):
    """System statistics view"""
    # Only allow staff/admin users to access this page
    if not request.user.is_staff:
        return redirect('core:dashboard')
    
    # Files statistics
    total_files = FileItem.objects.count()
    total_folders = Folder.objects.count()
    total_storage = FileItem.objects.aggregate(Sum('file_size'))['file_size__sum'] or 0
    avg_file_size = FileItem.objects.aggregate(Avg('file_size'))['file_size__avg'] or 0
    
    # Recent activity
    last_week = timezone.now() - timedelta(days=7)
    files_last_week = FileItem.objects.filter(created_at__gte=last_week).count()
    folders_last_week = Folder.objects.filter(created_at__gte=last_week).count()
    
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=last_week).count()
    storage_by_user = UserProfile.objects.values('user__username').annotate(
        total_storage=Sum('storage_used')
    ).order_by('-total_storage')[:5]
    
    # Format storage numbers
    for user in storage_by_user:
        user['readable_storage'] = FileItem.get_readable_size(user['total_storage'])
    
    context = {
        'total_files': total_files,
        'total_folders': total_folders,
        'total_storage': FileItem.get_readable_size(total_storage),
        'avg_file_size': FileItem.get_readable_size(avg_file_size),
        'files_last_week': files_last_week,
        'folders_last_week': folders_last_week,
        'total_users': total_users,
        'active_users': active_users,
        'storage_by_user': storage_by_user,
        'active_percentage': int((active_users / total_users * 100) if total_users > 0 else 0),
    }
    
    return render(request, 'core/stats.html', context)

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
