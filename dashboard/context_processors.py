from django.utils import timezone
from .models import Notification

def dashboard_context(request):
    """Add dashboard context to all templates."""
    if request.user.is_authenticated:
        return {
            'unread_notifications_count': Notification.get_unread_count(request.user),
            'current_year': timezone.now().year,
            'dashboard_refresh_interval': 300,  # 5 minutes
        }
    return {}