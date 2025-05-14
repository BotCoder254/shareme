import uuid
from django.utils import timezone
from .models import FileVersion

def create_file_version(file, content, user, reason=None):
    """
    Create a new version of a file
    
    Args:
        file: The FileItem instance to create a version for
        content: The content of the file version
        user: The user creating the version
        reason: Optional reason for the version (e.g., "Collaboration update")
    
    Returns:
        The created FileVersion instance
    """
    # Create the new version
    version = FileVersion.objects.create(
        file=file,
        content=content,
        version_number=get_next_version_number(file),
        created_by=user,
        reason=reason or "File update"
    )
    
    # Update the file's content
    file.content = content
    file.modified_at = timezone.now()
    file.modified_by = user
    file.save()
    
    return version

def get_next_version_number(file):
    """
    Get the next version number for a file
    
    Args:
        file: The FileItem instance
    
    Returns:
        The next version number as an integer
    """
    # Get the latest version number
    latest_version = FileVersion.objects.filter(file=file).order_by('-version_number').first()
    
    if latest_version:
        return latest_version.version_number + 1
    else:
        return 1

def generate_unique_id():
    """
    Generate a unique UUID for use in models
    
    Returns:
        A UUID string
    """
    return str(uuid.uuid4())

def get_file_extension(filename):
    """
    Get the extension of a file
    
    Args:
        filename: The name of the file
    
    Returns:
        The file extension without the dot
    """
    if '.' in filename:
        return filename.split('.')[-1].lower()
    return ''

def is_text_file(filename):
    """
    Check if a file is a text file based on its extension
    
    Args:
        filename: The name of the file
    
    Returns:
        Boolean indicating if the file is a text file
    """
    text_extensions = [
        'txt', 'html', 'htm', 'css', 'js', 'json', 'md', 'py', 'xml',
        'csv', 'log', 'sql', 'yaml', 'yml', 'ini', 'cfg', 'conf'
    ]
    
    extension = get_file_extension(filename)
    return extension in text_extensions 