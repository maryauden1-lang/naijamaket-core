from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.template import loader
from django.core.mail import EmailMultiAlternatives
from . import views
from . import views_monetization

app_name = 'marketplace'


class NaijasalePasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = "Reset your Naijasale password"
        body = loader.render_to_string(email_template_name, context)
        
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")
        
        email_message.send()


urlpatterns = [
    path('', views.index_view, name='home'),
    path('item/<slug:slug>/', views.listing_detail_view, name='listing_detail'),
    path('favorite/<int:listing_id>/', views.toggle_favorite_view, name='toggle_favorite'),
    path('saved/', views.saved_items_view, name='saved_items'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/edit/<int:listing_id>/', views.edit_listing_view, name='edit_listing'),
    path('dashboard/mark-sold/<int:listing_id>/', views.mark_sold_view, name='mark_sold'),
    path('dashboard/delete/<int:listing_id>/', views.delete_listing_view, name='delete_listing'),
    path('chat/start/<int:listing_id>/', views.start_chat_view, name='start_chat'),
    path('inbox/', views.inbox_view, name='inbox'),
    path('chat/<int:conversation_id>/', views.chat_detail_view, name='chat_detail'),
    path('chat/<int:conversation_id>/delete/', views.delete_conversation_view, name='delete_conversation'),
    path('chat/message/<int:message_id>/delete/', views.delete_message_view, name='delete_message'),
    path('api/chat/<int:conversation_id>/messages/', views.chat_api_messages_view, name='chat_api_messages'),
    path('api/chat/<int:conversation_id>/typing/', views.typing_status_api_view, name='typing_status_api'),
    path('chat/offer/<int:message_id>/respond/', views.respond_offer_view, name='respond_offer'),
    path('report/<int:listing_id>/', views.report_ad_view, name='report_ad'),
    
    # Registration & OTP Verification
    path('register/', views.register_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('post-ad/', views.post_ad_view, name='post_ad'),
    
    # Static Policy Pages
    path('page/<slug:slug>/', views.static_page_view, name='static_page'),
    
    # AJAX Endpoints
    path('api/search/', views.ajax_search_view, name='ajax_search'),
    path('api/get-areas/', views.get_areas_for_state_view, name='get_areas'),
    path('api/get-subcategories/', views.get_subcategories_for_category_view, name='get_subcategories'),
    path('api/unread-count/', views.unread_count_api_view, name='unread_count_api'),

    # Monetization, Promotion & Gateway Routes
    path('promote/<int:listing_id>/', views_monetization.promote_listing_view, name='promote_listing'),
    path('payment/callback/', views_monetization.payment_callback_view, name='payment_callback'),
    path('webhook/paystack/', views_monetization.paystack_webhook, name='paystack_webhook'),
    path('webhook/flutterwave/', views_monetization.flutterwave_webhook, name='flutterwave_webhook'),

    # Password Reset Pipeline
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            form_class=NaijasalePasswordResetForm,
            template_name='marketplace/password_reset_form.html',
            email_template_name='marketplace/emails/password_reset_email.html',
            html_email_template_name='marketplace/emails/password_reset_email.html',
            success_url=reverse_lazy('marketplace:password_reset_done'),
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='marketplace/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='marketplace/password_reset_confirm.html',
            success_url=reverse_lazy('marketplace:password_reset_complete'),
        ),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='marketplace/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]