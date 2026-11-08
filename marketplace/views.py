import base64
import random
import uuid
import urllib.parse
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Q, F, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from .models import (
    SiteSetting, StaticPage, Category, SubCategory, State, Area, Listing, 
    ListingImage, SellerProfile, Favorite, Conversation, Message,
    ReportedListing, SellerReview
)
from .forms import (
    UserRegisterForm, ListingForm, ProfileUpdateForm, 
    ReportListingForm, SellerReviewForm
)


def index_view(request):
    site_settings = SiteSetting.objects.first()
    if not site_settings:
        site_settings = SiteSetting.objects.create()

    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '')
    selected_subcategory = request.GET.get('subcategory', '')
    selected_state = request.GET.get('state', '')
    selected_condition = request.GET.get('condition', '')

    listings_queryset = Listing.objects.filter(status='active').select_related(
        'seller', 'seller__seller_profile', 'category', 'subcategory', 'state', 'area'
    ).prefetch_related('images').order_by('-is_featured', '-created_at')

    if search_query:
        listings_queryset = listings_queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(area__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    if selected_category:
        listings_queryset = listings_queryset.filter(category__slug=selected_category)

    if selected_subcategory:
        listings_queryset = listings_queryset.filter(subcategory__slug=selected_subcategory)

    selected_state_obj = None
    if selected_state:
        listings_queryset = listings_queryset.filter(state__slug=selected_state)
        selected_state_obj = State.objects.filter(slug=selected_state).first()

    if selected_condition:
        listings_queryset = listings_queryset.filter(condition=selected_condition)

    paginator = Paginator(listings_queryset, 20)
    page_number = request.GET.get('page', 1)

    try:
        listings = paginator.page(page_number)
    except PageNotAnInteger:
        listings = paginator.page(1)
    except EmptyPage:
        listings = paginator.page(paginator.num_pages)

    try:
        categories = Category.objects.annotate(
            total_ads=Count('listings', filter=Q(listings__status='active'))
        ).prefetch_related('subcategories').order_by('order', 'name')
        list(categories)
    except Exception:
        categories = Category.objects.annotate(
            total_ads=Count('listing', filter=Q(listing__status='active'))
        ).prefetch_related('subcategories').order_by('order', 'name')

    try:
        states_with_counts = State.objects.filter(is_active=True).annotate(
            total_ads=Count('listing', filter=Q(listing__status='active'))
        ).order_by('name')
        list(states_with_counts)
    except Exception:
        states_with_counts = State.objects.filter(is_active=True).annotate(
            total_ads=Count('listings', filter=Q(listings__status='active'))
        ).order_by('name')

    current_profile = None
    user_saved_ids = []
    unread_messages_count = 0
    if request.user.is_authenticated:
        if not (request.user.is_staff or request.user.is_superuser):
            current_profile, _ = SellerProfile.objects.get_or_create(
                user=request.user,
                defaults={'phone_number': '08000000000'}
            )
        user_saved_ids = list(Favorite.objects.filter(user=request.user).values_list('listing_id', flat=True))
        unread_messages_count = Message.objects.filter(
            Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
            is_read=False
        ).exclude(sender=request.user).count()

    context = {
        'settings': site_settings,
        'listings': listings,
        'page_obj': listings,
        'categories': categories,
        'states': states_with_counts,
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_subcategory': selected_subcategory,
        'selected_state': selected_state,
        'selected_state_obj': selected_state_obj,
        'selected_condition': selected_condition,
        'current_profile': current_profile,
        'user_saved_ids': user_saved_ids,
        'unread_messages_count': unread_messages_count,
        'total_nigeria_ads': Listing.objects.filter(status='active').count(),
    }
    return render(request, 'marketplace/index.html', context)


def listing_detail_view(request, slug):
    site_settings = SiteSetting.objects.first()
    if not site_settings:
        site_settings = SiteSetting.objects.create()

    listing = get_object_or_404(
        Listing.objects.select_related(
            'seller', 'seller__seller_profile', 'category', 'subcategory', 'state', 'area'
        ).prefetch_related('images'),
        slug=slug
    )
    
    session_key = f'viewed_ad_{listing.id}'
    if not request.session.get(session_key, False):
        Listing.objects.filter(pk=listing.pk).update(views_count=F('views_count') + 1)
        listing.refresh_from_db(fields=['views_count'])
        request.session[session_key] = True
        request.session.set_expiry(86400)
    
    similar_qs = Listing.objects.filter(
        status='active'
    ).exclude(id=listing.id).select_related(
        'seller', 'seller__seller_profile', 'area', 'state'
    ).prefetch_related('images')

    if listing.subcategory:
        related_items = list(similar_qs.filter(subcategory=listing.subcategory)[:6])
    else:
        related_items = list(similar_qs.filter(category=listing.category)[:6])

    if len(related_items) < 4:
        existing_ids = [item.id for item in related_items] + [listing.id]
        fallback_items = similar_qs.filter(
            category=listing.category
        ).exclude(id__in=existing_ids)[: (6 - len(related_items))]
        related_items.extend(fallback_items)

    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, listing=listing).exists()

    report_form = ReportListingForm()
    review_form = SellerReviewForm()
    seller_reviews = SellerReview.objects.filter(seller=listing.seller).select_related('reviewer')[:5]

    return render(request, 'marketplace/listing_detail.html', {
        'settings': site_settings,
        'listing': listing,
        'related_items': related_items,
        'is_favorited': is_favorited,
        'report_form': report_form,
        'review_form': review_form,
        'seller_reviews': seller_reviews,
    })


@login_required(login_url='marketplace:login')
def toggle_favorite_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    fav = Favorite.objects.filter(user=request.user, listing=listing)
    if fav.exists():
        fav.delete()
        messages.info(request, "Item removed from your saved list.")
    else:
        Favorite.objects.create(user=request.user, listing=listing)
        messages.success(request, "Item saved to your favorites!")
    
    next_url = request.META.get('HTTP_REFERER', 'marketplace:home')
    return redirect(next_url)


@login_required(login_url='marketplace:login')
def saved_items_view(request):
    favorites = Favorite.objects.filter(user=request.user).select_related(
        'listing', 'listing__seller', 'listing__seller__seller_profile', 'listing__state', 'listing__area'
    ).prefetch_related('listing__images')
    return render(request, 'marketplace/saved_items.html', {'favorites': favorites})


@login_required(login_url='marketplace:login')
def dashboard_view(request):
    if request.user.is_staff or request.user.is_superuser:
        messages.warning(request, "Staff accounts must use the Staff Workspace.")
        return redirect('workspace:dashboard')

    user_listings = Listing.objects.filter(seller=request.user).order_by('-created_at')
    active_count = user_listings.filter(status='active').count()
    pending_count = user_listings.filter(status='pending').count()
    sold_count = user_listings.filter(status='sold').count()
    total_views = sum(item.views_count for item in user_listings)

    return render(request, 'marketplace/dashboard.html', {
        'user_listings': user_listings,
        'active_count': active_count,
        'pending_count': pending_count,
        'sold_count': sold_count,
        'total_views': total_views,
    })


@login_required(login_url='marketplace:login')
def edit_listing_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, seller=request.user)
    if request.method == 'POST':
        form = ListingForm(request.POST, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{listing.title}' updated successfully!")
            return redirect('marketplace:dashboard')
    else:
        form = ListingForm(instance=listing)
    return render(request, 'marketplace/edit_listing.html', {'form': form, 'listing': listing})


@login_required(login_url='marketplace:login')
def mark_sold_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, seller=request.user)
    listing.status = 'sold'
    listing.save()
    messages.success(request, f"'{listing.title}' marked as Sold!")
    return redirect('marketplace:dashboard')


@login_required(login_url='marketplace:login')
def delete_listing_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, seller=request.user)
    listing.delete()
    messages.info(request, "Listing deleted permanently.")
    return redirect('marketplace:dashboard')


@login_required(login_url='marketplace:login')
def start_chat_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    if listing.seller == request.user:
        messages.warning(request, "You cannot message yourself about your own listing.")
        return redirect('marketplace:listing_detail', slug=listing.slug)

    conversation, _ = Conversation.objects.get_or_create(
        listing=listing,
        buyer=request.user,
        defaults={'seller': listing.seller}
    )
    return redirect('marketplace:chat_detail', conversation_id=conversation.id)


@login_required(login_url='marketplace:login')
def inbox_view(request):
    raw_conversations = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).select_related(
        'listing', 'buyer', 'seller', 
        'buyer__seller_profile', 'seller__seller_profile'
    ).prefetch_related('messages').order_by('-updated_at')

    conversations_data = []
    for conv in raw_conversations:
        other_user = conv.seller if request.user == conv.buyer else conv.buyer
        other_profile = getattr(other_user, 'seller_profile', None)
        last_message = conv.messages.order_by('-created_at').first()
        unread_for_this = conv.messages.filter(is_read=False).exclude(sender=request.user).count()

        conversations_data.append({
            'conversation': conv,
            'other_user': other_user,
            'other_profile': other_profile,
            'last_message': last_message,
            'unread_count': unread_for_this,
        })

    return render(request, 'marketplace/inbox.html', {
        'conversations_data': conversations_data,
    })


@login_required(login_url='marketplace:login')
def delete_conversation_view(request, conversation_id):
    conv = get_object_or_404(
        Conversation,
        Q(buyer=request.user) | Q(seller=request.user),
        id=conversation_id
    )
    if request.method == 'POST':
        conv.delete()
        messages.info(request, "Conversation deleted successfully.")
        return redirect('marketplace:inbox')
    return redirect('marketplace:chat_detail', conversation_id=conv.id)


@login_required(login_url='marketplace:login')
def delete_message_view(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    conversation_id = message.conversation_id
    message.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message_id': message_id})
    
    return redirect('marketplace:chat_detail', conversation_id=conversation_id)


@login_required(login_url='marketplace:login')
def typing_status_api_view(request, conversation_id):
    conv = get_object_or_404(
        Conversation,
        Q(buyer=request.user) | Q(seller=request.user),
        id=conversation_id
    )
    other_user = conv.seller if request.user == conv.buyer else conv.buyer

    if request.method == 'POST':
        is_typing = request.POST.get('typing') == 'true'
        cache_key = f"chat_typing_{conv.id}_{request.user.id}"
        if is_typing:
            cache.set(cache_key, True, timeout=4)
        else:
            cache.delete(cache_key)
        return JsonResponse({'status': 'ok'})

    other_typing_key = f"chat_typing_{conv.id}_{other_user.id}"
    is_other_typing = bool(cache.get(other_typing_key, False))
    return JsonResponse({
        'is_typing': is_other_typing,
        'other_username': other_user.username,
        'other_name': other_user.first_name or other_user.username
    })


@login_required(login_url='marketplace:login')
def chat_detail_view(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.select_related(
            'listing', 'buyer', 'seller', 
            'seller__seller_profile', 'buyer__seller_profile'
        ),
        id=conversation_id
    )

    if request.user not in [conversation.buyer, conversation.seller]:
        messages.error(request, "You do not have access to this conversation.")
        return redirect('marketplace:inbox')

    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    other_user = conversation.seller if request.user == conversation.buyer else conversation.buyer
    other_profile = getattr(other_user, 'seller_profile', None)

    # -------------------------------------------------------------
    # BUILD AUTOMATED WHATSAPP NOTIFICATION LINK FOR SELLER
    # -------------------------------------------------------------
    whatsapp_ping_url = None
    if request.user == conversation.buyer and conversation.seller:
        seller_prof = getattr(conversation.seller, 'seller_profile', None)
        raw_phone = ''
        if seller_prof:
            raw_phone = seller_prof.whatsapp_number or seller_prof.phone_number or ''
        
        # Clean up the phone number (turn 080... or +234... into 23480...)
        clean_phone = ''.join(ch for ch in str(raw_phone) if ch.isdigit())
        if clean_phone.startswith('0') and len(clean_phone) == 11:
            clean_phone = '234' + clean_phone[1:]
        elif clean_phone.startswith('234'):
            pass  # Already in international format
        
        if clean_phone:
            chat_link = request.build_absolute_uri(request.path)
            listing_title = conversation.listing.title if conversation.listing else "your listing"
            seller_name = conversation.seller.first_name or conversation.seller.username

            alert_text = (
                f"Hello {seller_name}! 👋\n\n"
                f"I just sent you a direct message on Naijasale regarding '*{listing_title}*'.\n\n"
                f"💬 Please view and reply to my message in your Naijasale inbox here:\n"
                f"{chat_link}"
            )
            encoded_text = urllib.parse.quote(alert_text)
            whatsapp_ping_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"

    if request.method == 'POST':
        action = request.POST.get('action', 'send_message')
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('is_ajax') == 'true'

        if action == 'make_offer':
            offer_raw = request.POST.get('offer_amount', '').strip().replace(',', '')
            note = request.POST.get('note', '').strip()
            
            try:
                offer_amount = Decimal(offer_raw)
                if offer_amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Please enter a valid offer amount.'}, status=400)
                messages.error(request, "Please enter a valid offer amount in Naira.")
                return redirect('marketplace:chat_detail', conversation_id=conversation.id)

            offer_text = note if note else f"Offered ₦{offer_amount:,.2f} for this item."
            new_msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=offer_text,
                msg_type='offer',
                offer_amount=offer_amount,
                offer_status='pending'
            )
            conversation.save()

            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message_id': new_msg.id,
                    'text': new_msg.text,
                    'msg_type': new_msg.msg_type,
                    'offer_amount': str(new_msg.offer_amount),
                    'offer_status': new_msg.offer_status,
                    'sender': new_msg.sender.username,
                    'is_me': True,
                    'created_at': new_msg.created_at.strftime('%H:%M'),
                    'whatsapp_ping_url': whatsapp_ping_url,
                })
            messages.success(request, f"Offer of ₦{offer_amount:,.2f} sent!")
            return redirect(f"{request.path}?sent=1")

        else:
            message_text = request.POST.get('message', '').strip()
            if message_text:
                new_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    text=message_text,
                    msg_type='text'
                )
                conversation.save()

                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message_id': new_msg.id,
                        'text': new_msg.text,
                        'msg_type': new_msg.msg_type,
                        'sender': new_msg.sender.username,
                        'is_me': True,
                        'created_at': new_msg.created_at.strftime('%H:%M'),
                        'whatsapp_ping_url': whatsapp_ping_url,
                    })
                return redirect(f"{request.path}?sent=1")

            elif is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Message cannot be empty.'}, status=400)

            return redirect('marketplace:chat_detail', conversation_id=conversation.id)

    chat_messages = conversation.messages.all().select_related('sender')
    last_offer = conversation.messages.filter(msg_type='offer').order_by('-created_at').first()
    just_sent = (request.GET.get('sent') == '1')

    return render(request, 'marketplace/chat_detail.html', {
        'conversation': conversation,
        'other_user': other_user,
        'other_profile': other_profile,
        'chat_messages': chat_messages,
        'last_offer': last_offer,
        'whatsapp_ping_url': whatsapp_ping_url,
        'just_sent': just_sent,
    })


@login_required(login_url='marketplace:login')
def chat_api_messages_view(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user not in [conversation.buyer, conversation.seller]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    last_id = request.GET.get('last_id', 0)
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    new_messages = conversation.messages.filter(id__gt=last_id).select_related('sender').order_by('created_at')
    new_messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    data = []
    for msg in new_messages:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'is_me': (msg.sender == request.user),
            'text': msg.text,
            'msg_type': msg.msg_type,
            'offer_amount': f"{msg.offer_amount:,.2f}" if msg.offer_amount else None,
            'offer_status': msg.offer_status,
            'created_at': msg.created_at.strftime('%H:%M'),
        })

    return JsonResponse({'messages': data})


@login_required(login_url='marketplace:login')
def respond_offer_view(request, message_id):
    message = get_object_or_404(Message.objects.select_related('conversation', 'conversation__seller'), id=message_id)
    conversation = message.conversation

    if request.user != conversation.seller:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Only the seller can accept or decline offers.'}, status=403)
        messages.error(request, "Only the seller can respond to price offers.")
        return redirect('marketplace:chat_detail', conversation_id=conversation.id)

    if request.method == 'POST':
        action = request.POST.get('response')
        if action == 'accept':
            message.offer_status = 'accepted'
            message.save()
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=f"🤝 Offer of ₦{message.offer_amount:,.2f} ACCEPTED by seller!",
                msg_type='text'
            )
            conversation.save()
            msg_response = f"You accepted the offer of ₦{message.offer_amount:,.2f}."
        elif action == 'decline':
            message.offer_status = 'declined'
            message.save()
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=f"❌ Offer of ₦{message.offer_amount:,.2f} declined by seller.",
                msg_type='text'
            )
            conversation.save()
            msg_response = f"You declined the offer of ₦{message.offer_amount:,.2f}."
        else:
            return HttpResponseBadRequest("Invalid action.")

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'offer_status': message.offer_status, 'message': msg_response})

        messages.info(request, msg_response)

    return redirect('marketplace:chat_detail', conversation_id=conversation.id)


@login_required(login_url='marketplace:login')
def report_ad_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    if request.method == 'POST':
        form = ReportListingForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.listing = listing
            report.reported_by = request.user
            report.save()
            messages.success(request, "Your safety report was submitted successfully. Our trust & safety team will review it shortly.")
        else:
            messages.error(request, "Please choose a valid reason for reporting this listing.")
    return redirect('marketplace:listing_detail', slug=listing.slug)


@login_required(login_url='marketplace:login')
def post_ad_view(request):
    if request.user.is_staff or request.user.is_superuser:
        messages.warning(request, "Staff accounts cannot post marketplace ads.")
        return redirect('workspace:dashboard')

    if request.method == 'POST':
        form = ListingForm(request.POST)
        files = request.FILES.getlist('images')

        if not files:
            messages.error(request, "Please upload at least one image of your item or job opportunity.")
        elif form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.status = 'pending'
            listing.save()

            for idx, uploaded_file in enumerate(files):
                ListingImage.objects.create(
                    listing=listing,
                    image=uploaded_file,
                    is_cover=(idx == 0)
                )

            messages.info(
                request, 
                "Your ad has been submitted successfully and is currently under review. "
                "Our moderation team will verify the details and activate it shortly to ensure platform quality and buyer safety."
            )
            return redirect('marketplace:dashboard')
    else:
        form = ListingForm()

    return render(request, 'marketplace/post_ad.html', {'form': form})


# ==========================================
# REGISTRATION WITH 6-DIGIT EMAIL OTP & ADMIN AUTO-INBOX
# ==========================================
def send_otp_email(user_email, otp):
    subject = f"{otp} is your Naijasale verification code"
    html_content = render_to_string('marketplace/emails/otp_email.html', {'otp_code': otp})
    msg = EmailMultiAlternatives(
        subject,
        f"Your verification code is: {otp}",
        settings.DEFAULT_FROM_EMAIL,
        [user_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower().strip()
            full_name = form.cleaned_data['full_name'].strip()
            password = form.cleaned_data['password']
            phone = form.cleaned_data.get('phone_number') or '08000000000'

            otp_code = f"{random.randint(100000, 999999)}"

            request.session['reg_user'] = {
                'email': email,
                'full_name': full_name,
                'password': password,
                'phone': phone,
                'otp': otp_code,
            }

            try:
                send_otp_email(email, otp_code)
            except Exception:
                messages.error(request, "Failed to send verification email. Please check your address or try again.")
                return render(request, 'marketplace/register.html', {'form': form})

            return redirect('marketplace:verify_email')
    else:
        form = UserRegisterForm()

    return render(request, 'marketplace/register.html', {'form': form})


def verify_email_view(request):
    reg_data = request.session.get('reg_user')
    if not reg_data:
        messages.warning(request, "Session expired or invalid. Please sign up again.")
        return redirect('marketplace:register')

    error = None
    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code', '').strip()

        if entered_otp == reg_data.get('otp'):
            email = reg_data['email']
            full_name = reg_data['full_name']
            password = reg_data['password']
            phone = reg_data['phone']

            user = User.objects.filter(username=email).first()
            if not user:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=full_name
                )
            else:
                user.set_password(password)
                user.first_name = full_name
                user.save()

            SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone_number': phone,
                    'whatsapp_number': phone
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
                            "Your email has been verified. You can now post ads for free or message sellers directly. "
                            "If you need any help, just reply here!"
                        )
                    )

            if 'reg_user' in request.session:
                del request.session['reg_user']
                
            login(request, user)
            messages.success(request, f"🎉 Welcome to Naijasale, {full_name}! Your account is verified. A welcome message has been sent to your Inbox.")
            return redirect('marketplace:home')
        else:
            error = "Invalid 6-digit code. Please check your email and try again."

    return render(request, 'marketplace/verify_email.html', {
        'email': reg_data.get('email'),
        'error': error
    })


def resend_otp_view(request):
    reg_data = request.session.get('reg_user')
    if not reg_data:
        return redirect('marketplace:register')

    otp_code = f"{random.randint(100000, 999999)}"
    reg_data['otp'] = otp_code
    request.session['reg_user'] = reg_data

    send_otp_email(reg_data['email'], otp_code)
    messages.info(request, "A new 6-digit verification code has been sent.")
    return redirect('marketplace:verify_email')


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('workspace:dashboard')
        return redirect('marketplace:home')

    error_message = None
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=identifier, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user:
            login(request, user)

            if user.is_staff or user.is_superuser:
                messages.success(request, f"Welcome to the Staff Workspace, {user.first_name or user.username}!")
                return redirect('workspace:dashboard')

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next', 'marketplace:home')
            return redirect(next_url)
        else:
            error_message = "Invalid email or password."

    return render(request, 'marketplace/login.html', {'error_message': error_message})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('marketplace:home')


@login_required(login_url='marketplace:login')
def profile_view(request):
    if request.user.is_staff or request.user.is_superuser:
        messages.warning(request, "Staff accounts cannot access seller profiles.")
        return redirect('workspace:dashboard')

    profile, _ = SellerProfile.objects.get_or_create(
        user=request.user,
        defaults={'phone_number': '08000000000'}
    )

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'submit_kyc':
            id_doc = request.FILES.get('id_document')
            selfie_b64 = request.POST.get('selfie_base64')

            has_id = bool(id_doc) or bool(profile.id_document)
            has_selfie = bool(selfie_b64) or bool(profile.selfie_image)

            if not has_id or not has_selfie:
                messages.error(request, "Both a valid NIN document and a live face selfie are required to submit for verification.")
                return redirect('marketplace:profile')

            if id_doc:
                profile.id_document = id_doc

            if selfie_b64 and ';base64,' in selfie_b64:
                format_str, img_str = selfie_b64.split(';base64,')
                ext = format_str.split('/')[-1]
                if ext == 'jpeg':
                    ext = 'jpg'
                file_name = f"selfie_{profile.user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                profile.selfie_image.save(file_name, ContentFile(base64.b64decode(img_str)), save=False)

            profile.verification_status = 'pending'
            profile.verification_submitted_at = timezone.now()
            profile.verification_feedback = None
            profile.save()

            messages.info(request, "Your KYC documents and biometric selfie have been submitted for review!")
            return redirect('marketplace:profile')

        else:
            form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Store profile details saved successfully!")
                return redirect('marketplace:profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'marketplace/profile.html', {
        'form': form,
        'profile': profile,
    })


def static_page_view(request, slug):
    site_settings = SiteSetting.objects.first()
    if not site_settings:
        site_settings = SiteSetting.objects.create()

    page = get_object_or_404(StaticPage, slug=slug)
    return render(request, 'marketplace/static_page.html', {
        'settings': site_settings,
        'page': page,
    })


def ajax_search_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        matches = Listing.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(area__name__icontains=query) |
            Q(category__name__icontains=query),
            status='active'
        ).select_related('area', 'state').prefetch_related('images')[:6]

        for item in matches:
            first_img = item.images.first()
            results.append({
                'title': item.title,
                'price': f"{item.price:,.2f}",
                'slug': item.slug,
                'location': item.area.name if item.area else (item.state.name if item.state else "Nigeria"),
                'image': first_img.image.url if first_img else None,
            })
    return JsonResponse({'results': results})


def get_areas_for_state_view(request):
    state_id = request.GET.get('state_id')
    areas = []
    if state_id:
        area_objs = Area.objects.filter(state_id=state_id).order_by('name')
        areas = [{'id': a.id, 'name': a.name} for a in area_objs]
    return JsonResponse({'areas': areas})


def get_subcategories_for_category_view(request):
    category_id = request.GET.get('category_id')
    subcategories = []
    category_slug = ""
    if category_id:
        cat_obj = Category.objects.filter(id=category_id).first()
        if cat_obj:
            category_slug = cat_obj.slug
        sub_objs = SubCategory.objects.filter(category_id=category_id).order_by('name')
        subcategories = [{'id': s.id, 'name': s.name} for s in sub_objs]
    return JsonResponse({'subcategories': subcategories, 'category_slug': category_slug})


@login_required(login_url='marketplace:login')
def unread_count_api_view(request):
    count = Message.objects.filter(
        Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
        is_read=False
    ).exclude(sender=request.user).count()
    return JsonResponse({'unread_count': count})