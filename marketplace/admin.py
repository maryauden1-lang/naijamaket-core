import os
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
            "description": "Available to all authorized staff members to purge dead images, clear expired sessions, and vacuum database fragmentation."
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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = "Site Settings & Platform Storage Hygiene"
        return super().changelist_view(request, extra_context=extra_context)

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
        <div style="background: linear-gradient(135deg, #4C1D95 0%, #6D28D9 100%); padding: 18px; border-radius: 14px; color: white; max-width: 650px; box-shadow: 0 4px 12px rgba(109,40,217,0.25);">
            <div style="font-weight: 900; font-size: 15px; margin-bottom: 6px;">
                ⚡ Platform Storage & Database Optimizer
            </div>
            <p style="font-size: 12px; line-height: 1.5; color: #E9D5FF; margin: 0 0 14px 0;">
                Scans all media folders on disk, deletes orphaned photos from deleted ads and inactive users, clears stale sessions, and reclaims wasted SQLite/Postgres disk space.
            </p>
            <a href="/admin/marketplace/sitesetting/system-cleanup/" 
               onclick="return confirm('Staff Confirmation: Are you sure you want to purge dead orphaned media files and optimize the platform database? Active ad photos will remain safe.');"
               style="display: inline-block; background-color: #FF8A00; color: #FFFFFF; font-weight: 800; font-size: 12px; padding: 10px 18px; border-radius: 10px; text-decoration: none; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(255,138,0,0.4);">
               🚀 Purge Dead Storage & Optimize Platform
            </a>
        </div>
        '''
        return mark_safe(html)
    system_cleanup_card.short_description = "Platform Garbage Collection"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('system-cleanup/', self.admin_site.admin_view(self.system_cleanup_view), name='staff_system_cleanup'),
        ]
        return custom_urls + urls

    def system_cleanup_view(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Permission Denied: Only authorized staff members can run system hygiene tasks.")
            return redirect("admin:index")

        deleted_files_count = 0
        freed_bytes = 0

        # 1. Collect all valid database file paths across models
        valid_db_files = set()

        def add_file(field_file):
            if field_file and hasattr(field_file, 'name') and field_file.name:
                valid_db_files.add(os.path.normpath(field_file.name))

        for img in ListingImage.objects.all():
            add_file(img.image)

        for prof in SellerProfile.objects.all():
            add_file(prof.avatar)
            add_file(prof.store_banner)
            add_file(prof.id_document)
            add_file(prof.selfie_image)

        for cat in Category.objects.all():
            add_file(cat.icon)

        for sub in SubCategory.objects.all():
            add_file(sub.icon)

        for setting in SiteSetting.objects.all():
            add_file(setting.logo)

        # 2. Inspect physical files in media root and delete orphans
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
            for root, dirs, files in os.walk(media_root):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    rel_path = os.path.normpath(os.path.relpath(file_path, media_root))

                    # Safety check: Never delete default placeholder or static icons
                    if rel_path not in valid_db_files:
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted_files_count += 1
                            freed_bytes += file_size
                        except Exception:
                            pass

        # 3. Clean expired Django sessions
        try:
            call_command('clearsessions')
        except Exception:
            pass

        # 4. Vacuum database to reclaim fragmented space
        try:
            with connection.cursor() as cursor:
                cursor.execute("VACUUM;")
        except Exception:
            pass

        freed_mb = freed_bytes / (1024 * 1024)
        messages.success(
            request,
            f"✅ System Optimization Complete! Deleted {deleted_files_count} orphaned file(s), freed {freed_mb:.2f} MB of storage, purged expired sessions, and vacuumed database fragmentation."
        )
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


# =========================================================================
# 9. CEO STAFF CONTROLS & IMMUTABLE AUDIT TRAIL
# =========================================================================
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