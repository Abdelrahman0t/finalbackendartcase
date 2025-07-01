# serializers.py
from rest_framework import serializers
from .models import *
from .models import CustomUser
import os
import cloudinary
import cloudinary.uploader

from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

class ImageGenerationRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=255)
    scheduler = serializers.CharField(required=False, default="K_EULER")

    

from decimal import Decimal

class DesignSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    is_anonymous = serializers.SerializerMethodField()
    posts = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)  # Accept price from the frontend

    class Meta:
        model = Design
        fields = ["id", "image_url", "user", "is_anonymous", "stock", "modell", "type", "sku", "price", "theclass", "posts", "color1", "color2", "color3", 'created_at']

    def get_user(self, obj):
        """Handle both authenticated and anonymous designs"""
        if obj.user:
            return obj.user.username
        return "Anonymous"

    def get_is_anonymous(self, obj):
        """Return whether the design is anonymous (has no user)"""
        return obj.user is None

    def validate_price(self, value):
        """Ensure the price is non-negative."""   
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def get_posts(self, obj):
        posts = obj.posts.all()
        posts_data = PostSerializer(posts, many=True, context=self.context).data

        # Update stock field in the post data to a string representation
        for post_data in posts_data:
            post_data['stock'] = "In Stock" if obj.stock else "Out of Stock"

        return posts_data

    def get_stock(self, obj):
        # Convert the stock field to a human-readable string for the design itself
        return "In Stock" if obj.stock else "Out of Stock"




 
        
class PostSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    profile_pic = serializers.CharField(source='user.profile_pic', read_only=True)
    hashtags = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    hashtag_names = serializers.SerializerMethodField(read_only=True)
    
    # Add complete user information
    user_details = serializers.SerializerMethodField()
    # Add comments on the post
    comments = serializers.SerializerMethodField()
    # Add like and favorite status
    is_liked = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    design = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)
    favorite_count = serializers.IntegerField(source='favorites.count', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'design', 'caption', 'description', 'user', 'user_id',
            'created_at', 'like_count', 'comment_count', 'favorite_count',
            'first_name', 'profile_pic', 'hashtags', 'hashtag_names',
            'user_details', 'comments', 'is_liked', 'is_favorited'
        ]

    def get_hashtag_names(self, obj):
        """Return hashtag names for read operations"""
        return [hashtag.name for hashtag in obj.hashtags.all()]

    def get_user_details(self, obj):
        """Return complete user information"""
        user = obj.user
        if user:
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile_pic': user.profile_pic,
                'status': user.status,
                'is_staff': user.is_staff,
                'date_joined': user.date_joined,
                'last_login': user.last_login
            }
        return None

    def get_comments(self, obj):
        """Return all comments on the post"""
        comments = obj.comments.all().order_by('-created_at')
        return CommentSerializer(comments, many=True).data

    def get_is_liked(self, obj):
        """Check if the context user (as_user or request.user) has liked this post"""
        user = self.context.get('as_user')
        if not user:
            request = self.context.get('request')
            user = request.user if request and request.user.is_authenticated else None
        if user and user.is_authenticated:
            return obj.likes.filter(user=user).exists()
        return False

    def get_is_favorited(self, obj):
        """Check if the context user (as_user or request.user) has favorited this post"""
        user = self.context.get('as_user')
        if not user:
            request = self.context.get('request')
            user = request.user if request and request.user.is_authenticated else None
        if user and user.is_authenticated:
            return obj.favorites.filter(user=user).exists()
        return False

    def create(self, validated_data):
        hashtags_data = validated_data.pop('hashtags', [])
        post = Post.objects.create(**validated_data)
        
        # Process hashtags (limit to 5)
        for tag in hashtags_data[:5]:
            if tag and len(tag.strip()) > 0:
                hashtag_obj, created = Hashtag.objects.get_or_create(name=tag.strip())
                post.hashtags.add(hashtag_obj)
        
        return post

    def get_design(self, obj):
        """
        Prepares the design data for serialization and applies discounts for eligible users.
        """
        request = self.context.get('request')  # Get the request from the context
        user = request.user if request else None  # Get the authenticated user

        # Default price
        price = obj.design.price

        # Apply discount for eligible users only if the design is not their own  

        stock_status = "In Stock" if obj.design.stock else "Out of Stock" 

        return {
            'id': obj.design.id,
            'image_url': obj.design.image_url,
            'stock': stock_status,  # String representation of stock
            'modell': obj.design.modell,
            'type': obj.design.type,
            'sku': obj.design.sku,
            'price': str(price),  # Return price as string
            'theclass': obj.design.theclass,
            'color1': obj.design.color1,
            'color2': obj.design.color2,
            'color3': obj.design.color3
        }



 
class OrderItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='product_id')
    image = serializers.URLField(source='image_url')  # For output: maps 'image_url' to 'image'
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'image', 'price', 'type', 'modell', 'quantity']
    
    def create(self, validated_data):
        # Map 'image' from frontend to 'image_url' for the model
        if 'image' in validated_data:
            validated_data['image_url'] = validated_data.pop('image')
        return super().create(validated_data)

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'city', 
            'country', 'status', 'created_at', 'items'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order




class NotificationSerializer(serializers.ModelSerializer):
    action_user = serializers.CharField(source='action_user.username', read_only=True)
    action_user_profile_pic = serializers.CharField(source='action_user.profile_pic', read_only=True)
    design_image_url = serializers.CharField(source='design.image_url', read_only=True)
    relative_time = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'message', 'notification_type', 'created_at', 'relative_time', 'is_read', 'action_user', 'action_user_profile_pic', 'design_image_url']

    def get_relative_time(self, obj):
        """Return relative time like '1 day ago', '2 hours ago', etc."""
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            if diff.days == 1:
                return "1 day ago"
            else:
                return f"{diff.days} days ago"
        elif diff.seconds >= 3600:  # More than 1 hour
            hours = diff.seconds // 3600
            if hours == 1:
                return "1 hour ago"
            else:
                return f"{hours} hours ago"
        elif diff.seconds >= 60:  # More than 1 minute
            minutes = diff.seconds // 60
            if minutes == 1:
                return "1 minute ago"
            else:
                return f"{minutes} minutes ago"
        else:
            return "Just now"



class ChartSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    design = serializers.SerializerMethodField()

    class Meta:
        model = Chart
        fields = ['id', 'design', 'added_at', 'user', 'price']  # Include the price field

    def get_design(self, obj):
        stock_status = "In Stock" if obj.design.stock else "Out of Stock"
        return {
            'id': obj.design.id,
            "image_url": obj.design.image_url,
            "stock": stock_status,
            "modell": obj.design.modell,
            "type": obj.design.type,
            "sku": obj.design.sku,
            'price' : obj.design.price   
        }



class LikeSerializer(serializers.ModelSerializer):
    # Include the like count (number of likes on the post) in the serializer
    post_like_count = serializers.IntegerField(source='post.likes.count', read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'created_at', 'post_like_count']


class CommentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')  # Get user ID
    username = serializers.CharField(source='user.username')  # Get username
    profile_pic = serializers.CharField(source='user.profile_pic')  # Get username
    first_name = serializers.CharField(source='user.first_name')  # Get username


    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_at', 'user_id', 'username',"profile_pic",'first_name']


class FavoriteSerializer(serializers.ModelSerializer):
    # Include the favorite count (number of favorites on the post) in the serializer
    post_favorite_count = serializers.IntegerField(source='post.favorites.count', read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'post', 'created_at', 'post_favorite_count']




       







from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'profile_pic', 'is_staff', 'status']
        extra_kwargs = {
            'password': {'write_only': True},  # Hide password in responses
            'is_staff': {'write_only': True}  # Hide is_staff in responses
        }

    def validate_password(self, value):
        """Ensure the password is at least 6 characters long."""
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long.")
        return value

    def create(self, validated_data):
        profile_pic_url = validated_data.pop('profile_pic', None)  

        # Set default profile picture if none is provided
        if not profile_pic_url:
            profile_pic_url = 'https://res.cloudinary.com/daalfrqob/image/upload/v1730076406/default-avatar-profile-trendy-style-social-media-user-icon-187599373_jtpxbk.webp'

        validated_data['profile_pic'] = profile_pic_url

        # Set is_staff to True for admin user
        if validated_data.get('username') == 'admin':
            validated_data['is_staff'] = True

        # Create the user (Django will automatically hash the password)
        return CustomUser.objects.create_user(**validated_data)




class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']

class ReportSerializer(serializers.ModelSerializer):
    reported_by = serializers.CharField(source='reported_by.username', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'content_id', 'content_type', 'reason', 'status', 
                 'reported_by', 'created_at']
        read_only_fields = ['id', 'reported_by', 'created_at']

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'priority', 'status', 'publish_date', 
                 'created_at', 'updated_at', 'type', 'image_url', 'position']
        read_only_fields = ['created_at', 'updated_at', 'position']

class PhoneProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneProduct
        fields = ['id', 'type', 'modell', 'stock', 'price', 'url']
