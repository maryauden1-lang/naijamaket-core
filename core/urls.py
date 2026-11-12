"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap

# Sitemaps configuration
try:
    from marketplace.sitemaps import ListingSitemap, StaticViewSitemap
    sitemaps = {
        'listings': ListingSitemap,
        'static': StaticViewSitemap,
    }
except ImportError:
    sitemaps = {}

urlpatterns = [
    # Custom secured CEO Admin Suite
    path('portal-management-99/', admin.site.urls),

    # XML Sitemap for SEO & Search Console
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # Dedicated Staff & Moderation Workspace
    path('workspace/', include('marketplace.workspace_urls', namespace='workspace')),

    # Marketplace core application
    path('', include('marketplace.urls', namespace='marketplace')),
]

# Serve local media & static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)