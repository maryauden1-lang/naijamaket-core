from .models import SystemNotification


def unread_notifications(request):
    if request.user.is_authenticated:
        qs = SystemNotification.objects.filter(recipient=request.user)
        return {
            'system_notifications': qs[:10],
            'unread_notif_count': qs.filter(is_read=False).count(),
        }
    return {
        'system_notifications': [],
        'unread_notif_count': 0,
    }