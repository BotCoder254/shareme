from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import FileItem, FileCategory, SharedFile, Folder, SharedFolder, FileShareLink
from .forms import FileUploadForm, FileCategoryForm, ShareLinkForm
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
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_instance = form.save(commit=False)
            file_instance.user = request.user
            
            # Get file size
            file_instance.file_size = request.FILES['file'].size
            
            file_instance.save()
            
            # Update user's storage used
            profile = request.user.profile
            profile.storage_used += file_instance.file_size
            profile.save()
            
            messages.success(request, "File uploaded successfully!")
            return redirect('files:file_list')
    else:
        form = FileUploadForm()
    
    context = {
        'form': form,
        'categories': FileCategory.objects.all(),
    }
    
    return render(request, 'files/file_upload.html', context)

@login_required
def file_delete(request, file_id):
    """View to delete a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    if request.method == 'POST':
        # Remove file size from user's storage
        profile = request.user.profile
        profile.storage_used -= file.file_size
        profile.save()
        
        # Delete file
        file.delete()
        
        messages.success(request, "File deleted successfully!")
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
    parent_id = request.GET.get('parent')
    parent_folder = None
    
    if parent_id:
        parent_folder = get_object_or_404(Folder, id=parent_id, user=request.user)
    
    if request.method == 'POST':
        folder_name = request.POST.get('folder_name')
        parent_id = request.POST.get('parent')
        
        if not folder_name:
            messages.error(request, "Folder name is required.")
            return redirect('files:file_list')
        
        # Check if folder already exists
        if parent_id:
            parent = get_object_or_404(Folder, id=parent_id, user=request.user)
            if Folder.objects.filter(user=request.user, name=folder_name, parent=parent).exists():
                messages.error(request, f"Folder '{folder_name}' already exists in this location.")
                return redirect('files:file_list')
        else:
            if Folder.objects.filter(user=request.user, name=folder_name, parent__isnull=True).exists():
                messages.error(request, f"Folder '{folder_name}' already exists in the root directory.")
                return redirect('files:file_list')
        
        # Create the folder
        folder = Folder(
            user=request.user,
            name=folder_name
        )
        
        if parent_id:
            folder.parent = get_object_or_404(Folder, id=parent_id, user=request.user)
        
        folder.save()
        messages.success(request, f"Folder '{folder_name}' created successfully!")
        
        # Redirect back to the parent folder if it exists
        if parent_id:
            return redirect(f'files:file_list?folder={parent_id}')
        return redirect('files:file_list')
    
    context = {
        'parent_folder': parent_folder,
    }
    
    return render(request, 'files/create_folder.html', context)

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
            return redirect(f'files:file_list?folder={parent_id}')
        return redirect('files:file_list')
    
    context = {
        'folder': folder,
    }
    
    return render(request, 'files/folder_delete.html', context)

@login_required
def folder_contents(request, folder_id):
    """View to show the contents of a folder"""
    # Check if the user owns the folder or it's shared with them
    folder = get_object_or_404(
        Folder, 
        Q(id=folder_id, user=request.user) | 
        Q(id=folder_id, shared_with__shared_with=request.user)
    )
    
    # Get all files in this folder
    files = FileItem.objects.filter(folder=folder)
    
    # Get all subfolders in this folder
    subfolders = Folder.objects.filter(parent=folder)
    
    # Build breadcrumb navigation
    breadcrumbs = []
    current = folder
    while current:
        breadcrumbs.insert(0, current)
        current = current.parent
    
    # Get shared status if the folder doesn't belong to the user
    is_shared = False
    if folder.user != request.user:
        shared_folder = SharedFolder.objects.get(folder=folder, shared_with=request.user)
        is_shared = True
        access_level = shared_folder.access_level
    
    context = {
        'folder': folder,
        'files': files,
        'folders': subfolders,
        'breadcrumbs': breadcrumbs,
        'is_shared': is_shared,
        'access_level': access_level if is_shared else None,
        'current_folder': folder,
    }
    
    return render(request, 'files/file_list.html', context)

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
