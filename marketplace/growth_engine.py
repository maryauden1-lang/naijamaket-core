from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

from .models import Listing, SystemNotification


def run_seller_growth_checks(user):
    """
    Standalone, fail-silent seller retention engine.
    Checks at most once every 12 hours per user so dashboard speed is never affected:
      1. Boost Expiry Warning (< 24 hours left on an active VIP/Featured ad)
      2. Zero-Views Ad Rescue (active ad live 48+ hours with < 5 views)
    """
    if not user or not getattr(user, "is_authenticated", False):
        return

    try:
        throttle_key = f"ns_growth_check_v1_{user.id}"
        if cache.get(throttle_key):
            return
        cache.set(throttle_key, True, timeout=60 * 60 * 12)

        now = timezone.now()
        active_ads = list(
            Listing.objects.filter(seller=user, status="active").order_by("-created_at")[:20]
        )
        if not active_ads:
            return

        # ------------------------------------------------------------------
        # 1. BOOST EXPIRY NUDGE (< 24 hours remaining)
        # ------------------------------------------------------------------
        soon_cutoff = now + timedelta(hours=24)
        for ad in active_ads:
            if ad.is_featured and ad.featured_until and now < ad.featured_until <= soon_cutoff:
                dedupe_key = f"ns_boost_expiry_nudge_{ad.id}"
                if not cache.get(dedupe_key):
                    hours_left = max(1, int((ad.featured_until - now).total_seconds() // 3600))
                    SystemNotification.objects.create(
                        recipient=user,
                        title=f"Your VIP Boost ends in ~{hours_left}h!",
                        message=(
                            f"Your boosted ad '{ad.title[:45]}' will drop out of top placement in about {hours_left} hour(s). "
                            f"Tap here to extend your boost now and keep getting priority buyer calls!"
                        ),
                        link=f"/promote/{ad.id}/",
                    )
                    cache.set(dedupe_key, True, timeout=60 * 60 * 48)
                    break  # Send at most 1 boost expiry alert per check

        # ------------------------------------------------------------------
        # 2. ZERO-VIEWS AD RESCUE (Live 48+ hours with < 5 views)
        # ------------------------------------------------------------------
        age_cutoff = now - timedelta(hours=48)
        for ad in active_ads:
            if (
                not ad.is_featured
                and ad.created_at <= age_cutoff
                and (ad.views_count or 0) < 5
            ):
                dedupe_key = f"ns_zero_views_nudge_{ad.id}"
                if not cache.get(dedupe_key):
                    SystemNotification.objects.create(
                        recipient=user,
                        title="Need more buyers for your ad?",
                        message=(
                            f"Your listing '{ad.title[:45]}' has only {ad.views_count or 0} view(s) so far. "
                            f"Boost it from ₦1,000 or share your WhatsApp Status flyer from your dashboard to reach 5x more buyers!"
                        ),
                        link=f"/promote/{ad.id}/",
                    )
                    cache.set(dedupe_key, True, timeout=60 * 60 * 24 * 7)
                    break  # Send at most 1 low-view tip per check

    except Exception:
        # Fail-silent guarantee: never interrupt seller dashboard loading
        pass