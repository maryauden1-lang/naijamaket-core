import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import AbandonedIntent, Listing


def record_user_intent(user, intent_type, listing=None, plan_name="", amount_ngn=0, notes=""):
    """
    Fail-silent upsert helper: updates an existing open ABANDONED record for this
    user + intent_type (so switching boost plans doesn't spam duplicate rows).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return
    try:
        amt = Decimal(str(amount_ngn or 0))
        existing = (
            AbandonedIntent.objects.filter(
                user=user,
                intent_type=intent_type,
                status__in=["ABANDONED", "CONTACTED"],
            )
            .order_by("-updated_at")
            .first()
        )
        if existing:
            existing.listing = listing or existing.listing
            if plan_name:
                existing.plan_name = str(plan_name)[:120]
            if amt > 0:
                existing.amount_ngn = amt
            if notes:
                existing.notes = str(notes)[:255]
            existing.status = "ABANDONED"
            existing.save(update_fields=["listing", "plan_name", "amount_ngn", "notes", "status", "updated_at"])
        else:
            AbandonedIntent.objects.create(
                user=user,
                intent_type=intent_type,
                status="ABANDONED",
                listing=listing,
                plan_name=str(plan_name or "")[:120],
                amount_ngn=amt,
                notes=str(notes or "")[:255],
            )
    except Exception:
        pass


def mark_intent_converted(user, intent_type=None, listing=None):
    """
    Automatically marks open leads as CONVERTED the moment the user completes
    payment or wallet boost, so staff never follow up with someone who already paid.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return
    try:
        qs = AbandonedIntent.objects.filter(
            user=user,
            status__in=["ABANDONED", "CONTACTED"],
        )
        if intent_type:
            qs = qs.filter(intent_type=intent_type)
        if listing:
            qs = qs.filter(listing=listing)
        qs.update(status="CONVERTED")
    except Exception:
        pass


@require_POST
def track_intent_api_view(request):
    """
    Lightweight background endpoint called silently from promote_ad.html and wallet.html.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": True})

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        data = request.POST

    intent_type = str(data.get("intent_type", "")).strip()
    if intent_type not in ("WALLET_TOPUP", "AD_BOOST", "POST_AD_DRAFT", "KYC_SUBMIT"):
        return JsonResponse({"ok": False}, status=400)

    listing = None
    listing_id = data.get("listing_id")
    if listing_id:
        listing = Listing.objects.filter(id=listing_id, seller=request.user).first()

    record_user_intent(
        user=request.user,
        intent_type=intent_type,
        listing=listing,
        plan_name=data.get("plan_name", ""),
        amount_ngn=data.get("amount_ngn", 0),
        notes=data.get("notes", ""),
    )
    return JsonResponse({"ok": True})