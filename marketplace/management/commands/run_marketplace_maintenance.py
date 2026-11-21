from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from marketplace.models import (
    Listing,
    SystemNotification,
    SellerProfile,
    ReportedListing,
)


class Command(BaseCommand):
    help = "Runs automated Naijasale marketplace maintenance and sends a daily CEO report."

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-report',
            action='store_true',
            help='Force send the CEO daily summary email immediately (for testing or daily cron).',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"[{now:%Y-%m-%d %H:%M}] Starting Naijasale maintenance...")

        # 1. Expire finished VIP / Featured boosts & notify sellers
        expired_boosts_qs = Listing.objects.filter(
            is_featured=True,
            featured_until__isnull=False,
            featured_until__lte=now,
        ).select_related('seller')

        expired_boost_count = 0
        for ad in expired_boosts_qs:
            ad.is_featured = False
            ad.save(update_fields=['is_featured'])
            expired_boost_count += 1

            SystemNotification.objects.create(
                recipient=ad.seller,
                title="⏳ Your VIP Ad Boost Has Ended",
                message=f"Your promotion for '{ad.title}' has expired. Tap to boost it again and stay at the top!",
                link=f"/promote/{ad.id}/",
            )

        # 2. Delete old READ system notifications (older than 30 days)
        notif_cutoff = now - timedelta(days=30)
        deleted_notifs, _ = SystemNotification.objects.filter(
            is_read=True,
            created_at__lt=notif_cutoff,
        ).delete()

        # 3. Clean up abandoned REJECTED ads older than 14 days
        rejected_cutoff = now - timedelta(days=14)
        deleted_rejected, _ = Listing.objects.filter(
            status='rejected',
            created_at__lt=rejected_cutoff,
        ).delete()

        # 4. Purge expired browser sessions safely (keeps active users logged in)
        call_command('clearsessions')

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {expired_boost_count} boosts expired, "
                f"{deleted_notifs} old notifications removed, "
                f"{deleted_rejected} stale rejected ads cleaned."
            )
        )

        # 5. Send CEO Summary Email (every morning at 8 AM WAT, or when --send-report is used)
        # Note: 8:00 AM Nigeria time (WAT) = 07:00 UTC
        is_morning_report_hour = (now.hour == 7)
        if options.get('send_report') or is_morning_report_hour:
            self.send_ceo_daily_report(
                now=now,
                expired_boost_count=expired_boost_count,
                deleted_notifs=deleted_notifs,
                deleted_rejected=deleted_rejected,
            )

    def send_ceo_daily_report(self, now, expired_boost_count, deleted_notifs, deleted_rejected):
        last_24h = now - timedelta(hours=24)

        total_users = User.objects.filter(is_staff=False, is_superuser=False).count()
        new_users_24h = User.objects.filter(
            is_staff=False, is_superuser=False, date_joined__gte=last_24h
        ).count()

        total_active_ads = Listing.objects.filter(status='active').count()
        new_ads_24h = Listing.objects.filter(created_at__gte=last_24h).count()
        active_vip_ads = Listing.objects.filter(is_featured=True, status='active').count()

        pending_ads = Listing.objects.filter(status='pending').count()
        pending_kyc = SellerProfile.objects.filter(verification_status='pending').count()
        unresolved_reports = ReportedListing.objects.filter(is_resolved=False).count()

        admin_emails = list(
            User.objects.filter(is_superuser=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
        if not admin_emails:
            self.stdout.write(self.style.WARNING("No superuser email found; skipping CEO report email."))
            return

        subject = f"📊 Naijasale Daily CEO Report — {now:%b %d, %Y}"
        text_body = (
            f"Naijasale 24-Hour Summary ({now:%Y-%m-%d %H:%M UTC})\n"
            f"--------------------------------------------------\n"
            f"New Signups (24h): {new_users_24h} (Total Users: {total_users})\n"
            f"New Ads Posted (24h): {new_ads_24h} (Total Live Ads: {total_active_ads})\n"
            f"Active VIP Boosted Ads: {active_vip_ads}\n\n"
            f"Moderation Queue Right Now:\n"
            f"- Pending Ads Awaiting Approval: {pending_ads}\n"
            f"- Pending NIN/KYC Reviews: {pending_kyc}\n"
            f"- Unresolved Safety Reports: {unresolved_reports}\n\n"
            f"Automated Maintenance Performed:\n"
            f"- Expired VIP Boosts Turned Off: {expired_boost_count}\n"
            f"- Old Read Notifications Cleaned: {deleted_notifs}\n"
            f"- Stale Rejected Ads Removed: {deleted_rejected}\n"
        )

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;border:1px solid #e2e8f0;border-radius:12px;">
            <h2 style="color:#4C1D95;margin-top:0;">📊 Naijasale Daily CEO Report</h2>
            <p style="color:#64748b;font-size:13px;">24-Hour Platform & Maintenance Digest • {now:%B %d, %Y}</p>

            <h3 style="color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:6px;">🚀 Growth (Last 24 Hours)</h3>
            <ul style="line-height:1.8;color:#1e293b;">
                <li><strong>New Users Joined:</strong> {new_users_24h} <em>(Total: {total_users:,})</em></li>
                <li><strong>New Ads Submitted:</strong> {new_ads_24h} <em>(Live Now: {total_active_ads:,})</em></li>
                <li><strong>Active VIP Boosted Ads:</strong> {active_vip_ads}</li>
            </ul>

            <h3 style="color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:6px;">🛡️ Items Needing Your Review</h3>
            <ul style="line-height:1.8;color:#1e293b;">
                <li><strong>Pending Ads:</strong> {pending_ads}</li>
                <li><strong>Pending NIN/KYC Requests:</strong> {pending_kyc}</li>
                <li><strong>Unresolved Reports:</strong> {unresolved_reports}</li>
            </ul>

            <h3 style="color:#0f172a;border-bottom:1px solid #e2e8f0;padding-bottom:6px;">🧹 Auto-Maintenance Completed</h3>
            <ul style="line-height:1.8;color:#1e293b;">
                <li><strong>Expired VIP Boosts Turned Off:</strong> {expired_boost_count}</li>
                <li><strong>Old Read Notifications Purged:</strong> {deleted_notifs}</li>
                <li><strong>Stale Rejected Ads Cleaned:</strong> {deleted_rejected}</li>
            </ul>

            <p style="margin-top:20px;">
                <a href="https://naijasale.com/portal-management-99/" style="background:#6D28D9;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:bold;">Open Admin Portal</a>
            </p>
        </div>
        """

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        self.stdout.write(self.style.SUCCESS(f"CEO report emailed to: {', '.join(admin_emails)}"))