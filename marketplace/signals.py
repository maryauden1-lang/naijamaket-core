from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.account.signals import user_signed_up
from .models import SellerProfile, Conversation, Message


@receiver(user_signed_up)
def setup_google_user_profile(sender, request, user, **kwargs):
    """
    Automatically creates a SellerProfile and sends the welcome Inbox message
    whenever a visitor signs up using Google OAuth.
    """
    full_name = (user.first_name or user.get_full_name() or user.username or "Friend").strip()
    if not user.first_name and full_name:
        user.first_name = full_name
        user.save(update_fields=['first_name'])

    SellerProfile.objects.get_or_create(
        user=user,
        defaults={
            'phone_number': '08000000000',
            'whatsapp_number': '08000000000',
        }
    )

    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
    if admin_user and admin_user != user:
        welcome_conv, _ = Conversation.objects.get_or_create(
            listing=None,
            buyer=user,
            seller=admin_user
        )
        if not welcome_conv.messages.exists():
            Message.objects.create(
                conversation=welcome_conv,
                sender=admin_user,
                text=(
                    f"Hello {full_name}! 👋 Welcome to Naijasale.\n\n"
                    "Your Google account is connected and verified. You can now post ads for free or message sellers directly. "
                    "If you need any help, just reply here!"
                )
            )