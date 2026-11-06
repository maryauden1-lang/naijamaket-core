from django.urls import path
from . import views

app_name = 'marketplace'

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
    path('api/chat/<int:conversation_id>/messages/', views.chat_api_messages_view, name='chat_api_messages'),
    path('chat/offer/<int:message_id>/respond/', views.respond_offer_view, name='respond_offer'),
    path('report/<int:listing_id>/', views.report_ad_view, name='report_ad'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('post-ad/', views.post_ad_view, name='post_ad'),
    
    # Static Policy Pages (Privacy Policy, Terms, etc.)
    path('page/<slug:slug>/', views.static_page_view, name='static_page'),
    
    # AJAX Endpoints
    path('api/search/', views.ajax_search_view, name='ajax_search'),
    path('api/get-areas/', views.get_areas_for_state_view, name='get_areas'),
    path('api/get-subcategories/', views.get_subcategories_for_category_view, name='get_subcategories'),
]