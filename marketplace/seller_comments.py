from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from .models import SellerComment

User = get_user_model()


def get_seller_comment_threads(seller):
    """
    Returns top-level comments for a seller with 1-level replies attached
    in memory using a single indexed query.
    """
    all_comments = list(
        SellerComment.objects.filter(seller=seller, is_hidden=False)
        .select_related("author", "parent", "parent__author")
        .order_by("-created_at")
    )

    replies_by_parent = {}
    top_level = []

    for comment in all_comments:
        if comment.parent_id:
            replies_by_parent.setdefault(comment.parent_id, []).append(comment)
        else:
            top_level.append(comment)

    for item in top_level:
        # Show replies oldest-to-newest under each comment for natural reading order
        item.thread_replies = list(reversed(replies_by_parent.get(item.id, [])))

    return top_level


@login_required
@require_POST
def post_seller_comment_view(request, seller_id):
    seller = get_object_or_404(User, id=seller_id)
    body = (request.POST.get("body") or "").strip()
    parent_id = request.POST.get("parent_id")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

    if not body:
        messages.error(request, "Please write a comment before posting.")
        return redirect(next_url)

    if len(body) > 600:
        messages.error(request, "Comment is too long (max 600 characters).")
        return redirect(next_url)

    parent_comment = None
    if parent_id:
        parent_comment = get_object_or_404(
            SellerComment,
            id=parent_id,
            seller=seller,
            is_hidden=False,
        )
        # Keep replies strictly 1 level deep so mobile threads stay clean
        if parent_comment.parent_id:
            parent_comment = parent_comment.parent

    SellerComment.objects.create(
        seller=seller,
        author=request.user,
        parent=parent_comment,
        body=body,
    )
    messages.success(
        request,
        "Your reply has been posted." if parent_comment else "Your comment has been posted.",
    )
    return redirect(next_url)


class SellerCommentDeleteView(View):
    @method_decorator(login_required)
    @method_decorator(require_POST)
    def post(self, request, comment_id):
        comment = get_object_or_404(SellerComment, id=comment_id)
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

        if request.user.id not in (comment.author_id, comment.seller_id) and not request.user.is_staff:
            messages.error(request, "You cannot remove this comment.")
            return redirect(next_url)

        comment.is_hidden = True
        comment.save(update_fields=["is_hidden"])
        messages.success(request, "Comment removed.")
        return redirect(next_url)