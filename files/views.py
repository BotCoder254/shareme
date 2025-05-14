from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import FileItem, FileCategory, SharedFile, Folder, SharedFolder, FileShareLink
from .forms import FileUploadForm, FileCategoryForm, ShareLinkForm, FolderForm
import os
from django.urls import reverse
from django.utils import timezone

@login_required
def file_list(request):
    """View to list all files of the user"""
    category_id = request.GET.get('category')
    favorite = request.GET.get('favorite')
    query = request.GET.get('q')
    
    files = FileItem.objects.filter(user=request.user)
    
    # Apply filters
    if category_id:
        files = files.filter(category_id=category_id)
    
    if favorite:
        files = files.filter(is_favorite=True)
    
    if query:
        files = files.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )
    
    # Get all categories for sidebar
    categories = FileCategory.objects.all()
    
    context = {
        'files': files,
        'categories': categories,
        'current_category': category_id,
        'is_favorite': favorite == '1',
        'query': query,
    }
    
    return render(request, 'files/file_list.html', context)

@login_required
def file_detail(request, file_id):
    """View to show details of a specific file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    shared_with = SharedFile.objects.filter(file=file)
    
    context = {
        'file': file,
        'shared_with': shared_with,
    }
    
    return render(request, 'files/file_detail.html', context)

@login_required
def file_upload(request):
    """View to upload a new file"""
    folders = Folder.objects.filter(user=request.user, parent=None).prefetch_related('subfolders')
    
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if the user has enough storage space
            file_size = request.FILES['file'].size
            profile = request.user.profile
            
            if not profile.has_storage_available(file_size):
                messages.error(
                    request, 
                    f"You don't have enough storage space. Available: {profile.get_available_storage_readable()}, "
                    f"Required: {FileItem.get_readable_size(file_size)}"
                )
                return render(request, 'files/file_upload.html', {
                    'form': form,
                    'categories': FileCategory.objects.all(),
                    'current_folder': request.POST.get('folder', None),
                    'folders': folders,
                })
                
            # User has enough space, create the file
            file_instance = form.save(commit=False)
            file_instance.user = request.user
            file_instance.file_size = file_size
            
            # Handle folder assignment
            folder_id = request.POST.get('folder')
            if folder_id:
                try:
                    folder = Folder.objects.get(id=folder_id, user=request.user)
                    file_instance.folder = folder
                except Folder.DoesNotExist:
                    pass
                
            file_instance.save()
            
            # Update user's storage used
            profile.storage_used += file_instance.file_size
            profile.save()
            
            messages.success(request, "File uploaded successfully!")
            
            # Return to the appropriate folder
            if folder_id:
                return redirect('files:folder_contents', folder_id=folder_id)
            return redirect('files:file_list')
    else:
        form = FileUploadForm()
        folder_id = request.GET.get('folder')
        current_folder = None
        if folder_id:
            try:
                current_folder = Folder.objects.get(id=folder_id, user=request.user)
            except Folder.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'categories': FileCategory.objects.all(),
        'current_folder': current_folder,
        'folders': folders,
    }
    
    return render(request, 'files/file_upload.html', context)

@login_required
def file_delete(request, file_id):
    """View to delete a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    if request.method == 'POST':
        # Capture file size before deletion
        file_size = file.file_size
        
        # Delete file
        file.delete()
        
        # Remove file size from user's storage
        profile = request.user.profile
        profile.storage_used = max(0, profile.storage_used - file_size)  # Prevent negative values
        profile.save()
        
        messages.success(request, "File deleted successfully!")
        
        # Check if redirecting to a folder
        folder_id = request.GET.get('folder')
        if folder_id:
            return redirect(f'files:file_list?folder={folder_id}')
        return redirect('files:file_list')
    
    context = {
        'file': file,
    }
    
    return render(request, 'files/file_delete.html', context)

@login_required
def file_toggle_favorite(request, file_id):
    """Toggle favorite status of a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    file.is_favorite = not file.is_favorite
    file.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'is_favorite': file.is_favorite
        })
    
    return redirect('files:file_detail', file_id=file.id)

@login_required
def file_share(request, file_id):
    """Share a file with another user"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        access_level = request.POST.get('access_level', 'view')
        
        try:
            user_to_share_with = User.objects.get(username=username)
            
            # Don't allow sharing with self
            if user_to_share_with == request.user:
                messages.error(request, "You cannot share a file with yourself.")
                return redirect('files:file_detail', file_id=file.id)
            
            # Check if already shared
            if SharedFile.objects.filter(file=file, shared_with=user_to_share_with).exists():
                messages.info(request, f"File is already shared with {username}.")
            else:
                SharedFile.objects.create(
                    file=file,
                    shared_by=request.user,
                    shared_with=user_to_share_with,
                    access_level=access_level
                )
                messages.success(request, f"File shared with {username} successfully!")
                
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' does not exist.")
        
        return redirect('files:file_detail', file_id=file.id)
    
    return redirect('files:file_detail', file_id=file.id)

@login_required
def file_download(request, file_id):
    """Download a file"""
    # Check if user owns the file or it's shared with them
    file = get_object_or_404(
        FileItem, 
        Q(id=file_id, user=request.user) | 
        Q(id=file_id, shared_with__shared_with=request.user)
    )
    
    # Check if the user is over storage limit and enforce if needed
    # We allow downloads of already stored files even if over limit
    profile = request.user.profile
    if profile.storage_limit_enforced and profile.get_storage_usage_percentage() >= 100:
        messages.warning(request, "You have reached your storage limit. Some features may be restricted until you free up space.")
    
    file_path = file.file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = f'attachment; filename="{file.filename()}"'
            return response
    
    messages.error(request, "File not found.")
    return redirect('files:file_list')

@login_required
def shared_files(request):
    """View to list files shared with the user"""
    shared = SharedFile.objects.filter(shared_with=request.user)
    
    context = {
        'shared_files': shared,
    }
    
    return render(request, 'files/shared_files.html', context)

@login_required
def folder_unshare(request, folder_id):
    """Remove sharing access for a folder"""
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        
        try:
            user_to_unshare_with = User.objects.get(username=username)
            
            # Check if folder is shared with this user
            shared_folder = SharedFolder.objects.filter(folder=folder, shared_with=user_to_unshare_with)
            
            if shared_folder.exists():
                shared_folder.delete()
                messages.success(request, f"Folder access for {username} has been removed.")
            else:
                messages.info(request, f"Folder is not shared with {username}.")
                
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' does not exist.")
        
        return redirect('files:file_list')
    
    # Get all users this folder is shared with
    shared_with = SharedFolder.objects.filter(folder=folder)
    
    context = {
        'folder': folder,
        'shared_with': shared_with,
    }
    
    return render(request, 'files/folder_unshare.html', context)

@login_required
def folder_share(request, folder_id):
    """Share a folder with another user"""
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        access_level = request.POST.get('access_level', 'view')
        
        try:
            user_to_share_with = User.objects.get(username=username)
            
            # Don't allow sharing with self
            if user_to_share_with == request.user:
                messages.error(request, "You cannot share a folder with yourself.")
                return redirect('files:file_list')
            
            # Check if already shared
            if SharedFolder.objects.filter(folder=folder, shared_with=user_to_share_with).exists():
                messages.info(request, f"Folder is already shared with {username}.")
            else:
                SharedFolder.objects.create(
                    folder=folder,
                    shared_by=request.user,
                    shared_with=user_to_share_with,
                    access_level=access_level
                )
                messages.success(request, f"Folder shared with {username} successfully!")
                
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' does not exist.")
        
        return redirect('files:file_list')
    
    context = {
        'folder': folder,
    }
    
    return render(request, 'files/folder_share.html', context)

@login_required
def create_folder(request):
    """View to create a new folder"""
    parent_folder_id = request.GET.get('parent')
    parent_folder = None
    
    if parent_folder_id:
        try:
            parent_folder = Folder.objects.get(id=parent_folder_id, user=request.user)
        except Folder.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = FolderForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.user = request.user
            
            # Set parent folder if provided
            if parent_folder:
                folder.parent = parent_folder
                
            folder.save()
            messages.success(request, "Folder created successfully!")
            
            # Handle redirect
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
                
            # Redirect to the parent folder if applicable
            if parent_folder:
                return redirect('files:folder_contents', folder_id=parent_folder.id)
                
            return redirect('files:file_list')
    else:
        form = FolderForm()
    
    context = {
        'form': form,
        'parent_folder': parent_folder,
    }
    
    return render(request, 'files/create_folder.html', context)

@login_required
def folder_detail(request, folder_id):
    """View folder details and manage subfolders"""
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    subfolders = folder.subfolders.all()
    files = FileItem.objects.filter(folder=folder, user=request.user)
    
    # Get folder path
    folder_path = []
    current = folder
    while current:
        folder_path.insert(0, current)
        current = current.parent
    
    context = {
        'folder': folder,
        'subfolders': subfolders,
        'files': files,
        'folder_path': folder_path,
    }
    
    return render(request, 'files/folder_detail.html', context)

@login_required
def folder_contents(request, folder_id):
    """View to display the contents of a folder"""
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    files = FileItem.objects.filter(folder=folder, user=request.user)
    subfolders = folder.subfolders.all()
    
    # Get folder breadcrumb path
    folder_path = []
    current = folder
    while current:
        folder_path.insert(0, current)
        current = current.parent
    
    context = {
        'folder': folder,
        'files': files,
        'subfolders': subfolders,
        'folder_path': folder_path,
        'categories': FileCategory.objects.all(),
    }
    
    return render(request, 'files/folder_contents.html', context)

@login_required
def create_file_share_link(request, file_id):
    """Create a public share link for a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    if request.method == 'POST':
        form = ShareLinkForm(request.POST)
        if form.is_valid():
            share_link = form.save(commit=False)
            share_link.file = file
            share_link.created_by = request.user
            
            # Handle password
            if form.cleaned_data.get('password'):
                # Hash the password before saving
                from django.contrib.auth.hashers import make_password
                share_link.password = make_password(form.cleaned_data.get('password'))
            
            # Handle expiry date
            expires_in = form.cleaned_data.get('expires_in')
            if expires_in == 'never':
                share_link.expires_at = None
            elif expires_in == 'custom':
                share_link.expires_at = form.cleaned_data.get('custom_expiry_date')
            else:
                # Parse the time period (1d, 7d, 30d)
                days = int(expires_in[:-1])
                share_link.expires_at = timezone.now() + timezone.timedelta(days=days)
            
            share_link.save()
            
            messages.success(request, "Share link created successfully!")
            return redirect('files:file_detail', file_id=file.id)
    else:
        form = ShareLinkForm()
    
    context = {
        'form': form,
        'file': file,
    }
    
    return render(request, 'files/create_share_link.html', context)

@login_required
def create_folder_share_link(request, folder_id):
    """Create a public share link for a folder"""
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    
    if request.method == 'POST':
        form = ShareLinkForm(request.POST)
        if form.is_valid():
            share_link = form.save(commit=False)
            share_link.folder = folder
            share_link.created_by = request.user
            
            # Handle password
            if form.cleaned_data.get('password'):
                # Hash the password before saving
                from django.contrib.auth.hashers import make_password
                share_link.password = make_password(form.cleaned_data.get('password'))
            
            # Handle expiry date
            expires_in = form.cleaned_data.get('expires_in')
            if expires_in == 'never':
                share_link.expires_at = None
            elif expires_in == 'custom':
                share_link.expires_at = form.cleaned_data.get('custom_expiry_date')
            else:
                # Parse the time period (1d, 7d, 30d)
                days = int(expires_in[:-1])
                share_link.expires_at = timezone.now() + timezone.timedelta(days=days)
            
            share_link.save()
            
            messages.success(request, "Share link created successfully!")
            return redirect('files:file_list')
    else:
        form = ShareLinkForm()
    
    context = {
        'form': form,
        'folder': folder,
    }
    
    return render(request, 'files/create_share_link.html', context)

def access_share_link(request, uuid):
    """View for accessing a shared file or folder via a public link"""
    share_link = get_object_or_404(FileShareLink, uuid=uuid)
    
    # Check if the link is still valid
    if not share_link.is_valid():
        return render(request, 'files/share_link_expired.html')
    
    # Handle password protection
    if share_link.password:
        if request.method == 'POST':
            password = request.POST.get('password')
            if share_link.check_password(password):
                # Password is correct, proceed
                request.session[f'share_link_access_{uuid}'] = True
            else:
                messages.error(request, "Incorrect password")
                return render(request, 'files/share_link_password.html', {'share_link': share_link})
        elif not request.session.get(f'share_link_access_{uuid}'):
            # First visit, show password form
            return render(request, 'files/share_link_password.html', {'share_link': share_link})
    
    # Increment access count
    share_link.increment_access_count()
    
    # Serve the file or folder contents
    if share_link.file:
        return render(request, 'files/shared_file_view.html', {'share_link': share_link, 'file': share_link.file})
    else:
        # Get all files in this folder
        files = FileItem.objects.filter(folder=share_link.folder)
        
        # Get all subfolders in this folder that should be accessible
        subfolders = Folder.objects.filter(parent=share_link.folder)
        
        return render(request, 'files/shared_folder_view.html', {
            'share_link': share_link,
            'folder': share_link.folder,
            'files': files,
            'folders': subfolders,
        })

@login_required
def manage_share_links(request, file_id=None, folder_id=None):
    """View to manage all share links for a file or folder"""
    share_links = []
    item = None
    
    if file_id:
        item = get_object_or_404(FileItem, id=file_id, user=request.user)
        share_links = FileShareLink.objects.filter(file=item, created_by=request.user)
        back_url = reverse('files:file_detail', args=[file_id])
    elif folder_id:
        item = get_object_or_404(Folder, id=folder_id, user=request.user)
        share_links = FileShareLink.objects.filter(folder=item, created_by=request.user)
        back_url = reverse('files:file_list')
    
    context = {
        'item': item,
        'share_links': share_links,
        'back_url': back_url,
        'is_file': file_id is not None,
    }
    
    return render(request, 'files/manage_share_links.html', context)

@login_required
def delete_share_link(request, link_id):
    """Delete a share link"""
    share_link = get_object_or_404(FileShareLink, id=link_id, created_by=request.user)
    
    if request.method == 'POST':
        if share_link.file:
            file_id = share_link.file.id
            share_link.delete()
            messages.success(request, "Share link deleted successfully!")
            return redirect('files:manage_share_links', file_id=file_id)
        else:
            folder_id = share_link.folder.id
            share_link.delete()
            messages.success(request, "Share link deleted successfully!")
            return redirect('files:manage_share_links', folder_id=folder_id)
    
    context = {
        'share_link': share_link,
    }
    
    return render(request, 'files/delete_share_link.html', context)

@login_required
def folder_delete(request, folder_id):
    """View to delete a folder and all its contents"""
    folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    parent_id = folder.parent.id if folder.parent else None
    
    if request.method == 'POST':
        # Get all files in this folder and subfolders
        files = folder.get_all_files()
        
        # Calculate total file size
        total_size = sum(file.file_size for file in files)
        
        # Update user's storage used
        profile = request.user.profile
        profile.storage_used -= total_size
        profile.save()
        
        # Delete folder (will cascade to all subfolders and files)
        folder.delete()
        
        messages.success(request, f"Folder '{folder.name}' and all its contents deleted successfully!")
        
        # Redirect back to the parent folder if it exists
        if parent_id:
            return redirect('files:folder_contents', folder_id=parent_id)
        return redirect('files:file_list')
    
    context = {
        'folder': folder,
    }
    
    return render(request, 'files/folder_delete.html', context)
