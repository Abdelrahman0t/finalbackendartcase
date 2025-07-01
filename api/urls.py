from django.urls import path
from .views import *
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)



urlpatterns = [
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/me/', get_thecurrent_user, name='adminDash'),
    path('api/all-orders/', all_orders_view, name='all_orders'),
    path('api/update-profile/', UserProfileView.as_view(), name='update-profile'),

    path('api/user/<int:user_id>/', get_user_details, name='get_user_details'),
    path('api/user/<int:user_id>/posts/', get_user_posts, name='user-posts'),
    path('api/user/<int:user_id>/posts/most-liked/', get_user_most_liked_posts, name='user-most-liked-posts'),
    path('api/user/<int:user_id>/posts/most-commented/', get_user_most_commented_posts, name='user-most-commented-posts'),
    path('api/designs/', DesignListView.as_view(), name='design-list'),
    path('api/designs/anonymous/', create_anonymous_design, name='create-anonymous-design'),
    path('api/designs/test-null-user/', test_create_null_user_design, name='test-create-null-user-design'),
    path('api/designs/associate/', associate_anonymous_design, name='associate-anonymous-design'),
    path('api/design/<int:designid>/', get_design_by_id, name='get_design_by_id'),
    path('api/design/<int:design_id>/update-user/', update_design_user, name='update_design_user'),
    path('api/design/<int:design_id>/test/', test_design_null_user, name='test_design_null_user'),
    path('api/register/', registerview),
    path('api/login/', registerview),
    path('api/profile/', profile_view, name='profile'),
    path('api/user-designs/', user_design_archive, name='profile'),

    path('api/posts/', posts, name='posts'),
    path('api/public-posts/', public_posts, name='posts'),
    path('api/posts/<int:post_id>/like/', toggle_like, name='toggle-like'),
    path('api/posts/<int:post_id>/favorite/', toggle_favorite, name='toggle-favorite'),
    path('api/posts/<int:post_id>/debug/', debug_likes_favorites, name='debug-likes-favorites'),
    path('api/posts/<int:post_id>/comment/', add_comment, name='add-comment'), 
    path('api/posts/<int:post_id>/comments/', get_comments, name='add-comment'),
    path('api/posts/most-liked-designs/', most_liked_designs, name='add-comment'),
    path('api/posts/most-added-to-cart-designs/', most_added_to_cart_designs, name='add-comment'),

  path('api/delete-like/<int:design_id>/', delete_like, name='delete_like'),
path('api/delete-fav/<int:design_id>/', delete_favorite, name='delete_favorite'),



    path('api/comments/<int:comment_id>/delete/', delete_comment, name='delete-comment'), 

 path('api/favorites/', user_favorites, name='user-favorites'),
 path('liked/', user_liked, name='user_liked'),  # Add this lin
 path('api/liked-posts/', user_liked_posts, name='user-liked-posts'),  # Get liked posts
 path('api/favorited-posts/', user_favorited_posts, name='user-favorited-posts'),  # Get favorited posts


    path('api/notifications/', get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/',mark_as_read, name='mark_as_read'),
    path('api/notifications/<int:notification_id>/delete/', delete_notification, name='delete_notification'),

    path('api/designsview/', test, name='send-design-to-printful'),     
    path('api/del/', get_templates, name='cancel_order_items'),



    path('api/cart/add/', add_to_cart, name='add-to-cart'),
    path('api/cart/view/', view_cart, name='view_cart'),
    path('api/cart/delete/<int:cart_id>/', delete_from_cart, name='delete_from_cart'),

 
 
    path('api/createOrder/', creatte_order, name='create-order'),
    path('cancelOrder/<int:order_id>/',  cancel_order, name='create-get_user_orders'),    
    path('api/orders/<int:order_id>/status/', update_order_status, name='update-order-status'),
    path('api/getOrder/', get_user_orders, name='create-get_user_orders'),

 
   
    path('api/test-order/', TestOrderView.as_view(), name='test_order'),
    path('api/create-product/', create_product_view, name='create-product'),
      
    path('api/users/', user_list, name='user-list'),  # List all users  
    path('api/users/<int:id>/', user_detail, name='user-detail'),  # Get user by ID
    path('api/users/<int:user_id>/posts/', get_user_posts, name='user-posts'), 
    path('api/user-posts/', user_posts, name='user-posts-authenticated'),  # Get posts for authenticated user



    path('search_posts/', search, name='search_posts'),
    path('stickers/', fetch_stickers, name='search_posts'),
    path('emoji/', fetch_emoji, name='search_posts'),

    path('top-users-by-likes/', top_users_by_likes, name='top-users-by-likes'),
    path('top-users-by-posts/', top_users_by_posts, name='top-users-by-posts'),

    path('designs/<int:design_id>/delete/', delete_design, name='delete_design'),
    path('posts/<int:post_id>/delete/', delete_post, name='delete_post'),
 path('recent-posts/', recent_posts, name='recent-posts'),
 path('posts/<int:id>/', get_post_by_id, name='get-post-by-id'),

    path('api/reports/', reports_view, name='reports'),
    path('api/reports/<int:report_id>/status/', update_report_status, name='update-report-status'),
    path('api/announcements/', announcements_view, name='announcements'),
    path('api/announcements/<int:announcement_id>/delete/', delete_announcement, name='delete_announcement'),
    path('api/announcements/<int:announcement_id>/position/', update_announcement_position, name='update_announcement_position'),
    path('api/admin/analytics/', admin_analytics, name='admin-analytics'),

    path('api/phone-products/', phone_products, name='phone-products'),
    path('api/phone-products/<int:product_id>/', phone_product_detail, name='phone-product-detail'),

    path('api/users/<int:user_id>/status/', update_user_status, name='update_user_status'),
    path('api/posts/all/', get_all_posts, name='get_all_posts'),
    path('api/checkout_order/', checkout_order, name='checkout_order'),

    path('api/associate_orders/', associate_orders, name='associate_orders'),
    path('api/orders/history/', user_order_history, name='user_order_history'),
    path('api/orders/debug/', test_orders_debug, name='test_orders_debug'),
]    