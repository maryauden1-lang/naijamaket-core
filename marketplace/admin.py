import os
import time
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
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse

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
    PromotionPlan,
    PaymentTransaction,
    SystemNotification,
    PromoBanner,
    AbandonedIntent,
)
from .support_sync import push_staff_support_message


# ==============================================================================
# REAL-TIME POLLING JSON ENDPOINT FOR BACKGROUND FETCH
# ==============================================================================
def live_online_stats_view(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    now_ts = time.time()
    active_registry = cache.get('active_visitor_registry') or {}

    live_devices = [
        device_id for device_id, ts in active_registry.items()
        if (now_ts - ts) < 300
    ]
    online_count = max(len(live_devices), 1)

    pending_listings = Listing.objects.filter(status='pending').count()
    pending_kyc = SellerProfile.objects.filter(verification_status='pending').count()
    unresolved_reports = ReportedListing.objects.filter(is_resolved=False).count()
    total_notifications = pending_listings + pending_kyc + unresolved_reports

    total_revenue = (
        PaymentTransaction.objects.filter(status='SUCCESSFUL').aggregate(total=Sum('amount_paid'))['total']
        or 0
    )

    return JsonResponse({
        'online_count': online_count,
        'pending_listings': pending_listings,
        'pending_kyc': pending_kyc,
        'unresolved_reports': unresolved_reports,
        'total_notifications': total_notifications,
        'total_revenue': f"{total_revenue:,.2f}",
    })


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

    total_notifications = pending_listings_count + pending_kyc_count + unresolved_reports_count

    total_conversations = Conversation.objects.count()
    total_favorites = Favorite.objects.count()
    total_views = Listing.objects.aggregate(total=Sum('views_count'))['total'] or 0

    total_areas = Area.objects.count()
    total_categories = Category.objects.count()
    total_pages = StaticPage.objects.count()

    # 3. Live Account Balance & Payment Revenue Metrics
    successful_txs = PaymentTransaction.objects.filter(status='SUCCESSFUL')
    total_revenue = successful_txs.aggregate(total=Sum('amount_paid'))['total'] or 0
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue = successful_txs.filter(created_at__gte=today_start).aggregate(total=Sum('amount_paid'))['total'] or 0
    successful_tx_count = successful_txs.count()
    pending_tx_count = PaymentTransaction.objects.filter(status='PENDING').count()
    recent_transactions = PaymentTransaction.objects.select_related('user', 'listing', 'plan').order_by('-created_at')[:5]

    # 4. Recent Registered Users (Latest 5)
    recent_users = User.objects.select_related('seller_profile').order_by('-date_joined')[:5]

    # 5. Top Categories with listing counts
    top_categories = Category.objects.annotate(
        listing_count=Count('listings')
    ).order_by('-listing_count')[:4]

    # 6. Real-Time Online Visitors
    now_ts = time.time()
    active_registry = cache.get('active_visitor_registry') or {}
    live_devices = [
        device_id for device_id, ts in active_registry.items()
        if (now_ts - ts) < 300
    ]
    online_count = max(len(live_devices), 1)

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
        # Bank-style balance variables
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'successful_tx_count': successful_tx_count,
        'pending_tx_count': pending_tx_count,
        'recent_transactions': recent_transactions,
    })

    return _original_admin_index(request, extra_context=extra_context)


admin.site.index = custom_admin_index
admin.site.site_header = "NaijaSale Admin"
admin.site.site_title = "NaijaSale Management"
admin.site.index_title = "Admin Dashboard"

_original_get_urls = admin.site.get_urls


def custom_admin_urls():
    custom_patterns = [
        path('live-stats-ping/', admin.site.admin_view(live_online_stats_view), name='live_stats_ping'),
    ]
    return custom_patterns + _original_get_urls()


admin.site.get_urls = custom_admin_urls


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
            "description": "Safe maintenance tool: clears expired sessions, optimizes database fragmentation, and removes only unlinked local media files without touching Backblaze B2.",
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
                Clears expired Django user sessions and optimizes SQLite database fragmentation while keeping all Backblaze B2 files and live customer ads 100% untouched.
            </p>
            <a href="/portal-management-99/marketplace/sitesetting/system-cleanup/" 
               onclick="return confirm('Run Safe System Optimization? Active listings and Backblaze B2 customer files remain completely safe.');"
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

        msg = (
            f"✅ System Optimization Complete! "
            f"Expired Sessions: {'Cleared' if sessions_purged else 'N/A'}. "
            f"SQLite Database Fragmentation: {'Vacuumed' if db_vacuumed else 'Skipped'}. "
            f"All customer Backblaze B2 files remain untouched."
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


# ==============================================================================
# MONETIZATION: PROMOTION PLANS & PAYMENT TRANSACTIONS
# ==============================================================================

@admin.register(PromotionPlan)
class PromotionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "badge_type", "duration_days", "price_ngn", "is_active")
    list_editable = ("price_ngn", "is_active")
    list_filter = ("badge_type", "is_active")
    search_fields = ("name",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "user",
        "listing",
        "plan",
        "formatted_amount",
        "gateway",
        "status_badge",
        "created_at",
    )
    list_filter = ("status", "gateway", "created_at")
    search_fields = ("reference", "gateway_reference", "user__username", "customer_email", "listing__title")
    readonly_fields = ("reference", "gateway_reference", "created_at", "updated_at")
    date_hierarchy = "created_at"

    def formatted_amount(self, obj):
        return format_html('<strong>₦{}</strong>', f"{obj.amount_paid:,.2f}")
    formatted_amount.short_description = "Amount"

    def status_badge(self, obj):
        if obj.status == "SUCCESSFUL":
            return mark_safe('<span style="padding: 3px 9px; font-size: 11px; font-weight: 700; border-radius: 9999px; background: #DCFCE7; color: #166534;">● PAID</span>')
        elif obj.status == "PENDING":
            return mark_safe('<span style="padding: 3px 9px; font-size: 11px; font-weight: 700; border-radius: 9999px; background: #FEF3C7; color: #92400E;">● PENDING</span>')
        return mark_safe('<span style="padding: 3px 9px; font-size: 11px; font-weight: 700; border-radius: 9999px; background: #FEE2E2; color: #991B1B;">● FAILED</span>')
    status_badge.short_description = "Status"


# ==============================================================================
# OFFICIAL CEO & ADMIN NOTIFICATIONS / BROADCASTS (IN-APP + BREVO EMAIL)
# ==============================================================================

@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "target_display", "send_to_all", "is_read", "created_at")
    list_filter = ("send_to_all", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__username", "recipient__email")
    autocomplete_fields = ("recipient",)
    fieldsets = (
        ("Audience (Choose Broadcast OR Single Account)", {
            "fields": ("send_to_all", "recipient"),
            "description": "Tick 'Send to all users' to broadcast to everyone (in-app + Gmail/email via Brevo), OR select a single user account to send an official CEO/Admin notice.",
        }),
        ("Announcement Content", {
            "fields": ("title", "message", "link"),
        }),
    )

    def target_display(self, obj):
        if obj.send_to_all and not obj.recipient:
            return "📢 All Registered Users"
        if obj.recipient:
            prefix = "📢 Broadcast → " if obj.send_to_all else "👤 Official DM → "
            return f"{prefix}{obj.recipient.username}"
        return "Unassigned"
    target_display.short_description = "Recipient"

    def _send_brevo_broadcast_email(self, recipient_emails, title, message_body, link=None):
        """Send branded HTML email in safe BCC batches of 50 via Brevo SMTP."""
        valid_emails = [e.strip() for e in recipient_emails if e and '@' in e]
        if not valid_emails:
            return 0, None

        action_url = "https://naijasale.com"
        if link:
            action_url = link if link.startswith("http") else f"https://naijasale.com{link if link.startswith('/') else '/' + link}"

        formatted_body = "<br>".join(message_body.splitlines())
        html_content = f"""
        <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; background-color: #F8FAFC; padding: 28px 16px;">
          <div style="max-width: 560px; margin: 0 auto; background: #FFFFFF; border-radius: 18px; overflow: hidden; border: 1px solid #E2E8F0; box-shadow: 0 4px 16px rgba(15,23,42,0.06);">
            <div style="background: linear-gradient(135deg, #6D28D9 0%, #7C3AED 100%); padding: 22px 26px; color: #FFFFFF;">
              <div style="font-size: 11px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; color: #FDE68A; margin-bottom: 4px;">
                Official Naijasale Update
              </div>
              <h1 style="margin: 0; font-size: 20px; font-weight: 800; line-height: 1.3;">
                {title}
              </h1>
            </div>
            <div style="padding: 26px; color: #1E293B; font-size: 14px; line-height: 1.65;">
              <p style="margin-top: 0;">Hello,</p>
              <div style="margin: 14px 0 22px 0; color: #334155;">
                {formatted_body}
              </div>
              <a href="{action_url}" style="display: inline-block; background-color: #FF8A00; color: #FFFFFF; font-weight: 800; font-size: 13px; padding: 12px 22px; border-radius: 12px; text-decoration: none;">
                Open Naijasale &rarr;
              </a>
            </div>
            <div style="background-color: #F1F5F9; padding: 14px 26px; font-size: 11px; color: #64748B; text-align: center;">
              You received this announcement because you have an active account on <strong>Naijasale.com</strong>.
            </div>
          </div>
        </div>
        """

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Naijasale <noreply@naijasale.com>")
        sent_count = 0
        batch_size = 50

        try:
            for i in range(0, len(valid_emails), batch_size):
                batch = valid_emails[i:i + batch_size]
                email = EmailMultiAlternatives(
                    subject=f"{title} — Naijasale",
                    body=f"{title}\n\n{message_body}\n\nVisit: {action_url}",
                    from_email=from_email,
                    to=[from_email],
                    bcc=batch,
                )
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=False)
                sent_count += len(batch)
            return sent_count, None
        except Exception as exc:
            return sent_count, str(exc)

    def save_model(self, request, obj, form, change):
        if not change and obj.send_to_all:
            active_users = list(User.objects.filter(is_active=True))
            notifications = [
                SystemNotification(
                    recipient=u,
                    send_to_all=True,
                    title=obj.title,
                    message=obj.message,
                    link=obj.link,
                )
                for u in active_users
            ]
            SystemNotification.objects.bulk_create(notifications)

            emails = [u.email for u in active_users if u.email]
            emailed_count, email_err = self._send_brevo_broadcast_email(
                emails, obj.title, obj.message, obj.link
            )

            if email_err:
                messages.warning(
                    request,
                    f"📢 In-app notice sent to {len(notifications)} user(s), but Brevo email paused after {emailed_count} email(s): {email_err}"
                )
            else:
                messages.success(
                    request,
                    f"📢 Official announcement '{obj.title}' sent in-app to {len(notifications)} user(s) AND emailed via Brevo to {emailed_count} Gmail/email address(es)!"
                )
        else:
            super().save_model(request, obj, form, change)
            if not change and obj.recipient and obj.recipient.email:
                emailed_count, email_err = self._send_brevo_broadcast_email(
                    [obj.recipient.email], obj.title, obj.message, obj.link
                )
                if email_err:
                    messages.warning(request, f"In-app notice saved, but Brevo email failed: {email_err}")
                else:
                    messages.success(request, f"✉️ Official email also delivered via Brevo to {obj.recipient.email}!")


# ==============================================================================
# ADMIN RECTANGULAR PROMO BANNERS + SPONSOR CLICK/VIEW ANALYTICS
# ==============================================================================

@admin.action(description="Reset Views & Clicks to 0 (Start Fresh Campaign)")
def reset_banner_analytics(modeladmin, request, queryset):
    updated = queryset.update(views_count=0, clicks_count=0)
    messages.success(request, f"✅ Reset views and clicks to 0 for {updated} banner(s).")


@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = (
        "banner_preview",
        "title",
        "formatted_views",
        "formatted_clicks",
        "ctr_badge",
        "order",
        "is_active",
        "created_at",
    )
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "link_url")
    readonly_fields = ("banner_preview", "views_count", "clicks_count", "ctr_badge")
    actions = [reset_banner_analytics]
    fieldsets = (
        ("Rectangular Promo Ad Details", {
            "fields": ("title", "banner_image", "banner_preview", "link_url", "badge_text"),
            "description": "Upload a wide rectangular ad banner. Every visitor click is tracked automatically before redirecting to the destination URL.",
        }),
        ("Sponsor Performance Analytics (Live)", {
            "fields": ("views_count", "clicks_count", "ctr_badge"),
            "description": "Real-time impressions, clicks, and Click-Through Rate (CTR) for sponsor reporting.",
        }),
        ("Display Order & Visibility", {
            "fields": ("order", "is_active"),
        }),
    )

    def banner_preview(self, obj):
        if obj.banner_image:
            return format_html(
                '<img src="{}" style="height: 54px; width: 170px; object-fit: cover; border-radius: 8px; border: 1px solid #CBD5E1;" />',
                obj.banner_image.url,
            )
        return "No image"
    banner_preview.short_description = "Preview"

    def formatted_views(self, obj):
        return format_html('<span style="font-weight: 700; color: #334155;">{}</span>', f"{obj.views_count:,}")
    formatted_views.short_description = "Views"
    formatted_views.admin_order_field = "views_count"

    def formatted_clicks(self, obj):
        return format_html(
            '<span style="padding: 3px 10px; font-size: 12px; font-weight: 800; border-radius: 9999px; background: #EDE9FE; color: #5B21B6;">{} clicks</span>',
            f"{obj.clicks_count:,}",
        )
    formatted_clicks.short_description = "Clicks"
    formatted_clicks.admin_order_field = "clicks_count"

    def ctr_badge(self, obj):
        ctr = obj.ctr_percentage
        bg = "#DCFCE7" if ctr >= 2.0 else "#F1F5F9"
        color = "#166534" if ctr >= 2.0 else "#475569"
        return format_html(
            '<span style="padding: 3px 9px; font-size: 11px; font-weight: 800; border-radius: 9999px; background: {}; color: {};">{}% CTR</span>',
            bg,
            color,
            f"{ctr:.2f}",
        )
    ctr_badge.short_description = "CTR"


# ==============================================================================
# ABANDONED TOP-UP & AD BOOST RECOVERY QUEUE (1-CLICK WHATSAPP & IN-APP CHAT)
# ==============================================================================

@admin.register(AbandonedIntent)
class AbandonedIntentAdmin(admin.ModelAdmin):
    list_display = (
        "user_info",
        "intent_type",
        "target_details",
        "formatted_amount",
        "status_badge",
        "updated_at",
        "recovery_actions",
    )
    list_filter = ("status", "intent_type", "updated_at")
    search_fields = ("user__username", "user__first_name", "user__seller_profile__phone_number", "listing__title", "plan_name")
    readonly_fields = ("user", "intent_type", "listing", "plan_name", "amount_ngn", "notes", "contacted_by", "created_at", "updated_at")

    def user_info(self, obj):
        profile = getattr(obj.user, "seller_profile", None)
        phone = profile.phone_number if profile else "No phone"
        name = obj.user.get_full_name() or obj.user.username
        return format_html('<strong>{}</strong><br><span style="color:#64748B;font-size:11px;">{}</span>', name, phone)
    user_info.short_description = "Seller"

    def target_details(self, obj):
        if obj.listing:
            return format_html('{}<br><span style="color:#6D28D9;font-size:11px;font-weight:700;">{}</span>', obj.listing.title[:45], obj.plan_name or "Boost")
        return obj.plan_name or obj.notes or "Wallet Funding"
    target_details.short_description = "What They Tried To Do"

    def formatted_amount(self, obj):
        if obj.amount_ngn and obj.amount_ngn > 0:
            return format_html('<strong>₦{}</strong>', f"{obj.amount_ngn:,.0f}")
        return "—"
    formatted_amount.short_description = "Amount"

    def status_badge(self, obj):
        colors = {
            "ABANDONED": ("#FEF3C7", "#92400E", "● STOPPED / ABANDONED"),
            "CONTACTED": ("#E0E7FF", "#3730A3", "● STAFF FOLLOWED UP"),
            "CONVERTED": ("#DCFCE7", "#166534", "● PAID / COMPLETED"),
            "DISMISSED": ("#F1F5F9", "#475569", "● DISMISSED"),
        }
        bg, fg, label = colors.get(obj.status, ("#F1F5F9", "#475569", obj.status))
        return format_html(
            '<span style="padding:3px 9px;font-size:10.5px;font-weight:800;border-radius:9999px;background:{};color:{};">{}</span>',
            bg, fg, label
        )
    status_badge.short_description = "Status"

    def recovery_actions(self, obj):
        if obj.status == "CONVERTED":
            return mark_safe('<span style="color:#16A34A;font-weight:700;font-size:11px;">✓ Converted</span>')

        wa_url = obj.whatsapp_recovery_url
        wa_btn = ""
        if wa_url:
            wa_btn = format_html(
                '<a href="{}" target="_blank" style="display:inline-block;background:#16A34A;color:#fff;font-weight:700;font-size:11px;padding:5px 10px;border-radius:8px;text-decoration:none;margin-right:5px;">WhatsApp</a>',
                wa_url
            )

        chat_url = f"/portal-management-99/marketplace/abandonedintent/{obj.id}/push-chat/"
        chat_btn = format_html(
            '<a href="{}" style="display:inline-block;background:#6D28D9;color:#fff;font-weight:700;font-size:11px;padding:5px 10px;border-radius:8px;text-decoration:none;">In-App Chat</a>',
            chat_url
        )
        return mark_safe(wa_btn + chat_btn)
    recovery_actions.short_description = "1-Click Follow-Up"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:intent_id>/push-chat/', self.admin_site.admin_view(self.push_in_app_chat_view), name='abandoned_intent_push_chat'),
        ]
        return custom + urls

    def push_in_app_chat_view(self, request, intent_id):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Unauthorized")
            return redirect("admin:index")

        intent = AbandonedIntent.objects.filter(id=intent_id).select_related("user", "listing").first()
        if not intent:
            messages.error(request, "Lead not found.")
            return redirect("/portal-management-99/marketplace/abandonedintent/")

        name = intent.user.first_name or intent.user.username
        if intent.intent_type == "AD_BOOST":
            item = intent.listing.title if intent.listing else "your ad"
            action_desc = f"boost '{item}' ({intent.plan_name or 'VIP placement'})"
        elif intent.intent_type == "WALLET_TOPUP":
            amt = f"₦{intent.amount_ngn:,.0f}" if intent.amount_ngn else "your NaijaSale Wallet"
            action_desc = f"top up {amt} into your NaijaSale Wallet"
        else:
            action_desc = "complete your action on NaijaSale"

        followup_text = (
            f"Hi {name}! 👋 We noticed you were trying to {action_desc} earlier but stopped before finishing. "
            f"Did you experience any payment or network issue? Reply right here and our team will help you!"
        )

        # Drop into the user's Live Support Chat thread (stored in cache by support_sync.py)
        push_staff_support_message(intent.user, followup_text)

        # Also send an in-app SystemNotification bell alert
        SystemNotification.objects.create(
            recipient=intent.user,
            title="Need help finishing your NaijaSale boost/top-up?",
            message=followup_text,
            link="/wallet/" if intent.intent_type == "WALLET_TOPUP" else "/dashboard/",
        )

        intent.status = "CONTACTED"
        intent.contacted_by = request.user
        intent.save(update_fields=["status", "contacted_by", "updated_at"])

        messages.success(request, f"✅ Sent helpful follow-up to {name} via Live Chat & Notification Bell!")
        return redirect("/portal-management-99/marketplace/abandonedintent/")


# ==============================================================================
# NAIJASALE WALLET & DOUBLE-ENTRY LEDGER (TAMPER-PROOF ADMIN VIEW)
# ==============================================================================
from .admin_wallet import UserWalletAdmin, WalletTransactionAdmin  # noqa: E402, F401