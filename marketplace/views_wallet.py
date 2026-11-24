import hashlib
import hmac
import json
import uuid
import urllib.request
import urllib.error
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Listing, PromotionPlan, SystemNotification
from .models_wallet import UserWallet, WalletTransaction
from .intent_tracker import record_user_intent, mark_intent_converted

MIN_TOPUP_NGN = Decimal("500.00")
MAX_TOPUP_NGN = Decimal("2000000.00")


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _paystack_headers(secret_key):
    return {
        "Authorization": f"Bearer {secret_key.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "NaijaSale-Wallet/1.0 (+https://naijasale.com)",
    }


def _credit_wallet_atomically(reference, verified_amount_ngn, gateway_ref=""):
    """
    Idempotent, database-row-locked wallet credit.
    Guarantees a Paystack reference can NEVER credit a user's balance twice,
    even under simultaneous webhook + callback race conditions.
    """
    with transaction.atomic():
        tx = (
            WalletTransaction.objects.select_for_update()
            .filter(reference=reference, tx_type="DEPOSIT")
            .first()
        )
        if not tx:
            return False, "Transaction reference not found."

        if tx.status == "SUCCESSFUL":
            mark_intent_converted(tx.user, intent_type="WALLET_TOPUP")
            return True, "Already credited."

        # Strict amount check (prevents underpayment tampering)
        if verified_amount_ngn < tx.amount:
            tx.status = "FAILED"
            tx.description = f"{tx.description} [Amount mismatch: paid ₦{verified_amount_ngn}]"
            tx.save(update_fields=["status", "description"])
            return False, "Verified amount is less than expected deposit."

        wallet = UserWallet.objects.select_for_update().get(id=tx.wallet_id)
        if wallet.is_frozen:
            return False, "Wallet is currently frozen for security review."

        before = wallet.balance
        after = before + tx.amount

        wallet.balance = after
        wallet.total_deposited = wallet.total_deposited + tx.amount
        wallet.save(update_fields=["balance", "total_deposited", "updated_at"])

        tx.status = "SUCCESSFUL"
        tx.balance_before = before
        tx.balance_after = after
        tx.gateway_reference = str(gateway_ref or tx.gateway_reference)
        tx.completed_at = timezone.now()
        tx.save(
            update_fields=[
                "status",
                "balance_before",
                "balance_after",
                "gateway_reference",
                "completed_at",
            ]
        )

        SystemNotification.objects.create(
            recipient=tx.user,
            title="💰 Wallet Top-Up Confirmed",
            message=f"₦{tx.amount:,.2f} has been credited to your Naijasale Wallet. New balance: ₦{after:,.2f}.",
            link="/wallet/",
        )

        # Automatically clear any open WALLET_TOPUP lead for this user
        mark_intent_converted(tx.user, intent_type="WALLET_TOPUP")
        return True, "Wallet credited successfully."


def _verify_paystack_reference(reference):
    """Server-to-server verification directly against Paystack API."""
    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "").strip()
    if not secret_key or "placeholder" in secret_key:
        return False, Decimal("0.00"), ""

    req = urllib.request.Request(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=_paystack_headers(secret_key),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            body = json.loads(res.read().decode("utf-8"))
            data = body.get("data") or {}
            if (
                body.get("status") is True
                and data.get("status") == "success"
                and data.get("currency") == "NGN"
                and data.get("reference") == reference
            ):
                paid_ngn = Decimal(str(data.get("amount", 0))) / Decimal("100")
                gateway_id = str(data.get("id", ""))
                return True, paid_ngn, gateway_id
    except Exception:
        pass
    return False, Decimal("0.00"), ""


@login_required
def wallet_dashboard_view(request):
    wallet = UserWallet.get_or_create_wallet(request.user)
    transactions = WalletTransaction.objects.filter(user=request.user)[:30]
    active_listings = Listing.objects.filter(seller=request.user, status="active").order_by("-created_at")
    plans = PromotionPlan.objects.filter(is_active=True).order_by("price_ngn")

    return render(
        request,
        "marketplace/wallet.html",
        {
            "wallet": wallet,
            "transactions": transactions,
            "active_listings": active_listings,
            "plans": plans,
            "min_topup": int(MIN_TOPUP_NGN),
            "max_topup": int(MAX_TOPUP_NGN),
        },
    )


@login_required
@require_POST
def wallet_topup_init_view(request):
    wallet = UserWallet.get_or_create_wallet(request.user)
    if wallet.is_frozen:
        messages.error(request, "Your wallet is temporarily restricted. Please contact Naijasale Support.")
        return redirect("marketplace:wallet_dashboard")

    raw_amount = (request.POST.get("amount") or "").replace(",", "").strip()
    try:
        amount_ngn = Decimal(raw_amount).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        messages.error(request, "Please enter a valid Naira amount.")
        return redirect("marketplace:wallet_dashboard")

    if amount_ngn < MIN_TOPUP_NGN or amount_ngn > MAX_TOPUP_NGN:
        messages.error(
            request,
            f"Top-up amount must be between ₦{MIN_TOPUP_NGN:,.0f} and ₦{MAX_TOPUP_NGN:,.0f}.",
        )
        return redirect("marketplace:wallet_dashboard")

    unique_ref = f"NSW-{uuid.uuid4().hex[:12].upper()}"
    customer_email = request.user.email or f"{request.user.username}@naijasale.com"

    WalletTransaction.objects.create(
        reference=unique_ref,
        wallet=wallet,
        user=request.user,
        tx_type="DEPOSIT",
        status="PENDING",
        amount=amount_ngn,
        balance_before=wallet.balance,
        balance_after=wallet.balance,
        description=f"Paystack Wallet Top-Up (₦{amount_ngn:,.2f})",
        ip_address=_get_client_ip(request),
    )

    # Record checkout intent in case user drops off inside Paystack modal
    record_user_intent(
        user=request.user,
        intent_type="WALLET_TOPUP",
        plan_name="Paystack Wallet Top-Up",
        amount_ngn=amount_ngn,
        notes=f"Ref {unique_ref}",
    )

    paystack_key = getattr(settings, "PAYSTACK_SECRET_KEY", "").strip()
    if not paystack_key or "placeholder" in paystack_key:
        _credit_wallet_atomically(unique_ref, amount_ngn, gateway_ref="SANDBOX-TEST")
        messages.success(request, f"[Test Mode] ₦{amount_ngn:,.2f} added to your wallet!")
        return redirect("marketplace:wallet_dashboard")

    callback_url = request.build_absolute_uri("/wallet/topup/callback/")
    payload = {
        "email": customer_email,
        "amount": int(amount_ngn * 100),
        "currency": "NGN",
        "reference": unique_ref,
        "callback_url": callback_url,
        "metadata": {
            "purpose": "wallet_topup",
            "user_id": request.user.id,
            "username": request.user.username,
        },
    }

    req = urllib.request.Request(
        "https://api.paystack.co/transaction/initialize",
        data=json.dumps(payload).encode("utf-8"),
        headers=_paystack_headers(paystack_key),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            if res_data.get("status"):
                return redirect(res_data["data"]["authorization_url"])
            messages.error(request, f"Paystack error: {res_data.get('message', 'Unable to start payment.')}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        try:
            err_msg = json.loads(err_body).get("message", f"HTTP {e.code}")
        except Exception:
            err_msg = f"HTTP {e.code}: {e.reason}"
        messages.error(request, f"Paystack connection error: {err_msg}")
    except Exception as e:
        messages.error(request, f"Unable to reach Paystack right now: {e}")

    return redirect("marketplace:wallet_dashboard")


@login_required
def wallet_topup_callback_view(request):
    reference = (request.GET.get("reference") or request.GET.get("trxref") or "").strip()
    if not reference or not reference.startswith("NSW-"):
        return redirect("marketplace:wallet_dashboard")

    tx = WalletTransaction.objects.filter(reference=reference, user=request.user).first()
    if not tx:
        messages.error(request, "Invalid wallet transaction reference.")
        return redirect("marketplace:wallet_dashboard")

    if tx.status == "SUCCESSFUL":
        mark_intent_converted(request.user, intent_type="WALLET_TOPUP")
        messages.success(request, f"₦{tx.amount:,.2f} top-up confirmed!")
        return redirect("marketplace:wallet_dashboard")

    verified, paid_ngn, gateway_id = _verify_paystack_reference(reference)
    if verified:
        ok, msg = _credit_wallet_atomically(reference, paid_ngn, gateway_ref=gateway_id)
        if ok:
            messages.success(request, f"Payment verified! ₦{tx.amount:,.2f} credited to your wallet.")
        else:
            messages.error(request, msg)
    else:
        messages.warning(
            request,
            "Payment is still confirming with Paystack. Your balance will update automatically once confirmed.",
        )

    return redirect("marketplace:wallet_dashboard")


@csrf_exempt
@require_POST
def paystack_wallet_webhook_view(request):
    """
    Dedicated Paystack webhook endpoint for NSW- wallet deposits.
    Verifies HMAC-SHA512 cryptographic signature + server-to-server verification.
    """
    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "").strip().encode("utf-8")
    signature = request.headers.get("x-paystack-signature", "")

    if not secret_key or not signature:
        return HttpResponse(status=400)

    computed_hmac = hmac.new(secret_key, request.body, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(computed_hmac, signature):
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if payload.get("event") == "charge.success":
        data = payload.get("data") or {}
        reference = (data.get("reference") or "").strip()
        if reference.startswith("NSW-") and data.get("currency") == "NGN":
            verified, paid_ngn, gateway_id = _verify_paystack_reference(reference)
            if verified:
                _credit_wallet_atomically(reference, paid_ngn, gateway_ref=gateway_id)

    return HttpResponse(status=200)


@login_required
@require_POST
def wallet_boost_ad_view(request):
    """
    1-Click Ad Boost paid directly from UserWallet balance with strict row locking.
    """
    listing_id = request.POST.get("listing_id")
    plan_id = request.POST.get("plan_id")

    listing = get_object_or_404(Listing, id=listing_id, seller=request.user)
    plan = get_object_or_404(PromotionPlan, id=plan_id, is_active=True)
    cost = Decimal(str(plan.price_ngn)).quantize(Decimal("0.01"))

    UserWallet.get_or_create_wallet(request.user)

    with transaction.atomic():
        wallet = UserWallet.objects.select_for_update().get(user=request.user)
        if wallet.is_frozen:
            messages.error(request, "Your wallet is currently restricted. Contact support.")
            return redirect("marketplace:wallet_dashboard")

        if wallet.balance < cost:
            record_user_intent(
                user=request.user,
                intent_type="AD_BOOST",
                listing=listing,
                plan_name=f"{plan.name} ({plan.duration_days} Days)",
                amount_ngn=cost,
                notes="Stopped due to insufficient wallet balance",
            )
            messages.error(
                request,
                f"Insufficient wallet balance (₦{wallet.balance:,.2f}). Top up at least ₦{(cost - wallet.balance):,.2f} more.",
            )
            return redirect("marketplace:wallet_dashboard")

        before = wallet.balance
        after = before - cost

        wallet.balance = after
        wallet.total_spent = wallet.total_spent + cost
        wallet.save(update_fields=["balance", "total_spent", "updated_at"])

        spend_ref = f"NSW-BOOST-{uuid.uuid4().hex[:10].upper()}"
        WalletTransaction.objects.create(
            reference=spend_ref,
            wallet=wallet,
            user=request.user,
            tx_type="BOOST_SPEND",
            status="SUCCESSFUL",
            amount=cost,
            balance_before=before,
            balance_after=after,
            description=f"{plan.name} ({plan.duration_days}d) for '{listing.title[:45]}'",
            ip_address=_get_client_ip(request),
            completed_at=timezone.now(),
        )

        # Activate or extend listing boost cleanly
        now = timezone.now()
        base_time = (
            listing.featured_until
            if (listing.is_featured and listing.featured_until and listing.featured_until > now)
            else now
        )
        listing.is_featured = True
        listing.featured_until = base_time + timedelta(days=plan.duration_days)
        if plan.badge_type:
            listing.promotion_badge = plan.badge_type
        listing.save(update_fields=["is_featured", "featured_until", "promotion_badge"])

        SystemNotification.objects.create(
            recipient=request.user,
            title="🚀 Ad Boosted via Wallet",
            message=f"'{listing.title}' is now boosted ({plan.name}) for {plan.duration_days} days. Wallet balance: ₦{after:,.2f}.",
            link=f"/item/{listing.slug}/",
        )

        # Clear any open AD_BOOST lead for this user/listing
        mark_intent_converted(request.user, intent_type="AD_BOOST", listing=listing)

    messages.success(
        request,
        f"Success! '{listing.title}' is now boosted for {plan.duration_days} days using your Wallet.",
    )
    return redirect("marketplace:listing_detail", slug=listing.slug)