from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog
import re
import json

class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to automatically log sensitive actions"""
    
    # List of URL patterns to log
    SENSITIVE_URLS = [
        # Admin actions
        r'^/admin/',
        # Authentication actions
        r'^/accounts/login/',
        r'^/accounts/logout/',
        # File operations
        r'^/files/[0-9]+/delete/',
        r'^/files/[0-9]+/share/',
        r'^/files/[0-9]+/unshare/',
        r'^/files/[0-9]+/download/',
        # Folder operations
        r'^/folder/[0-9]+/delete/',
        r'^/folder/[0-9]+/share/',
        r'^/folder/[0-9]+/unshare/',
        # Collaboration
        r'^/collaboration/',
        # Share links
        r'^/share-links/delete/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile regex patterns
        self.sensitive_patterns = [re.compile(pattern) for pattern in self.SENSITIVE_URLS]
    
    def __call__(self, request):
        # Check if the URL should be logged
        should_log = False
        for pattern in self.sensitive_patterns:
            if pattern.match(request.path):
                should_log = True
                break
        
        # Process request
        response = self.get_response(request)
        
        # Log sensitive actions
        if should_log:
            # Determine action type
            action = self._determine_action_type(request)
            
            # Format request data
            try:
                if request.method == 'POST':
                    if 'password' in request.POST:
                        # Don't log password data
                        post_data = request.POST.copy()
                        post_data['password'] = '********'
                        details = {
                            'method': request.method,
                            'path': request.path,
                            'data': dict(post_data)
                        }
                    else:
                        details = {
                            'method': request.method,
                            'path': request.path,
                            'data': dict(request.POST)
                        }
                else:
                    details = {
                        'method': request.method,
                        'path': request.path,
                    }
                    
                # Add response status
                details['status_code'] = response.status_code
                
                # Log the action
                success = 200 <= response.status_code < 400
                AuditLog.log(
                    action=action,
                    user=request.user if request.user.is_authenticated else None,
                    request=request,
                    details=details,
                    success=success
                )
            except Exception as e:
                # Never break functionality because of logging
                print(f"Error in audit logging middleware: {str(e)}")
        
        return response
    
    def _determine_action_type(self, request):
        """Determine the type of action based on the URL and method"""
        path = request.path
        method = request.method
        
        # Login/logout
        if '/accounts/login/' in path:
            return 'login'
        elif '/accounts/logout/' in path:
            return 'logout'
        # Admin actions
        elif '/admin/' in path:
            return 'admin'
        # File operations
        elif '/delete/' in path:
            return 'delete'
        elif '/share/' in path and 'unshare' not in path:
            return 'share'
        elif '/unshare/' in path:
            return 'unshare'
        elif '/download/' in path:
            return 'download'
        elif '/upload/' in path:
            return 'upload'
        # Collaboration
        elif '/collaboration/' in path:
            return 'collaborate'
        # Default
        else:
            if method == 'POST':
                return 'update'
            elif method == 'GET':
                return 'security'
            else:
                return 'security' 