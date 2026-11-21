from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse

from .models import (
    Listing,
    Message,
    SystemNotification,
    SellerProfile,
    ReportedListing,
)


def live_pulse_api_view(request):
    """
    Ultra-fast global heartbeat endpoint (< 2ms DB queries).
    Returns the latest IDs/counts so the frontend detects changes immediately
    and shows non-intrusive live toast notifications without page refresh.
    """
    # 1. Latest active listing on the marketplace (for all visitors)
    latest_active = (
        Listing.objects.filter(status='active')
        .order_by('-id')
        .values('id', 'title', 'slug')
        .first()
    )

    payload = {
        'authenticated': request.user.is_authenticated,
        'latest_listing_id': latest_active['id'] if latest_active else 0,
        'latest_listing_title': latest_active['title'] if latest_active else '',
        'latest_listing_url': (
            reverse('marketplace:listing_detail', kwargs={'slug': latest_active['slug']})
            if latest_active
            else ''
        ),
    }

    if not request.user.is_authenticated:
        return JsonResponse(payload)

    # 2. Staff & Superuser Moderation Queues
    if request.user.is_staff or request.user.is_superuser:
        pending_ads = Listing.objects.filter(status='pending').count()
        pending_kyc = SellerProfile.objects.filter(verification_status='pending').count()
        unresolved_reports = ReportedListing.objects.filter(is_resolved=False).count()

        payload.update({
            'is_staff': True,
            'pending_ads_count': pending_ads,
            'pending_kyc_count': pending_kyc,
            'unresolved_reports_count': unresolved_reports,
        })
        return JsonResponse(payload)

    # 3. Regular Buyer / Seller Live Alerts
    # A) Latest unread chat message or price offer
    latest_msg = (
        Message.objects.filter(
            Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
            is_read=False,
        )
        .exclude(sender=request.user)
        .select_related('sender', 'conversation')
        .order_by('-id')
        .first()
    )

    unread_msg_count = (
        Message.objects.filter(
            Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
            is_read=False,
        )
        .exclude(sender=request.user)
        .count()
    )

    # B) Latest unread official CEO / system notification
    latest_notif = (
        SystemNotification.objects.filter(recipient=request.user, is_read=False)
        .order_by('-id')
        .first()
    )

    # C) Seller's own approved ads count (detects instant approval while waiting)
    my_active_ads = Listing.objects.filter(seller=request.user, status='active').count()
    latest_my_approved = (
        Listing.objects.filter(seller=request.user, status='active')
        .order_by('-id')
        .values('id', 'title', 'slug')
        .first()
    )

    payload.update({
        'is_staff': False,
        'unread_msg_count': unread_msg_count,
        'latest_msg_id': latest_msg.id if latest_msg else 0,
        'latest_msg_sender': (
            (latest_msg.sender.first_name or latest_msg.sender.username)
            if latest_msg
            else ''
        ),
        'latest_msg_type': latest_msg.msg_type if latest_msg else 'text',
        'latest_msg_text': (latest_msg.text[:75] if latest_msg else ''),
        'latest_msg_url': (
            reverse('marketplace:chat_detail', kwargs={'conversation_id': latest_msg.conversation_id})
            if latest_msg
            else reverse('marketplace:inbox')
        ),
        'latest_notif_id': latest_notif.id if latest_notif else 0,
        'latest_notif_title': latest_notif.title if latest_notif else '',
        'latest_notif_message': (latest_notif.message[:85] if latest_notif else ''),
        'latest_notif_link': (latest_notif.link or '/dashboard/') if latest_notif else '/dashboard/',
        'my_active_ads_count': my_active_ads,
        'latest_my_approved_title': latest_my_approved['title'] if latest_my_approved else '',
        'latest_my_approved_url': (
            reverse('marketplace:listing_detail', kwargs={'slug': latest_my_approved['slug']})
            if latest_my_approved
            else '/dashboard/'
        ),
    })

    return JsonResponse(payload)