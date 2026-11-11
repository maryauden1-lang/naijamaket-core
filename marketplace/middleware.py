import time
from django.core.cache import cache


class ActiveUserMiddleware:
    """
    Counts every device individually by assigning each browser an isolated session.
    Works seamlessly across shared Wi-Fi, routers, and mobile proxies.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Skip static assets, media, and background icon queries
        if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path == '/favicon.ico':
            return self.get_response(request)

        # 2. Force session creation so every unique phone/browser has a distinct token
        if not request.session.session_key:
            request.session.save()

        # 3. Use the unique session key (or User ID if logged in)
        if request.user.is_authenticated:
            device_id = f"user_{request.user.id}"
        else:
            device_id = f"guest_{request.session.session_key}"

        now = time.time()

        # 4. Read active devices dictionary from the shared database cache
        active_registry = cache.get('active_visitor_registry') or {}

        # 5. Record/refresh this device's timestamp
        active_registry[device_id] = now

        # 6. Prune any device that hasn't made a request in the last 5 minutes (300s)
        cutoff = now - 300
        pruned_registry = {d_id: ts for d_id, ts in active_registry.items() if ts > cutoff}

        # 7. Write back to cache
        cache.set('active_visitor_registry', pruned_registry, timeout=600)

        response = self.get_response(request)
        return response