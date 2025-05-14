from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Notification

@login_required
def notification_list(request):
    """View to list all notifications of the user"""
    notifications = Notification.objects.filter(recipient=request.user)
    unread_count = notifications.filter(read=False).count()
    
    # Mark all as read if requested
    if request.GET.get('mark_all_read'):
        notifications.filter(read=False).update(read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications:list')
    
    # Return JSON if requested (for AJAX)
    if request.GET.get('format') == 'json':
        notification_data = [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'notification_type': n.notification_type,
            'read': n.read,
            'created_at': n.created_at.isoformat(),
            'sender': n.sender.username if n.sender else None,
            'link': n.link
        } for n in notifications[:10]]  # Limit to 10 most recent
        
        return JsonResponse({
            'notifications': notification_data,
            'unread_count': unread_count,
            'total_count': notifications.count()
        })
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications/notification_list.html', context)

@login_required
def notification_detail(request, notification_id):
    """View to show a specific notification and mark it as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    # Mark as read if unread
    if not notification.read:
        notification.mark_as_read()
    
    # Redirect to link if available
    if notification.link:
        return redirect(notification.link)
    
    # Otherwise show notification details
    context = {
        'notification': notification,
    }
    
    return render(request, 'notifications/notification_detail.html', context)

@login_required
@require_POST
def mark_as_read(request, notification_id):
    """AJAX view to mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_count(request):
    """AJAX view to get unread notification count"""
    count = Notification.objects.filter(recipient=request.user, read=False).count()
    return JsonResponse({'count': count})

@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a notification"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    messages.success(request, "Notification deleted successfully.")
    
    # Return JSON response if AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:list')
