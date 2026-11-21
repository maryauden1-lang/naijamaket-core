import time
from django.core.cache import cache


BOT_USER_AGENT_KEYWORDS = (
    'bot', 'crawl', 'spider', 'slurp', 'mediapartners', 'adsbot',
    'bingpreview', 'facebookexternalhit', 'twitterbot', 'whatsapp',
    'telegrambot', 'linkedinbot', 'python-requests', 'urllib', 'curl',
    'wget', 'httpclient', 'scrapy', 'headless', 'phantomjs', 'selenium',
    'playwright', 'puppeteer', 'uptime', 'pingdom', 'statuscake', 'monitor',
    'ahrefs', 'semrush', 'mj12bot', 'dotbot', 'yandex', 'baidu', 'duckduckbot',
    'go-http-client', 'axios', 'node-fetch', 'java/', 'okhttp', 'zgrab', 'censys'
)


def is_bot_request(request):
    """Detects search engine crawlers, uptime monitors, and automated scripts."""
    ua = (request.META.get('HTTP_USER_AGENT') or '').strip().lower()
    if not ua or len(ua) < 15:
        return True
    if not request.META.get('HTTP_ACCEPT_LANGUAGE'):
        return True
    return any(keyword in ua for keyword in BOT_USER_AGENT_KEYWORDS)


class ActiveUserMiddleware:
    """
    Counts ONLY verified real human devices:
    - Excludes bots, crawlers, uptime monitors, and requests without browser language headers.
    - Requires a verified browser session cookie so cookie-less scrapers cannot inflate guest counts.
    - Excludes staff/superuser accounts and admin portal polling.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Skip static assets, media, admin portal polling, and background icon queries
        if (
            request.path.startswith('/static/')
            or request.path.startswith('/media/')
            or request.path.startswith('/portal-management-99/')
            or request.path == '/favicon.ico'
        ):
            return self.get_response(request)

        # 2. Skip bots, crawlers, uptime monitors, and headerless scripts
        if is_bot_request(request):
            return self.get_response(request)

        # 3. Skip staff/superuser accounts so your own admin activity doesn't count as customer traffic
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return self.get_response(request)

        # 4. Require an existing session cookie before counting guests:
        # First-time visitors get a session cookie assigned; real browsers send it back on subsequent
        # requests/polls, whereas cookie-less scanners never get counted.
        has_existing_session = bool(request.session.session_key)
        if not has_existing_session:
            request.session.save()
            return self.get_response(request)

        # 5. Use the verified session key (or User ID if logged in)
        if request.user.is_authenticated:
            device_id = f"user_{request.user.id}"
        else:
            device_id = f"guest_{request.session.session_key}"

        now = time.time()

        # 6. Read active devices dictionary from the shared database cache
        active_registry = cache.get('active_visitor_registry') or {}

        # 7. Record/refresh this verified human device's timestamp
        active_registry[device_id] = now

        # 8. Prune any device that hasn't made a request in the last 5 minutes (300s)
        cutoff = now - 300
        pruned_registry = {d_id: ts for d_id, ts in active_registry.items() if ts > cutoff}

        # 9. Write back to cache
        cache.set('active_visitor_registry', pruned_registry, timeout=600)

        response = self.get_response(request)
        return response