from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .models import FileItem, FileCategory, SharedFile, Folder, SharedFolder, FileShareLink, FileVersion, Comment, CollaborationSession, CollaborationParticipant, AuditLog
from .forms import FileUploadForm, FileCategoryForm, ShareLinkForm, FolderForm, CommentForm, CollaborationSessionForm, ShareFileForm, ShareFolderForm
import os
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json
import uuid
import shutil

@login_required
def file_list(request):
    """View to list all files of the user"""
    category_id = request.GET.get('category')
    favorite = request.GET.get('favorite')
    query = request.GET.get('q')
    trash = request.GET.get('trash')
    
    if trash:
        # Show only files in trash
        files = FileItem.objects.filter(user=request.user, deleted_at__isnull=False)
    else:
        # Show only files not in trash
        files = FileItem.objects.filter(user=request.user, deleted_at__isnull=True)
    
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
        'is_trash': trash == '1',
        'query': query,
    }
    
    if trash:
        return render(request, 'files/trash.html', context)
    
    return render(request, 'files/file_list.html', context)

@login_required
def file_detail(request, file_id):
    """View to show details of a specific file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    shared_with = SharedFile.objects.filter(file=file)
    
    # Get file versions
    versions = file.versions.all().order_by('-version_number')
    current_version = file.get_current_version()
    
    # Get active collaboration session if any
    active_session = CollaborationSession.objects.filter(file=file, active=True).first()
    
    # Get comment count
    comment_count = Comment.objects.filter(file=file).count()
    
    context = {
        'file': file,
        'shared_with': shared_with,
        'versions': versions,
        'current_version': current_version,
        'version_count': versions.count(),
        'active_session': active_session,
        'comment_count': comment_count,
    }
    
    return render(request, 'files/file_detail.html', context)

@login_required
def file_upload(request):
    """View to upload a new file"""
    folders = Folder.objects.filter(user=request.user, parent=None).prefetch_related('subfolders')
    current_folder = None
    existing_file = None
    form = FileUploadForm()
    
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
                # Try to get current folder for the context
                folder_id = request.POST.get('folder')
                if folder_id:
                    try:
                        current_folder = Folder.objects.get(id=folder_id, user=request.user)
                    except Folder.DoesNotExist:
                        pass
                
                # Try to get existing file for the context
                existing_file_id = request.POST.get('existing_file')
                if existing_file_id:
                    try:
                        existing_file = FileItem.objects.get(id=existing_file_id, user=request.user)
                    except FileItem.DoesNotExist:
                        pass
                        
                return render(request, 'files/file_upload.html', {
                    'form': form,
                    'categories': FileCategory.objects.all(),
                    'current_folder': current_folder,
                    'folders': folders,
                    'existing_file': existing_file,
                })
            
            # Check if this is a new version of an existing file
            existing_file_id = request.POST.get('existing_file')
            if existing_file_id:
                try:
                    # Get the existing file
                    existing_file = FileItem.objects.get(id=existing_file_id, user=request.user)
                    
                    # Create a new version
                    version = FileVersion.create_version(
                        file_item=existing_file,
                        version_file=request.FILES['file'],
                        user=request.user
                    )
                    
                    # Update the existing file's information
                    existing_file.file_size = file_size
                    existing_file.title = form.cleaned_data['title']
                    existing_file.description = form.cleaned_data['description']
                    existing_file.category = form.cleaned_data['category']
                    existing_file.is_public = form.cleaned_data['is_public']
                    existing_file.updated_at = timezone.now()
                    existing_file.save()
                    
                    # Update user's storage used
                    profile.storage_used += file_size
                    profile.save()
                    
                    messages.success(request, f"New version (v{version.version_number}) of '{existing_file.title}' uploaded successfully!")
                    return redirect('files:file_detail', file_id=existing_file.id)
                
                except FileItem.DoesNotExist:
                    messages.error(request, "The file you're trying to update doesn't exist or you don't have permission to update it.")
            
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
            
            # Create the initial version
            FileVersion.create_version(
                file_item=file_instance,
                version_file=request.FILES['file'],
                user=request.user
            )
            
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
        existing_file_id = request.GET.get('existing_file')
        current_folder = None
        existing_file = None
        
        if folder_id:
            try:
                current_folder = Folder.objects.get(id=folder_id, user=request.user)
            except Folder.DoesNotExist:
                pass
        
        if existing_file_id:
            try:
                existing_file = FileItem.objects.get(id=existing_file_id, user=request.user)
                # Pre-fill form with existing file data
                form = FileUploadForm(initial={
                    'title': existing_file.title,
                    'description': existing_file.description,
                    'category': existing_file.category,
                    'is_public': existing_file.is_public
                })
            except FileItem.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'categories': FileCategory.objects.all(),
        'current_folder': current_folder,
        'folders': folders,
        'existing_file': existing_file,
    }
    
    return render(request, 'files/file_upload.html', context)

@login_required
def file_delete(request, file_id):
    """View to delete a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    # Check if file is already in trash
    permanent = request.GET.get('permanent') == '1' and file.is_in_trash()
    
    if request.method == 'POST':
        if permanent:
            # Capture file size before deletion
            file_size = file.file_size
            
            # Delete file
            file.delete()
            
            # Remove file size from user's storage
            profile = request.user.profile
            profile.storage_used = max(0, profile.storage_used - file_size)  # Prevent negative values
            profile.save()
            
            messages.success(request, "File permanently deleted!")
        else:
            # Move to trash
            file.soft_delete()
            messages.success(request, "File moved to trash!")
        
        # Check if redirecting to a folder
        folder_id = request.GET.get('folder')
        if folder_id:
            return redirect(reverse('files:file_list') + f'?folder={folder_id}')
        
        if request.GET.get('trash') == '1':
            return redirect(reverse('files:file_list') + '?trash=1')
            
        return redirect('files:file_list')
    
    context = {
        'file': file,
        'permanent': permanent,
    }
    
    return render(request, 'files/file_delete.html', context)

@login_required
def file_restore(request, file_id):
    """View to restore a file from trash"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user, deleted_at__isnull=False)
    
    if request.method == 'POST':
        file.restore()
        messages.success(request, "File restored from trash!")
        return redirect(reverse('files:file_list') + '?trash=1')
    
    context = {
        'file': file,
    }
    
    return render(request, 'files/file_restore.html', context)

@login_required
def empty_trash(request):
    """View to empty trash (permanently delete all files in trash)"""
    trash_files = FileItem.objects.filter(user=request.user, deleted_at__isnull=False)
    trash_count = trash_files.count()
    
    if request.method == 'POST':
        # Calculate total size to free up
        total_size = 0
        for file in trash_files:
            total_size += file.file_size
        
        # Delete all files in trash
        trash_files.delete()
        
        # Update user's storage used
        if total_size > 0:
            profile = request.user.profile
            profile.storage_used = max(0, profile.storage_used - total_size)
            profile.save()
        
        messages.success(request, f"Trash emptied! {trash_count} file{'s' if trash_count != 1 else ''} permanently deleted.")
        return redirect('files:file_list')
    
    context = {
        'trash_count': trash_count,
    }
    
    return render(request, 'files/empty_trash.html', context)

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
        form = ShareFileForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            access_level = form.cleaned_data['access_level']
            expires_in = form.cleaned_data['expires_in']
            custom_expiry_date = form.cleaned_data['custom_expiry_date']
            
            try:
                user_to_share_with = User.objects.get(username=username)
                
                # Don't allow sharing with self
                if user_to_share_with == request.user:
                    messages.error(request, "You cannot share a file with yourself.")
                    return redirect('files:file_detail', file_id=file.id)
                
                # Check if already shared
                share_instance = SharedFile.objects.filter(file=file, shared_with=user_to_share_with).first()
                
                # Set the expiry date based on selection
                expires_at = None
                if expires_in == 'custom':
                    expires_at = custom_expiry_date
                elif expires_in != 'never':
                    # Parse the time period (1d, 7d, 30d)
                    days = int(expires_in[:-1])
                    expires_at = timezone.now() + timezone.timedelta(days=days)
                
                if share_instance:
                    # Update existing share
                    share_instance.access_level = access_level
                    share_instance.expires_at = expires_at
                    share_instance.save()
                    messages.info(request, f"File share updated for {username}.")
                else:
                    # Create new share
                    SharedFile.objects.create(
                        file=file,
                        shared_by=request.user,
                        shared_with=user_to_share_with,
                        access_level=access_level,
                        expires_at=expires_at
                    )
                    messages.success(request, f"File shared with {username} successfully!")
                    
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' does not exist.")
            
            return redirect('files:file_detail', file_id=file.id)
    else:
        form = ShareFileForm()
    
    context = {
        'form': form,
        'file': file,
    }
    
    return render(request, 'files/file_share.html', context)

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
    # Get shared files excluding expired ones
    shared = SharedFile.objects.filter(shared_with=request.user).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )
    
    # Get count of expired shares for notification
    expired_count = SharedFile.objects.filter(
        shared_with=request.user,
        expires_at__isnull=False, 
        expires_at__lt=timezone.now()
    ).count()
    
    context = {
        'shared_files': shared,
        'expired_count': expired_count,
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
        form = ShareFolderForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            access_level = form.cleaned_data['access_level']
            expires_in = form.cleaned_data['expires_in']
            custom_expiry_date = form.cleaned_data['custom_expiry_date']
            
            try:
                user_to_share_with = User.objects.get(username=username)
                
                # Don't allow sharing with self
                if user_to_share_with == request.user:
                    messages.error(request, "You cannot share a folder with yourself.")
                    return redirect('files:file_list')
                
                # Check if already shared
                share_instance = SharedFolder.objects.filter(folder=folder, shared_with=user_to_share_with).first()
                
                # Set the expiry date based on selection
                expires_at = None
                if expires_in == 'custom':
                    expires_at = custom_expiry_date
                elif expires_in != 'never':
                    # Parse the time period (1d, 7d, 30d)
                    days = int(expires_in[:-1])
                    expires_at = timezone.now() + timezone.timedelta(days=days)
                
                if share_instance:
                    # Update existing share
                    share_instance.access_level = access_level
                    share_instance.expires_at = expires_at
                    share_instance.save()
                    messages.info(request, f"Folder share updated for {username}.")
                else:
                    # Create new share
                    SharedFolder.objects.create(
                        folder=folder,
                        shared_by=request.user,
                        shared_with=user_to_share_with,
                        access_level=access_level,
                        expires_at=expires_at
                    )
                    messages.success(request, f"Folder shared with {username} successfully!")
                    
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' does not exist.")
            
            return redirect('files:file_list')
    else:
        form = ShareFolderForm()
    
    context = {
        'form': form,
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

@login_required
def file_version_set_current(request, file_id, version_id):
    """Set a specific version as the current version"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    version = get_object_or_404(FileVersion, id=version_id, file=file)
    
    if request.method == 'POST':
        # Update all versions to not current
        file.versions.update(is_current=False)
        
        # Set this version as current
        version.is_current = True
        version.save()
        
        messages.success(request, f"Version {version.version_number} is now the current version.")
        return redirect('files:file_detail', file_id=file.id)
    
    context = {
        'file': file,
        'version': version,
    }
    
    return render(request, 'files/file_version_set_current.html', context)

@login_required
def file_version_download(request, file_id, version_id):
    """Download a specific version of a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    version = get_object_or_404(FileVersion, id=version_id, file=file)
    
    file_path = version.version_file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = f'attachment; filename="{file.title}_v{version.version_number}.{file.extension().lower()}"'
            return response
    
    messages.error(request, "File version not found.")
    return redirect('files:file_detail', file_id=file.id)

@login_required
def file_version_delete(request, file_id, version_id):
    """Delete a specific version of a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    version = get_object_or_404(FileVersion, id=version_id, file=file)
    
    # Don't allow deleting the only version
    if file.versions.count() <= 1:
        messages.error(request, "Cannot delete the only version of the file.")
        return redirect('files:file_detail', file_id=file.id)
    
    # Don't allow deleting the current version
    if version.is_current:
        messages.error(request, "Cannot delete the current version. Please set another version as current first.")
        return redirect('files:file_detail', file_id=file.id)
    
    if request.method == 'POST':
        # Capture version size before deletion
        version_size = version.version_size
        
        # Delete version
        version.delete()
        
        # Update user's storage used
        profile = request.user.profile
        profile.storage_used = max(0, profile.storage_used - version_size)
        profile.save()
        
        messages.success(request, f"Version {version.version_number} deleted successfully!")
        return redirect('files:file_detail', file_id=file.id)
    
    context = {
        'file': file,
        'version': version,
    }
    
    return render(request, 'files/file_version_delete.html', context)

# New views for collaboration features

@login_required
def file_comments(request, file_id):
    """View to show and add comments for a file"""
    file = get_object_or_404(FileItem, id=file_id)
    
    # Check if user has access to the file
    has_access = (
        file.user == request.user or 
        file.is_public or 
        SharedFile.objects.filter(file=file, shared_with=request.user).exists()
    )
    
    if not has_access:
        messages.error(request, "You don't have permission to view this file.")
        return redirect('files:file_list')
    
    # Get all root comments (no parent)
    comments = Comment.objects.filter(file=file, parent=None)
    
    # Handle new comment submission
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.file = file
            comment.user = request.user
            
            # Check if it's a reply to another comment
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id, file=file)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    pass
                
            comment.save()
            messages.success(request, "Comment added successfully!")
            return redirect('files:file_comments', file_id=file.id)
    else:
        form = CommentForm()
    
    context = {
        'file': file,
        'comments': comments,
        'form': form,
    }
    
    return render(request, 'files/file_comments.html', context)

@login_required
def delete_comment(request, comment_id):
    """Delete a comment"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Security check: only the comment author or the file owner can delete the comment
    if comment.user != request.user and comment.file.user != request.user:
        messages.error(request, "You don't have permission to delete this comment.")
        return redirect('files:file_comments', file_id=comment.file.id)
    
    if request.method == 'POST':
        file_id = comment.file.id
        comment.delete()
        messages.success(request, "Comment deleted successfully!")
        return redirect('files:file_comments', file_id=file_id)
    
    context = {
        'comment': comment,
    }
    
    return render(request, 'files/delete_comment.html', context)

@login_required
def edit_comment(request, comment_id):
    """Edit a comment"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Security check: only the comment author can edit the comment
    if comment.user != request.user:
        messages.error(request, "You don't have permission to edit this comment.")
        return redirect('files:file_comments', file_id=comment.file.id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Comment updated successfully!")
            return redirect('files:file_comments', file_id=comment.file.id)
    else:
        form = CommentForm(instance=comment)
    
    context = {
        'form': form,
        'comment': comment,
    }
    
    return render(request, 'files/edit_comment.html', context)

@login_required
def start_collaboration(request, file_id):
    file = get_object_or_404(FileItem, id=file_id)
    
    # Check if user has permission to edit this file
    if file.user != request.user and not SharedFile.objects.filter(
            file=file, shared_with=request.user, access_level__in=['edit']).exists():
        messages.error(request, "You don't have permission to collaborate on this file.")
        return redirect('files:file_detail', file_id=file_id)
    
    # Check if there's already an active session
    active_session = CollaborationSession.objects.filter(file=file, active=True).first()
    if active_session:
        return redirect('files:join_collaboration', session_id=active_session.id)
    
    if request.method == 'POST':
        # Create new session
        session = CollaborationSession()
        session.file = file
        session.started_by = request.user
        session.content = file.content if hasattr(file, 'content') else ""
        session.save()
        
        # Add creator as first participant
        CollaborationParticipant.objects.create(
            session=session,
            user=request.user,
            is_active=True
        )
        
        messages.success(request, "Collaboration session started successfully.")
        return redirect('files:join_collaboration', session_id=session.id)
    
    return render(request, 'files/start_collaboration.html', {
        'file': file
    })

@login_required
def join_collaboration(request, session_id):
    """Join an existing collaboration session"""
    session = get_object_or_404(CollaborationSession, id=session_id)
    
    # Check if the session is still active
    if not session.active:
        messages.error(request, "This collaboration session has ended.")
        return redirect('files:file_detail', file_id=session.file.id)
    
    # Check if user has access to the file
    file = session.file
    has_access = (
        file.user == request.user or 
        file.is_public or 
        SharedFile.objects.filter(file=file, shared_with=request.user).exists()
    )
    
    if not has_access:
        messages.error(request, "You don't have permission to join this collaboration session.")
        return redirect('files:file_list')
    
    # Add user as participant if not already
    participant, created = CollaborationParticipant.objects.get_or_create(
        session=session,
        user=request.user,
        defaults={'is_active': True}
    )
    
    if not participant.is_active:
        participant.is_active = True
        participant.save()
    
    # Get all active participants
    active_participants = CollaborationParticipant.objects.filter(
        session=session,
        is_active=True
    ).select_related('user')
    
    return render(request, 'files/collaboration_session.html', {
        'session': session,
        'file': file,
        'participants': active_participants,
        'current_user': request.user,
        'can_end': file.user == request.user or session.started_by == request.user
    })

@login_required
def end_collaboration(request, session_id):
    """End an active collaboration session"""
    session = get_object_or_404(CollaborationSession, id=session_id)
    
    # Security check: only the session creator or file owner can end the session
    if session.started_by != request.user and session.file.user != request.user:
        messages.error(request, "You don't have permission to end this collaboration session.")
        return redirect('files:join_collaboration', session_id=session.id)
    
    if request.method == 'POST':
        session.end_session()
        messages.success(request, "Collaboration session ended.")
        return redirect('files:file_detail', file_id=session.file.id)
    
    context = {
        'session': session,
    }
    
    return render(request, 'files/end_collaboration.html', context)

@login_required
def update_collaboration(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    # Check if request is AJAX by examining content type or accept headers
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    session = get_object_or_404(CollaborationSession, id=session_id, active=True)
    file = session.file
    
    # Check if user has permission to edit this file
    if file.user != request.user and not SharedFile.objects.filter(
            file=file, shared_with=request.user, access_level='edit').exists():
        return JsonResponse({
            'status': 'error',
            'message': "You don't have permission to edit this file."
        })
    
    try:
        # Handle both form data and JSON data
        if is_ajax and request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        if 'content' in data:
            session.content = data['content']
            session.save()
        
        if 'cursor_position' in data:
            participant, created = CollaborationParticipant.objects.get_or_create(
                session=session,
                user=request.user,
                defaults={'is_active': True}
            )
            
            # Update cursor position
            if isinstance(data['cursor_position'], dict):
                cursor_position = data['cursor_position']
            else:
                cursor_position = json.loads(data['cursor_position'])
                
            participant.cursor_position = cursor_position
            participant.last_active = timezone.now()
            participant.save()
        
        # Get updated participant info
        active_participants = CollaborationParticipant.objects.filter(
            session=session,
            is_active=True
        ).select_related('user')
        
        participants_data = []
        for p in active_participants:
            if p.user != request.user:  # Don't include current user
                participants_data.append({
                    'username': p.user.username,
                    'cursor_position': p.cursor_position,
                    'last_active': p.last_active.isoformat() if p.last_active else None
                })
        
        return JsonResponse({
            'status': 'success',
            'participants': participants_data
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def send_chat_message(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    # Check if request is AJAX by examining content type or accept headers
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    session = get_object_or_404(CollaborationSession, id=session_id, active=True)
    
    try:
        # Handle both form data and JSON data
        if is_ajax and request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'status': 'error', 'message': 'Message cannot be empty'})
        
        # In a real implementation, you would save this to a ChatMessage model
        # For now, we'll just echo it back for the frontend to handle
        
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': str(uuid.uuid4()),  # Generate a temporary ID
                'user': request.user.username,
                'content': message,
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def view_comments(request, file_id):
    file = get_object_or_404(FileItem, id=file_id)
    
    # Check if user has permission to view this file
    if file.user != request.user and not SharedFile.objects.filter(
            file=file, shared_with=request.user).exists():
        messages.error(request, "You don't have permission to view this file.")
        return redirect('files:dashboard')
    
    # Get top-level comments (no parent)
    comments = Comment.objects.filter(
        file=file,
        parent=None
    ).order_by('-created_at')
    
    # Form for adding new comments
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.file = file
            comment.user = request.user
            comment.save()
            messages.success(request, "Comment added successfully.")
            return redirect('files:view_comments', file_id=file_id)
    else:
        form = CommentForm()
    
    return render(request, 'files/comments.html', {
        'file': file,
        'comments': comments,
        'form': form
    })

@login_required
def add_reply(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)
    file = parent_comment.file
    
    # Check if user has permission to view this file
    if file.user != request.user and not SharedFile.objects.filter(
            file=file, shared_with=request.user).exists():
        messages.error(request, "You don't have permission to view this file.")
        return redirect('files:dashboard')
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.file = file
            reply.user = request.user
            reply.parent = parent_comment
            reply.save()
            messages.success(request, "Reply added successfully.")
    
    return redirect('files:view_comments', file_id=file.id)

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    file = comment.file
    
    # Check if user has permission to delete this comment
    if comment.user != request.user and file.user != request.user:
        messages.error(request, "You don't have permission to delete this comment.")
        return redirect('files:view_comments', file_id=file.id)
    
    if request.method == 'POST':
        comment.delete()
        messages.success(request, "Comment deleted successfully.")
    
    return redirect('files:view_comments', file_id=file.id)

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    file = comment.file
    
    # Check if user has permission to edit this comment
    if comment.user != request.user:
        messages.error(request, "You don't have permission to edit this comment.")
        return redirect('files:view_comments', file_id=file.id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Comment updated successfully.")
            return redirect('files:view_comments', file_id=file.id)
    else:
        form = CommentForm(instance=comment)
    
    return render(request, 'files/edit_comment.html', {
        'form': form,
        'comment': comment,
        'file': file
    })

@login_required
def file_unshare(request, file_id):
    """Remove sharing access for a file"""
    file = get_object_or_404(FileItem, id=file_id, user=request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        
        try:
            user_to_unshare_with = User.objects.get(username=username)
            
            # Check if file is shared with this user
            shared_file = SharedFile.objects.filter(file=file, shared_with=user_to_unshare_with)
            
            if shared_file.exists():
                shared_file.delete()
                messages.success(request, f"File access for {username} has been removed.")
            else:
                messages.info(request, f"File is not shared with {username}.")
                
        except User.DoesNotExist:
            messages.error(request, f"User '{username}' does not exist.")
        
        return redirect('files:file_share', file_id=file.id)
    
    # Get all users this file is shared with
    shared_with = SharedFile.objects.filter(file=file)
    
    context = {
        'file': file,
        'shared_with': shared_with,
    }
    
    return render(request, 'files/file_unshare.html', context)

# Audit Log Views
@login_required
def audit_logs(request):
    """View to display audit logs for admins and users"""
    # Regular users can only see their own logs
    if not request.user.is_staff:
        logs = AuditLog.objects.filter(user=request.user)
    else:
        logs = AuditLog.objects.all()
    
    # Filtering
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    date_from = request.GET.get('date_from')
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    
    success_filter = request.GET.get('success')
    if success_filter in ['true', 'false']:
        logs = logs.filter(success=(success_filter == 'true'))
    
    object_type_filter = request.GET.get('object_type')
    if object_type_filter:
        logs = logs.filter(object_type=object_type_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 25)  # Show 25 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique object types for filter dropdown
    object_types = AuditLog.objects.values_list('object_type', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'action_types': dict(AuditLog.ACTION_TYPES),
        'object_types': object_types,
        'filters': {
            'action': action_filter,
            'user': user_filter,
            'date_from': date_from,
            'date_to': date_to,
            'success': success_filter,
            'object_type': object_type_filter,
        }
    }
    
    return render(request, 'files/audit_logs.html', context)

@login_required
def audit_log_detail(request, log_id):
    """View to show details of a specific audit log entry"""
    # Regular users can only see their own logs
    if request.user.is_staff:
        log = get_object_or_404(AuditLog, id=log_id)
    else:
        log = get_object_or_404(AuditLog, id=log_id, user=request.user)
    
    context = {
        'log': log,
    }
    
    return render(request, 'files/audit_log_detail.html', context)

@login_required
def export_audit_logs(request):
    """Export audit logs to CSV for admins"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to export audit logs.")
        return redirect('files:audit_logs')
    
    import csv
    from django.http import HttpResponse
    
    # Filtering (same as audit_logs view)
    logs = AuditLog.objects.all()
    
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    date_from = request.GET.get('date_from')
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    
    success_filter = request.GET.get('success')
    if success_filter in ['true', 'false']:
        logs = logs.filter(success=(success_filter == 'true'))
    
    object_type_filter = request.GET.get('object_type')
    if object_type_filter:
        logs = logs.filter(object_type=object_type_filter)
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Action', 'Object Type', 'Object ID', 'IP Address', 'Success'])
    
    # Add data rows
    for log in logs:
        writer.writerow([
            log.timestamp,
            log.user.username if log.user else 'Anonymous',
            log.get_action_display(),
            log.object_type or '-',
            log.object_id or '-',
            log.ip_address or '-',
            'Yes' if log.success else 'No'
        ])
    
    return response

# Bulk Operations Views

@login_required
def bulk_action(request):
    """Handle bulk operations on files"""
    if request.method != 'POST':
        return redirect('files:file_list')
    
    # Get the selected files from the form
    file_ids = request.POST.getlist('selected_files')
    action = request.POST.get('bulk_action')
    
    if not file_ids:
        messages.warning(request, "No files selected for the bulk action.")
        return redirect('files:file_list')
    
    # Convert file_ids to a list of integers for task processing
    file_ids = [int(fid) for fid in file_ids if fid.isdigit()]
    
    # Get current folder for redirect later
    current_folder_id = request.POST.get('current_folder')
    
    # Process the bulk action
    if action == 'delete':
        from .tasks import bulk_delete_files
        # Run the task asynchronously
        task = bulk_delete_files.delay(file_ids, request.user.id)
        messages.success(request, f"Delete operation started for {len(file_ids)} file(s). This may take a moment.")
    
    elif action == 'download':
        from .tasks import bulk_download_files
        # Run the task asynchronously
        task = bulk_download_files.delay(file_ids, request.user.id)
        messages.success(request, f"Preparing download for {len(file_ids)} file(s). You'll be notified when it's ready.")
    
    elif action == 'move':
        destination_folder_id = request.POST.get('destination_folder')
        if not destination_folder_id:
            messages.error(request, "Please select a destination folder.")
            return redirect('files:file_list')
        
        from .tasks import bulk_move_files
        # Run the task asynchronously
        task = bulk_move_files.delay(file_ids, destination_folder_id, request.user.id)
        messages.success(request, f"Move operation started for {len(file_ids)} file(s). This may take a moment.")
    
    # Store the task_id in the session for status checking
    if not request.session.get('bulk_tasks'):
        request.session['bulk_tasks'] = {}
    
    request.session['bulk_tasks'][action] = {
        'task_id': task.id,
        'status': 'PENDING',
        'total_files': len(file_ids),
        'started_at': timezone.now().isoformat()
    }
    request.session.modified = True
    
    # Redirect back to the appropriate folder
    if current_folder_id:
        return redirect('files:folder_contents', folder_id=current_folder_id)
    return redirect('files:file_list')

@login_required
def bulk_task_status(request, task_id):
    """Check the status of a bulk operation task"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    
    if result.ready():
        try:
            task_result = result.get()
            if task_result.get('status') == 'success':
                data = {
                    'status': 'SUCCESS',
                    'result': task_result
                }
                
                # Special handling for bulk download
                if 'zip_path' in task_result:
                    # Set up a session variable to track the download
                    request.session['bulk_download'] = {
                        'path': task_result['zip_path'],
                        'temp_dir': task_result['temp_dir'],
                        'filename': task_result['filename'],
                        'created_at': timezone.now().isoformat()
                    }
                    request.session.modified = True
                    
                    # Add download URL to response
                    data['download_url'] = reverse('files:bulk_download_get', kwargs={'filename': task_result['filename']})
            else:
                data = {
                    'status': 'FAILURE',
                    'error': task_result.get('message', 'Unknown error')
                }
        except Exception as e:
            data = {
                'status': 'FAILURE',
                'error': str(e)
            }
    else:
        data = {
            'status': result.state,
            'info': {
                'current': 0,
                'total': 1,
                'percent': 0
            }
        }
    
    return JsonResponse(data)

@login_required
def bulk_download_get(request, filename):
    """Serve the bulk download ZIP file"""
    download_info = request.session.get('bulk_download')
    
    if not download_info or not filename or filename != download_info.get('filename'):
        messages.error(request, "Download not found or expired.")
        return redirect('files:file_list')
    
    # Send the file as a response
    file_path = download_info['path']
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Clean up the temp directory after sending the file
            temp_dir = download_info.get('temp_dir')
            if temp_dir and os.path.exists(temp_dir):
                # Schedule cleanup for after the response is sent
                import threading
                def cleanup_temp():
                    import time
                    # Wait a bit to ensure the file is fully sent
                    time.sleep(5)
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception:
                        pass
                
                # Start cleanup thread
                threading.Thread(target=cleanup_temp).start()
            
            # Clear the session variable
            del request.session['bulk_download']
            request.session.modified = True
            
            return response
    
    messages.error(request, "Download file not found.")
    return redirect('files:file_list')

@login_required
def get_folders_for_move(request):
    """Get a list of folders for the bulk move operation"""
    folders = Folder.objects.filter(user=request.user).values('id', 'name', 'parent')
    
    # Organize folders in a hierarchical structure
    def build_folder_tree(folders, parent=None):
        result = []
        for folder in folders:
            if folder['parent'] == parent:
                children = build_folder_tree(folders, folder['id'])
                if children:
                    folder['children'] = children
                result.append(folder)
        return result
    
    folder_tree = build_folder_tree(list(folders))
    
    return JsonResponse({
        'folders': folder_tree
    })

@login_required
def bulk_upload_form(request):
    """Show the multi-file upload form"""
    folders = Folder.objects.filter(user=request.user)
    
    # Get current folder if specified
    current_folder = None
    folder_id = request.GET.get('folder')
    if folder_id:
        try:
            current_folder = Folder.objects.get(id=folder_id, user=request.user)
        except Folder.DoesNotExist:
            pass
    
    # Get categories for the form
    categories = FileCategory.objects.all()
    
    context = {
        'folders': folders,
        'current_folder': current_folder,
        'categories': categories,
    }
    
    return render(request, 'files/bulk_upload.html', context)

@login_required
def process_bulk_upload(request):
    """Process multiple file uploads"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
    
    try:
        files = request.FILES.getlist('files[]')
        category_id = request.POST.get('category')
        folder_id = request.POST.get('folder')
        is_public = request.POST.get('is_public') == 'on'
        
        if not files:
            return JsonResponse({'status': 'error', 'message': 'No files provided'})
        
        # Get the total size of all files
        total_size = sum(f.size for f in files)
        
        # Check if user has enough storage
        profile = request.user.profile
        if not profile.has_storage_available(total_size):
            return JsonResponse({
                'status': 'error',
                'message': f"Not enough storage space. Available: {profile.get_available_storage_readable()}, Required: {FileItem.get_readable_size(total_size)}"
            })
        
        # Get category and folder
        category = None
        folder = None
        
        if category_id:
            try:
                category = FileCategory.objects.get(id=category_id)
            except FileCategory.DoesNotExist:
                pass
        
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, user=request.user)
            except Folder.DoesNotExist:
                pass
        
        # Process each file
        results = []
        for uploaded_file in files:
            try:
                # Create the file record
                file_item = FileItem(
                    user=request.user,
                    title=os.path.splitext(uploaded_file.name)[0],
                    file=uploaded_file,
                    file_size=uploaded_file.size,
                    category=category,
                    folder=folder,
                    is_public=is_public
                )
                file_item.save()
                
                # Create the initial version
                FileVersion.create_version(
                    file_item=file_item,
                    version_file=uploaded_file,
                    user=request.user
                )
                
                # Update user's storage used
                profile.storage_used += file_item.file_size
                
                # Log the upload
                AuditLog.log(
                    action='upload',
                    user=request.user,
                    obj=file_item,
                    details={'bulk_operation': True},
                    success=True
                )
                
                results.append({
                    'name': uploaded_file.name,
                    'size': file_item.get_readable_file_size(),
                    'status': 'success',
                    'id': file_item.id
                })
            except Exception as e:
                results.append({
                    'name': uploaded_file.name,
                    'size': FileItem.get_readable_size(uploaded_file.size),
                    'status': 'error',
                    'error': str(e)
                })
        
        # Save the profile after all uploads
        profile.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully uploaded {len(results)} files',
            'results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error processing uploads: {str(e)}'
        })
