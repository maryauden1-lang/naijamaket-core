import hashlib
import hmac
import json
import uuid
import urllib.request
import urllib.error
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Listing, PromotionPlan, PaymentTransaction


def _activate_listing_boost(transaction):
    """Helper to activate boost status and extend expiry cleanly."""
    if transaction.status == "SUCCESSFUL":
        return

    listing = transaction.listing
    plan = transaction.plan
    duration = plan.duration_days if plan else 7

    base_time = (
        listing.featured_until
        if (listing.is_featured and listing.featured_until and listing.featured_until > timezone.now())
        else timezone.now()
    )

    listing.is_featured = True
    listing.featured_until = base_time + timedelta(days=duration)
    if plan and plan.badge_type:
        listing.promotion_badge = plan.badge_type
    listing.save(update_fields=["is_featured", "featured_until", "promotion_badge"])

    transaction.status = "SUCCESSFUL"
    transaction.save(update_fields=["status"])


@login_required
def promote_listing_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, seller=request.user)
    plans = PromotionPlan.objects.filter(is_active=True).order_by('price_ngn')

    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        gateway = request.POST.get("gateway", "PAYSTACK").upper()
        plan = get_object_or_404(PromotionPlan, id=plan_id, is_active=True)

        unique_ref = f"NS-{uuid.uuid4().hex[:10].upper()}"
        customer_email = request.user.email or f"{request.user.username}@naijasale.com"

        transaction = PaymentTransaction.objects.create(
            reference=unique_ref,
            user=request.user,
            listing=listing,
            plan=plan,
            amount_paid=plan.price_ngn,
            currency="NGN",
            gateway=gateway,
            status="PENDING",
            customer_email=customer_email,
        )

        callback_url = request.build_absolute_uri('/payment/callback/')

        # --- LOCAL DEV SANDBOX FALLBACK (When real keys aren't set yet) ---
        paystack_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        flw_key = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")

        if (gateway == "PAYSTACK" and "placeholder" in paystack_key) or (
            gateway == "FLUTTERWAVE" and "placeholder" in flw_key
        ):
            _activate_listing_boost(transaction)
            messages.success(
                request,
                f"[Test Mode] {plan.name} activated! Your ad is now boosted for {plan.duration_days} days."
            )
            return redirect("marketplace:listing_detail", slug=listing.slug)

        # --- PAYSTACK ---
        if gateway == "PAYSTACK":
            payload = {
                "email": customer_email,
                "amount": int(plan.price_ngn * 100),
                "reference": unique_ref,
                "callback_url": callback_url,
            }
            req = urllib.request.Request(
                "https://api.paystack.co/transaction/initialize",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {paystack_key}",
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    res_data = json.loads(res.read().decode("utf-8"))
                    if res_data.get("status"):
                        return redirect(res_data["data"]["authorization_url"])
            except Exception as e:
                messages.error(request, f"Paystack connection error: {e}")

        # --- FLUTTERWAVE ---
        elif gateway == "FLUTTERWAVE":
            payload = {
                "tx_ref": unique_ref,
                "amount": str(plan.price_ngn),
                "currency": "NGN",
                "redirect_url": callback_url,
                "customer": {
                    "email": customer_email,
                    "name": request.user.username,
                },
                "customizations": {
                    "title": f"NaijaSale - {plan.name}",
                    "description": f"Boost for ad #{listing.id}",
                }
            }
            req = urllib.request.Request(
                "https://api.flutterwave.com/v3/payments",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {flw_key}",
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as res:
                    res_data = json.loads(res.read().decode("utf-8"))
                    if res_data.get("status") == "success":
                        return redirect(res_data["data"]["link"])
            except Exception as e:
                messages.error(request, f"Flutterwave connection error: {e}")

    return render(request, "marketplace/promote_ad.html", {"listing": listing, "plans": plans})


@login_required
def payment_callback_view(request):
    reference = request.GET.get("reference") or request.GET.get("tx_ref") or request.GET.get("trxref")
    transaction_id = request.GET.get("transaction_id")

    if not reference:
        return redirect("marketplace:dashboard")

    transaction = PaymentTransaction.objects.filter(reference=reference).select_related("listing", "plan").first()
    if not transaction:
        return redirect("marketplace:dashboard")

    if transaction.status == "SUCCESSFUL":
        return redirect("marketplace:listing_detail", slug=transaction.listing.slug)

    # Verify Paystack
    if transaction.gateway == "PAYSTACK":
        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        req = urllib.request.Request(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret_key}"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
                if data.get("status") and data.get("data", {}).get("status") == "success":
                    _activate_listing_boost(transaction)
                    messages.success(request, "Payment confirmed! Your ad is now boosted.")
                    return redirect("marketplace:listing_detail", slug=transaction.listing.slug)
        except Exception:
            pass

    # Verify Flutterwave
    elif transaction.gateway == "FLUTTERWAVE" and transaction_id:
        secret_key = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "")
        req = urllib.request.Request(
            f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
            headers={"Authorization": f"Bearer {secret_key}"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
                if (
                    data.get("status") == "success"
                    and data.get("data", {}).get("status") == "successful"
                    and data.get("data", {}).get("tx_ref") == reference
                ):
                    transaction.gateway_reference = str(transaction_id)
                    transaction.save(update_fields=["gateway_reference"])
                    _activate_listing_boost(transaction)
                    messages.success(request, "Payment confirmed! Your ad is now boosted.")
                    return redirect("marketplace:listing_detail", slug=transaction.listing.slug)
        except Exception:
            pass

    messages.error(request, "Payment could not be verified. Contact support if debited.")
    return redirect("marketplace:dashboard")


@csrf_exempt
@require_POST
def paystack_webhook(request):
    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "").encode("utf-8")
    signature = request.headers.get("x-paystack-signature", "")

    computed_hmac = hmac.new(secret_key, request.body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(computed_hmac, signature):
        return HttpResponse(status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if payload.get("event") == "charge.success":
        reference = payload.get("data", {}).get("reference")
        if reference:
            transaction = PaymentTransaction.objects.filter(reference=reference).select_related("listing", "plan").first()
            if transaction:
                _activate_listing_boost(transaction)

    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    secret_hash = getattr(settings, "FLUTTERWAVE_SECRET_HASH", "")
    signature = request.headers.get("verif-hash", "")

    if not secret_hash or signature != secret_hash:
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event_data = payload.get("data", {})
    if payload.get("event") == "charge.completed" and event_data.get("status") == "successful":
        reference = event_data.get("tx_ref")
        if reference:
            transaction = PaymentTransaction.objects.filter(reference=reference).select_related("listing", "plan").first()
            if transaction:
                transaction.gateway_reference = str(event_data.get("id", ""))
                transaction.save(update_fields=["gateway_reference"])
                _activate_listing_boost(transaction)

    return HttpResponse(status=200)