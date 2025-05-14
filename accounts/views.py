from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile
from django.db.models import Sum
from files.models import FileItem
from .forms import UserSignUpForm, UserUpdateForm, ProfileUpdateForm

def signup(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
        
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username, password=raw_password)
            login(request, user)
            messages.success(request, "Your account has been created successfully!")
            return redirect('core:dashboard')
    else:
        form = UserSignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def profile(request):
    """User profile view"""
    # Get total storage used
    storage_used = FileItem.objects.filter(user=request.user).aggregate(Sum('file_size'))['file_size__sum'] or 0
    
    # Update profile with current storage used
    profile = request.user.profile
    profile.storage_used = storage_used
    profile.save()
    
    # Get recent activity
    recent_files = FileItem.objects.filter(user=request.user).order_by('-updated_at')[:5]
    
    context = {
        'user': request.user,
        'profile': profile,
        'recent_files': recent_files,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_edit(request):
    """Edit user profile view"""
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    return render(request, 'accounts/profile_edit.html', context)
