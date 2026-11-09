import os
from pathlib import Path
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.urls import path
from django.conf import settings
from django.db import connection
from django.core.management import call_command

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


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = (
        "site_name", 
        "logo_preview", 
        "support_phone", 
        "support_email", 
        "show_announcement", 
        "maintenance_mode"
    )
    readonly_fields = ("logo_preview", "system_cleanup_card")
    fieldsets = (
        ("Platform Storage & System Hygiene", {
            "fields": ("system_cleanup_card",),
            "description": "Safe maintenance tool: clears expired sessions, vacuums database fragmentation, and deletes orphaned listing images."
        }),
        ("Branding & Identity", {
            "fields": ("site_name", "tagline", "logo", "logo_preview")
        }),
        ("Customer Support & Location", {
            "fields": ("support_phone", "support_whatsapp", "support_email", "office_address")
        }),
        ("Social Profiles", {
            "fields": ("facebook_url", "twitter_url", "instagram_url")
        }),
        ("Platform Banners & Status", {
            "fields": ("announcement_text", "show_announcement", "maintenance_mode")
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 45px; max-width: 140px; border-radius: 8px; object-fit: contain; background: #5B21B6; padding: 4px;" />',
                obj.logo.url
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
            <a href="/admin/marketplace/sitesetting/system-cleanup/" 
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

        # Whitelist ONLY image extensions (hard guard)
        VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

        # 1. Collect all valid active database file paths
        valid_db_filenames = set()

        def register_field(field_file):
            if field_file and hasattr(field_file, 'name') and field_file.name:
                # Normalize slashes and lower-case
                clean_name = str(field_file.name).replace('\\', '/').strip('/').lower()
                if clean_name:
                    valid_db_filenames.add(clean_name)
                    # Also register just the filename (e.g. "photo123.jpg") for extra matching accuracy
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

        # 2. Inspect ONLY safe dedicated upload folders inside MEDIA_ROOT
        media_root = Path(settings.MEDIA_ROOT).resolve()
        
        # STRICT BOUNDARY: Only scan these specific subdirectories if they exist
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

                    # HARD GUARD 1: Only check whitelisted image files
                    if file_path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
                        continue

                    # HARD GUARD 2: Must be physically inside media_root
                    try:
                        file_path.relative_to(media_root)
                    except ValueError:
                        continue  # Skip anything outside media_root

                    total_scanned_images += 1

                    rel_path_str = str(file_path.relative_to(media_root)).replace('\\', '/').strip('/').lower()
                    pure_name = file_name.lower()

                    # If not in active DB records, it's an orphan
                    if (rel_path_str not in valid_db_filenames) and (pure_name not in valid_db_filenames):
                        try:
                            f_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files_count += 1
                            freed_bytes += f_size
                        except Exception:
                            pass

        # 3. Clear expired Django sessions
        sessions_purged = True
        try:
            call_command('clearsessions')
        except Exception:
            sessions_purged = False

        # 4. Vacuum database
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
        return redirect('/admin/marketplace/sitesetting/')


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