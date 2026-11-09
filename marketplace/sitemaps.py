from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Listing, StaticPage


class StaticViewSitemap(Sitemap):
    """Indexes core public discovery and action pages."""
    priority = 1.0
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return [
            'marketplace:home',
            'marketplace:login',
            'marketplace:register',
            'marketplace:post_ad',
        ]

    def location(self, item):
        return reverse(item)


class ListingSitemap(Sitemap):
    """Indexes all active, approved marketplace listings."""
    priority = 0.9
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return Listing.objects.filter(status='active').order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at

    def location(self, obj):
        return reverse('marketplace:listing_detail', kwargs={'slug': obj.slug})


class StaticPageSitemap(Sitemap):
    """Indexes custom CMS pages (Terms, Privacy, Safety Tips, etc.)."""
    priority = 0.5
    changefreq = 'monthly'
    protocol = 'https'

    def items(self):
        return StaticPage.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('marketplace:static_page', kwargs={'slug': obj.slug})