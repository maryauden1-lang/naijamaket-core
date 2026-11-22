import json
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

SUPPORT_CACHE_KEY = 'naijasale_support_threads_v1'
SUPPORT_TTL_SECONDS = 60 * 60 * 24 * 30  # Keep support history for 30 days


def _get_threads():
    return cache.get(SUPPORT_CACHE_KEY) or {}


def _save_threads(threads):
    # Keep at most 150 most recently updated conversations so cache stays tiny and fast
    if len(threads) > 150:
        sorted_items = sorted(
            threads.items(),
            key=lambda kv: kv[1].get('updated_at', 0),
            reverse=True,
        )[:150]
        threads = dict(sorted_items)
    cache.set(SUPPORT_CACHE_KEY, threads, timeout=SUPPORT_TTL_SECONDS)


def _get_visitor_identity(request):
    if request.user.is_authenticated:
        display_name = (
            request.user.get_full_name().strip()
            or request.user.username
            or f"User #{request.user.id}"
        )
        return (
            f"user_{request.user.id}",
            display_name,
            request.user.email or "Registered Member",
            True,
        )

    if not request.session.session_key:
        request.session.save()
    short_code = (request.session.session_key or "guest")[:6].upper()
    return (
        f"guest_{request.session.session_key}",
        f"Guest #{short_code}",
        "Unregistered Visitor",
        False,
    )


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def support_chat_api_view(request):
    """
    Standalone live support chat API for both unregistered guests and logged-in users.
    Staff/Superusers automatically get the multi-thread Support Desk view to reply live.
    """
    threads = _get_threads()
    is_staff = request.user.is_authenticated and (
        request.user.is_staff or request.user.is_superuser
    )

    # =========================================================
    # STAFF / ADMIN SUPPORT DESK MODE
    # =========================================================
    if is_staff:
        if request.method == "POST":
            try:
                body = json.loads(request.body.decode("utf-8"))
            except Exception:
                body = request.POST

            thread_id = (body.get("thread_id") or "").strip()
            text = (body.get("text") or "").strip()[:1000]
            action = (body.get("action") or "reply").strip()

            if thread_id in threads:
                if action == "mark_read":
                    threads[thread_id]["unread_by_staff"] = 0
                    _save_threads(threads)
                elif text:
                    now_ts = time.time()
                    threads[thread_id]["messages"].append({
                        "sender": "staff",
                        "sender_name": "Naijasale Support",
                        "text": text,
                        "time": timezone.localtime().strftime("%I:%M %p"),
                        "ts": now_ts,
                    })
                    threads[thread_id]["messages"] = threads[thread_id]["messages"][-60:]
                    threads[thread_id]["updated_at"] = now_ts
                    threads[thread_id]["unread_by_staff"] = 0
                    threads[thread_id]["unread_by_user"] = (
                        threads[thread_id].get("unread_by_user", 0) + 1
                    )
                    _save_threads(threads)

        # Return sorted list of all support threads for staff
        thread_list = sorted(
            threads.values(),
            key=lambda t: t.get("updated_at", 0),
            reverse=True,
        )
        total_unread = sum(t.get("unread_by_staff", 0) for t in thread_list)
        return JsonResponse({
            "role": "staff",
            "unread_count": total_unread,
            "threads": thread_list,
        })

    # =========================================================
    # CUSTOMER / GUEST VISITOR MODE
    # =========================================================
    thread_id, display_name, subtitle, is_registered = _get_visitor_identity(request)

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            body = request.POST

        action = (body.get("action") or "send").strip()

        if action == "mark_read":
            if thread_id in threads:
                threads[thread_id]["unread_by_user"] = 0
                _save_threads(threads)
        else:
            text = (body.get("text") or "").strip()[:1000]
            guest_contact = (body.get("contact") or "").strip()[:80]
            if text:
                now_ts = time.time()
                if thread_id not in threads:
                    threads[thread_id] = {
                        "thread_id": thread_id,
                        "name": display_name,
                        "subtitle": guest_contact or subtitle,
                        "is_registered": is_registered,
                        "updated_at": now_ts,
                        "unread_by_staff": 0,
                        "unread_by_user": 0,
                        "messages": [],
                    }
                elif guest_contact:
                    threads[thread_id]["subtitle"] = guest_contact

                threads[thread_id]["messages"].append({
                    "sender": "user",
                    "sender_name": display_name,
                    "text": text,
                    "time": timezone.localtime().strftime("%I:%M %p"),
                    "ts": now_ts,
                })
                threads[thread_id]["messages"] = threads[thread_id]["messages"][-60:]
                threads[thread_id]["updated_at"] = now_ts
                threads[thread_id]["unread_by_staff"] = (
                    threads[thread_id].get("unread_by_staff", 0) + 1
                )
                _save_threads(threads)

    current_thread = threads.get(thread_id) or {
        "thread_id": thread_id,
        "name": display_name,
        "subtitle": subtitle,
        "is_registered": is_registered,
        "unread_by_user": 0,
        "messages": [],
    }

    return JsonResponse({
        "role": "customer",
        "is_registered": is_registered,
        "visitor_name": display_name,
        "unread_count": current_thread.get("unread_by_user", 0),
        "messages": current_thread.get("messages", []),
    })