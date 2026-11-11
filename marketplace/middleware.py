from django.core.cache import cache
from django.utils import timezone


class ActiveUserMiddleware:
    """
    Tracks active online visitors (both authenticated users and guests)
    using Django's fast in-memory/database cache backend without slowing down SQL.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Determine unique identifier (User ID if logged in, otherwise Session Key or IP)
        if request.user.is_authenticated:
            visitor_id = f"online_user_{request.user.id}"
        elif request.session.session_key:
            visitor_id = f"online_guest_{request.session.session_key}"
        else:
            # Fallback to remote IP if no session exists yet
            ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR')
            visitor_id = f"online_ip_{ip}"

        # 2. Store timestamp in cache with a 5-minute (300 seconds) sliding window
        cache.set(visitor_id, timezone.now().timestamp(), timeout=300)

        # 3. Keep an index of active keys in cache
        active_keys = cache.get('active_visitor_keys', set())
        if not isinstance(active_keys, set):
            active_keys = set()

        active_keys.add(visitor_id)
        cache.set('active_visitor_keys', active_keys, timeout=600)

        response = self.get_response(request)
        return response