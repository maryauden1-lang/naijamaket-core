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

LIVE_PULSE_SCRIPT_TAG = (
    b'\n<script src="/static/js/live_pulse.js?v=2" defer></script>'
    b'\n<script src="/static/js/help_center.js?v=1" defer></script>\n</body>'
)


def is_bot_request(request):
    """Detects search engine crawlers, uptime monitors, and automated scripts."""
    ua = (request.META.get('HTTP_USER_AGENT') or '').strip().lower()
    if not ua or len(ua) < 15:
        return True
    if not request.META.get('HTTP_ACCEPT_LANGUAGE'):
        return True
    return any(keyword in ua for keyword in BOT_USER_AGENT_KEYWORDS)


def _inject_live_pulse_script(request, response):
    """Automatically attaches live_pulse.js and help_center.js to every HTML page."""
    if request.path.startswith('/portal-management-99/'):
        return response
    if getattr(response, 'streaming', False):
        return response

    content_type = response.get('Content-Type', '')
    if 'text/html' not in content_type:
        return response

    if b'help_center.js' in response.content or b'</body>' not in response.content:
        return response

    response.content = response.content.replace(b'</body>', LIVE_PULSE_SCRIPT_TAG, 1)
    if response.has_header('Content-Length'):
        response['Content-Length'] = len(response.content)
    return response


class ActiveUserMiddleware:
    """
    1. Counts ONLY verified real human devices (with verified session cookie & browser headers).
    2. Injects global Live-Pulse & Help Center scripts into every HTML page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Skip static assets, media, admin portal polling, background APIs, and icons
        if (
            request.path.startswith('/static/')
            or request.path.startswith('/media/')
            or request.path.startswith('/portal-management-99/')
            or request.path in ('/api/live-pulse/', '/api/support-chat/')
            or request.path == '/favicon.ico'
        ):
            return self.get_response(request)

        # 2. Skip bots, crawlers, uptime monitors, and headerless scripts
        if is_bot_request(request):
            return self.get_response(request)

        # 3. Skip staff/superuser accounts so your own admin activity doesn't count as customer traffic
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            response = self.get_response(request)
            return _inject_live_pulse_script(request, response)

        # 4. Require an existing session cookie before counting guests
        has_existing_session = bool(request.session.session_key)
        if not has_existing_session:
            request.session.save()
            response = self.get_response(request)
            return _inject_live_pulse_script(request, response)

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
        return _inject_live_pulse_script(request, response)