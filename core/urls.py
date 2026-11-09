from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

# Sitemaps configuration
from marketplace.sitemaps import StaticViewSitemap, ListingSitemap, StaticPageSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'listings': ListingSitemap,
    'pages': StaticPageSitemap,
}


def robots_txt(request):
    """Directs search engines to crawl public items while protecting private app areas."""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /workspace/",
        "Disallow: /api/",
        "Disallow: /chat/",
        "Disallow: /dashboard/",
        "Disallow: /saved/",
        "Disallow: /favorite/",
        "Disallow: /report/",
        "Disallow: /password-reset/",
        "Allow: /",
        "",
        "Sitemap: https://naijasale.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def admin_access_guard(request):
    """
    Guards /admin/:
    - If superuser -> allow into standard Django admin
    - If staff (moderator/support) -> redirect straight to /workspace/
    - Otherwise -> standard admin login
    """
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return admin.site.index(request)
        elif request.user.is_staff:
            return redirect('workspace:dashboard')
    return admin.site.login(request, extra_context={'next': '/workspace/'})


urlpatterns = [
    # Guarded root admin entry
    path('admin/', admin_access_guard, name='admin_guard'),
    # Full Django admin sub-routes
    path('admin/', admin.site.urls),
    # Staff workspace portal
    path('workspace/', include('marketplace.workspace_urls')),
    # Search Engine Crawlers & Indexing
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    # Public marketplace routes
    path('', include('marketplace.urls')),
]

# Ensure uploaded media serves properly
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)