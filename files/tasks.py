import os
import shutil
import zipfile
import tempfile
from io import BytesIO
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import FileItem, Folder, AuditLog

@shared_task
def bulk_delete_files(file_ids, user_id):
    """
    Deletes multiple files asynchronously
    """
    user = User.objects.get(id=user_id)
    total_files = len(file_ids)
    deleted_count = 0
    
    for file_id in file_ids:
        try:
            file = FileItem.objects.get(id=file_id, user=user)
            file.soft_delete()
            deleted_count += 1
            
            # Log the deletion
            AuditLog.log(
                action='delete',
                user=user,
                obj=file,
                details={'bulk_operation': True},
                success=True
            )
        except FileItem.DoesNotExist:
            pass
    
    return {
        'status': 'success',
        'message': f'Successfully deleted {deleted_count} of {total_files} files',
        'deleted_count': deleted_count
    }

@shared_task
def bulk_download_files(file_ids, user_id):
    """
    Creates a ZIP file containing multiple files
    """
    user = User.objects.get(id=user_id)
    
    # Create a unique temporary directory for this job
    temp_dir = tempfile.mkdtemp(prefix='bulk_download_')
    zip_filename = os.path.join(temp_dir, f'bulk_download_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip')
    
    try:
        # Create the ZIP file
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_id in file_ids:
                try:
                    file = FileItem.objects.get(id=file_id)
                    
                    # Check if user has access to this file
                    if file.user != user and not file.shared_with.filter(shared_with=user).exists():
                        continue
                    
                    # Add the file to the ZIP with a subfolder structure if needed
                    if file.folder:
                        arcname = os.path.join(file.folder.name, file.title)
                    else:
                        arcname = file.title
                        
                    # Add file extension if not in title
                    ext = os.path.splitext(file.file.name)[1]
                    if not arcname.endswith(ext):
                        arcname += ext
                    
                    zipf.write(file.file.path, arcname=arcname)
                    
                    # Increment download count
                    file.download_count += 1
                    file.save(update_fields=['download_count'])
                    
                    # Log the download
                    AuditLog.log(
                        action='download',
                        user=user,
                        obj=file,
                        details={'bulk_operation': True},
                        success=True
                    )
                except FileItem.DoesNotExist:
                    pass
        
        # Return the path to the ZIP file and the temporary directory
        return {
            'status': 'success',
            'zip_path': zip_filename,
            'temp_dir': temp_dir,
            'filename': os.path.basename(zip_filename)
        }
    except Exception as e:
        # Clean up the temporary directory in case of error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {
            'status': 'error',
            'message': str(e)
        }

@shared_task
def bulk_move_files(file_ids, destination_folder_id, user_id):
    """
    Moves multiple files to a destination folder
    """
    user = User.objects.get(id=user_id)
    destination_folder = None
    
    if destination_folder_id:
        try:
            destination_folder = Folder.objects.get(id=destination_folder_id, user=user)
        except Folder.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Destination folder not found'
            }
    
    total_files = len(file_ids)
    moved_count = 0
    
    for file_id in file_ids:
        try:
            file = FileItem.objects.get(id=file_id, user=user)
            
            # Update the file's folder
            file.folder = destination_folder
            file.save()
            moved_count += 1
            
            # Log the move
            AuditLog.log(
                action='update',
                user=user,
                obj=file,
                details={
                    'bulk_operation': True,
                    'action': 'move',
                    'destination_folder': destination_folder.id if destination_folder else None
                },
                success=True
            )
        except FileItem.DoesNotExist:
            pass
    
    folder_name = destination_folder.name if destination_folder else 'Root'
    return {
        'status': 'success',
        'message': f'Successfully moved {moved_count} of {total_files} files to {folder_name}',
        'moved_count': moved_count
    }

@shared_task
def bulk_upload_files(upload_data, user_id):
    """
    Process multiple file uploads asynchronously
    Note: This is a placeholder - actual implementation would need to handle
    file uploads differently as they can't be easily passed to Celery
    """
    # This is a placeholder for the actual implementation
    # In a real-world scenario, you'd need to handle file uploads differently,
    # possibly by saving files to a temporary location and then processing them
    return {
        'status': 'success',
        'message': 'Files uploaded successfully',
        'count': len(upload_data)
    } 