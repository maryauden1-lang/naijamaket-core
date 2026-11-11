import os
from pathlib import Path
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.urls import path
from django.conf import settings
from django.db import connection
from django.db.models import Count, Sum
from django.utils import timezone
from django.core.management import call_command
from django.core.cache import cache

# Optional import for AXES logs
try:
    from axes.models import AccessAttempt, AccessLog, AccessFailureLog
except ImportError:
    AccessAttempt = None
    AccessLog = None
    AccessFailureLog = None

from .models import (
    SiteSetting,
    StaticPage,
    FAQ,
    State,
    Area,
    Category,
    SubCategory,
    SellerProfile,
    SellerReview,
    Listing,
    ListingImage,
    Favorite,
    Conversation,
    Message,
    ReportedListing,
    StaffProfile,
    StaffActivityLog,
)


# ==============================================================================
# HOOK CUSTOM CEO DASHBOARD CONTEXT INTO DJANGO ADMIN
# ==============================================================================
_original_admin_index = admin.site.index


def custom_admin_index(request, extra_context=None):
    extra_context = extra_context or {}

    # 1. Top Row Metrics
    total_groups = Group.objects.count()
    total_users = User.objects.count()

    total_axes_attempts = AccessAttempt.objects.count() if AccessAttempt else 0
    total_axes_failures = AccessFailureLog.objects.count() if AccessFailureLog else 0
    total_axes_logs = AccessLog.objects.count() if AccessLog else 0

    # 2. Marketplace Metrics & Moderation Queues
    total_listings = Listing.objects.count()
    pending_listings_count = Listing.objects.filter(status='pending').count()
    pending_kyc_count = SellerProfile.objects.filter(verification_status='pending').count()
    unresolved_reports_count = ReportedListing.objects.filter(is_resolved=False).count()

    # Total combined pending actions for CEO alerts
    total_notifications = pending_listings_count + pending_kyc_count + unresolved_reports_count

    total_conversations = Conversation.objects.count()
    total_favorites = Favorite.objects.count()
    total_views = Listing.objects.aggregate(total=Sum('views_count'))['total'] or 0

    total_areas = Area.objects.count()
    total_categories = Category.objects.count()
    total_pages = StaticPage.objects.count()

    # 3. Recent Registered Users (Latest 5)
    recent_users = User.objects.select_related('seller_profile').order_by('-date_joined')[:5]

    # 4. Top Categories with listing counts
    top_categories = Category.objects.annotate(
        listing_count=Count('listings')
    ).order_by('-listing_count')[:4]

    # 5. Real-Time Online Visitors (last 5 minutes)
    active_keys = cache.get('active_visitor_keys', set())
    now = timezone.now().timestamp()
    valid_keys = set()

    if isinstance(active_keys, set):
        for key in list(active_keys):
            last_seen = cache.get(key)
            if last_seen and (now - last_seen) < 300:
                valid_keys.add(key)
    
    cache.set('active_visitor_keys', valid_keys, timeout=600)
    online_count = max(len(valid_keys), 1)

    extra_context.update({
        'total_groups': total_groups,
        'total_users': total_users,
        'online_count': online_count,
        'total_axes_attempts': total_axes_attempts,
        'total_axes_failures': total_axes_failures,
        'total_axes_logs': total_axes_logs,
        'total_listings': total_listings,
        'pending_listings_count': pending_listings_count,
        'pending_kyc_count': pending_kyc_count,
        'unresolved_reports_count': unresolved_reports_count,
        'total_notifications': total_notifications,
        'total_conversations': total_conversations,
        'total_favorites': total_favorites,
        'total_views': total_views,
        'total_areas': total_areas,
        'total_categories': total_categories,
        'total_pages': total_pages,
        'recent_users': recent_users,
        'top_categories': top_categories,
        'admin_prefix': 'portal-management-99',
    })

    return _original_admin_index(request, extra_context=extra_context)


# Apply custom index and branding to default admin site
admin.site.index = custom_admin_index
admin.site.site_header = "NaijaSale Admin"
admin.site.site_title = "NaijaSale Management"
admin.site.index_title = "Admin Dashboard"


# ==============================================================================
# MODEL ADMIN REGISTRATIONS
# ==============================================================================

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = (
        "site_name",
        "logo_preview",
        "support_phone",
        "support_email",
        "show_announcement",
        "maintenance_mode",
    )
    readonly_fields = ("logo_preview", "system_cleanup_card")
    fieldsets = (
        ("Platform Storage & System Hygiene", {
            "fields": ("system_cleanup_card",),
            "description": "Safe maintenance tool: clears expired sessions, vacuums database fragmentation, and deletes orphaned listing images.",
        }),
        ("Branding & Identity", {
            "fields": ("site_name", "tagline", "logo", "logo_preview"),
        }),
        ("Customer Support & Location", {
            "fields": ("support_phone", "support_whatsapp", "support_email", "office_address"),
        }),
        ("Social Profiles", {
            "fields": ("facebook_url", "twitter_url", "instagram_url"),
        }),
        ("Platform Banners & Status", {
            "fields": ("announcement_text", "show_announcement", "maintenance_mode"),
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 45px; max-width: 140px; border-radius: 8px; object-fit: contain; background: #5B21B6; padding: 4px;" />',
                obj.logo.url,
            )
        return "No logo uploaded"
    logo_preview.short_description = "Live Logo Preview"

    def system_cleanup_card(self, obj):
        html = '''
        <div style="background: linear-gradient(135deg, #1E1B4B 0%, #4338CA 100%); padding: 18px; border-radius: 12px; color: white; max-width: 650px; box-shadow: 0 4px 12px rgba(67,56,202,0.25);">
            <div style="font-weight: 800; font-size: 15px; margin-bottom: 6px;">
                ⚡ Safe Storage & Database Optimizer
            </div>
            <p style="font-size: 12px; line-height: 1.5; color: #C7D2FE; margin: 0 0 14px 0;">
                Clears expired Django user sessions, vacuums database fragmentation to speed up SQL queries, and purges orphaned photos in media/listings that no longer belong to any active ad.
            </p>
            <a href="/portal-management-99/marketplace/sitesetting/system-cleanup/" 
               onclick="return confirm('Run Safe System Optimization? Active listings and user files remain completely safe.');"
               style="display: inline-block; background-color: #059669; color: #FFFFFF; font-weight: 700; font-size: 12px; padding: 10px 18px; border-radius: 8px; text-decoration: none; text-transform: uppercase; letter-spacing: 0.5px;">
                🚀 Run Safe Maintenance
            </a>
        </div>
        '''
        return mark_safe(html)
    system_cleanup_card.short_description = "System Hygiene"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('system-cleanup/', self.admin_site.admin_view(self.system_cleanup_view), name='staff_system_cleanup'),
        ]
        return custom_urls + urls

    def system_cleanup_view(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Permission Denied: Only staff members can run maintenance.")
            return redirect("admin:index")

        deleted_files_count = 0
        freed_bytes = 0
        total_scanned_images = 0

        VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
        valid_db_filenames = set()

        def register_field(field_file):
            if field_file and hasattr(field_file, 'name') and field_file.name:
                clean_name = str(field_file.name).replace('\\', '/').strip('/').lower()
                if clean_name:
                    valid_db_filenames.add(clean_name)
                    valid_db_filenames.add(Path(clean_name).name)

        for img in ListingImage.objects.all():
            register_field(img.image)

        for prof in SellerProfile.objects.all():
            register_field(prof.avatar)
            register_field(prof.store_banner)
            register_field(prof.id_document)
            register_field(prof.selfie_image)

        for cat in Category.objects.all():
            register_field(cat.icon)

        for sub in SubCategory.objects.all():
            register_field(sub.icon)

        for setting in SiteSetting.objects.all():
            register_field(setting.logo)

        media_root = Path(settings.MEDIA_ROOT).resolve()
        safe_target_subdirs = [
            media_root / 'listings',
            media_root / 'listing_images',
            media_root / 'sellers',
            media_root / 'uploads',
        ]

        for target_dir in safe_target_subdirs:
            if not target_dir.exists():
                continue

            for root, dirs, files in os.walk(target_dir):
                for file_name in files:
                    file_path = Path(root) / file_name

                    if file_path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
                        continue

                    try:
                        file_path.relative_to(media_root)
                    except ValueError:
                        continue

                    total_scanned_images += 1
                    rel_path_str = str(file_path.relative_to(media_root)).replace('\\', '/').strip('/').lower()
                    pure_name = file_name.lower()

                    if (rel_path_str not in valid_db_filenames) and (pure_name not in valid_db_filenames):
                        try:
                            f_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files_count += 1
                            freed_bytes += f_size
                        except Exception:
                            pass

        sessions_purged = True
        try:
            call_command('clearsessions')
        except Exception:
            sessions_purged = False

        db_vacuumed = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM;")
        except Exception:
            db_vacuumed = False

        freed_mb = freed_bytes / (1024 * 1024)
        active_db_count = len(valid_db_filenames)

        msg = (
            f"✅ System Optimization Complete! "
            f"Scanned {total_scanned_images} uploaded image(s) in media folders against {active_db_count} active database reference(s). "
            f"Purged {deleted_files_count} orphaned file(s) (freed {freed_mb:.2f} MB). "
            f"Expired Sessions: {'Cleared' if sessions_purged else 'N/A'}. "
            f"Database Fragmentation: {'Vacuumed' if db_vacuumed else 'Skipped (Non-SQLite)'}."
        )
        messages.success(request, msg)
        return redirect('/portal-management-99/marketplace/sitesetting/')


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "updated_at")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "order")


class AreaInline(admin.TabularInline):
    model = Area
    extra = 1


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [AreaInline]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "is_popular")
    list_filter = ("state", "is_popular")
    search_fields = ("name", "state__name")


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon_name", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubCategoryInline]


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name", "category__name")


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "is_nin_verified", "is_cac_verified", "state", "area", "is_banned")
    list_editable = ("is_nin_verified", "is_cac_verified")
    list_filter = ("is_nin_verified", "is_cac_verified", "state", "is_banned")
    search_fields = ("user__username", "phone_number", "whatsapp_number", "instagram_handle")


@admin.register(SellerReview)
class SellerReviewAdmin(admin.ModelAdmin):
    list_display = ("seller", "reviewer", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("seller__username", "reviewer__username", "comment")


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price",
        "category",
        "seller",
        "condition",
        "state",
        "area",
        "status",
        "is_featured",
        "created_at",
    )
    list_filter = ("status", "is_featured", "condition", "state", "category")
    search_fields = ("title", "description", "seller__username")
    list_editable = ("status", "is_featured")
    inlines = [ListingImageInline]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "listing", "created_at")
    search_fields = ("user__username", "listing__title")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "text", "is_read", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("listing", "buyer", "seller", "updated_at")
    search_fields = ("listing__title", "buyer__username", "seller__username")
    inlines = [MessageInline]


@admin.register(ReportedListing)
class ReportedListingAdmin(admin.ModelAdmin):
    list_display = ("listing", "reason", "reported_by", "created_at", "is_resolved")
    list_filter = ("reason", "is_resolved", "created_at")
    list_editable = ("is_resolved",)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "get_staff_name", "role", "phone", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("employee_id", "user__username", "user__first_name", "user__last_name", "phone")
    list_editable = ("is_active",)

    def get_staff_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_staff_name.short_description = "Staff Member"


@admin.register(StaffActivityLog)
class StaffActivityLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "staff", "action", "target_object_id", "ip_address")
    list_filter = ("action", "timestamp", "staff")
    search_fields = ("staff__username", "target_object_id", "details", "ip_address")
    readonly_fields = ("staff", "action", "target_object_id", "details", "ip_address", "timestamp")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False