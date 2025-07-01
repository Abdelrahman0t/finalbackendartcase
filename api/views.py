from rest_framework import generics,viewsets
from rest_framework.response import Response
from rest_framework import status,permissions
from .models import *
from .serializers import *
import os
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.conf import settings
import requests
from rest_framework.views import APIView
from rest_framework.decorators import api_view ,permission_classes
import logging
from decouple import config
import cloudinary.uploader
from rest_framework.permissions import IsAuthenticated, AllowAny
from decimal import Decimal
# Set up logging
logger = logging.getLogger(__name__)
from django.views.decorators.csrf import csrf_exempt
import json
import io
import base64
from django.db.models import Count, Sum, Avg, FloatField, F, ExpressionWrapper, Value, DecimalField, Subquery, OuterRef, IntegerField
from django.db.models import Q
from django.utils import timezone
from django.db.models.functions import TruncDate, ExtractHour, ExtractDay, Cast, Coalesce
from PIL import Image
from io import BytesIO
from cloudinary.uploader import upload
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound
from rest_framework_simplejwt.views import TokenObtainPairView

from api.clip_classifier import classify_design  # Import the classification function


class DesignListView(generics.ListCreateAPIView):
    queryset = Design.objects.all()
    serializer_class = DesignSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        stock = self.request.data.get('stock', True)  # Default to True if no stock is provided
        price = self.request.data.get('price')  # Get the price from the request

        if price is None:
            raise serializers.ValidationError("Price is required.")

        try:
            price = Decimal(price)
            if price < 0:
                raise serializers.ValidationError("Price cannot be negative.")
        except Exception:
            raise serializers.ValidationError("Invalid price format.")

        # Save the design with the user, stock, and price
        design = serializer.save(user=self.request.user, stock=stock, price=price)

        try:
            classification = classify_design(design)  # Now returns a dict
            design.theclass = classification.get('category', 'unknown')
            design.color1 = classification.get('color1', '')
            design.color2 = classification.get('color2', '')
            design.color3 = classification.get('color3', '')
            design.save()
        except Exception as e:
            print(f"Error in classification: {e}")  





@api_view(['DELETE'])
def delete_design(request, design_id):
    """
    Deletes a design if the user is the owner.
    """
    design = get_object_or_404(Design, id=design_id)

    # Check ownership
    if design.user != request.user:
        return Response(
            {"detail": "You do not have permission to delete this design."},
            status=status.HTTP_403_FORBIDDEN
        )

    design.delete()
    return Response(
        {"detail": "Design deleted successfully."},
        status=status.HTTP_200_OK
    )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    """
    Deletes a post if the user is the owner or if the user is an admin.
    """
    post = get_object_or_404(Post, id=post_id)

    # Check ownership or if the user is an admin
    if post.user != request.user and request.user.username != 'admin':
        return Response(
            {"detail": "You do not have permission to delete this post."},
            status=status.HTTP_403_FORBIDDEN
        )

    post.delete()
    return Response(
        {"detail": "Post deleted successfully."},
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
def get_design_by_id(request, designid):   
    try:
        # Fetch the design based on the designid
        design = Design.objects.get(id=designid)
        
        print(f"Fetching design {designid}: user={design.user}, is_anonymous={design.user is None}")

        # Serialize the design data
        serializer = DesignSerializer(design)    

        # Check if the user is eligible for a discount
        user = request.user
        serialized_data = serializer.data  # Get serialized data
        if user.is_authenticated and user.is_discount_eligible():
            discounted_price = Decimal(serialized_data['price']) * Decimal(0.75)  # Apply a 25% discount
            serialized_data['price'] = round(discounted_price, 2)  # Update the price in the serialized data

        print(f"Returning design data: {serialized_data}")
        return Response(serialized_data)  # Return serialized design data in JSON format
    except Design.DoesNotExist:
        return Response({'error': 'Design not found'}, status=status.HTTP_404_NOT_FOUND)       
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_design_archive(request):
    """
    Retrieve all designs created by the authenticated user, ordered by latest created designs first, 
    including discounts if eligible.
    """
    user = request.user

    # Fetch all designs created by the authenticated user, ordered by creation date (latest first)
    designs = Design.objects.filter(user=user).order_by('-created_at')

    # Pass the request to the serializer context so that we can apply discount logic
    serializer = DesignSerializer(designs, many=True, context={'request': request})
     
    return Response({"user": user.username, "designs": serializer.data})
  



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def posts(request):
    """
    Handles creating and fetching posts.
    """
    if request.method == 'GET':
        # Fetch all posts
        all_posts = Post.objects.all().order_by('-created_at')
        serializer = PostSerializer(all_posts, many=True, context={'request': request})
        return Response(serializer.data)

    if request.method == 'POST':
        # Create a new post
        design_id = request.data.get('design')
        caption = request.data.get('caption')
        description = request.data.get('description')
        hashtags = request.data.get('hashtags', [])

        print(f"Received POST request with design_id: {design_id}")
        print(f"Request data: {request.data}")

        if not design_id:
            return Response({"error": "Design ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # First try to find the design by ID only
            design = Design.objects.get(id=design_id)
            print(f"Found design: {design.id}, user: {design.user}")
            
            # Check if the design belongs to the current user or is anonymous
            if design.user and design.user != request.user:
                return Response({"error": "You can only create posts for your own designs or anonymous designs."}, status=status.HTTP_403_FORBIDDEN)
                
        except Design.DoesNotExist:
            print(f"Design with ID {design_id} not found")
            return Response({"error": "Design not found."}, status=status.HTTP_404_NOT_FOUND)

        # Create the post directly with the design object
        try:
            post = Post.objects.create(
                user=request.user,
                design=design,
                caption=caption,
                description=description
            )
            
            # Add hashtags
            for tag in hashtags[:5]:
                if tag and len(tag.strip()) > 0:
                    hashtag_obj, created = Hashtag.objects.get_or_create(name=tag.strip())
                    post.hashtags.add(hashtag_obj)
            
            print(f"Post created successfully: {post.id}")
            
            # Serialize the response
            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error creating post: {e}")
            return Response({"error": f"Failed to create post: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def public_posts(request):
    posts = Post.objects.all().select_related('design', 'user')  # Fetch posts with related fields
    
    # If user is authenticated, pass the request context to calculate is_liked/is_favorited
    if request.user.is_authenticated:
        serializer = PostSerializer(posts, many=True, context={'request': request})
    else:
        # For anonymous users, don't pass request context (will default to False for is_liked/is_favorited)
        serializer = PostSerializer(posts, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)
###########################################################################################################################################################
@api_view(['GET']) 
def get_user_posts(request, user_id):
    # Fetch the user using the user_id
    user = get_object_or_404(CustomUser, pk=user_id)

    # Fetch posts for the user with related data
    posts = Post.objects.filter(user=user).select_related('design').order_by('-created_at')
    
    # Annotate with like and comment counts
    posts = posts.annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True)
    )
    
    # --- NEW: Support ?as_user=<id> to check like/favorite for any user ---
    as_user_id = request.query_params.get('as_user')
    context = {'request': request}
    if as_user_id:
        try:
            as_user = CustomUser.objects.get(pk=as_user_id)
            context['as_user'] = as_user
        except CustomUser.DoesNotExist:
            pass  # fallback to request.user
    
    # Serialize the posts with context for proper design data
    serializer = PostSerializer(posts, many=True, context=context)
    
    return Response(serializer.data)




from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Post, Like, Favorite, Comment
from .serializers import CommentSerializer

# Toggle like (add or remove)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_like(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

    # Check if the user has already liked the post
    existing_like = Like.objects.filter(user=request.user, post=post).first()

    if existing_like:
        # If the like already exists, remove it
        existing_like.delete()

        # Remove the like notification if it exists
        Notification.objects.filter(
            user=post.user,
            action_user=request.user,
            design=post.design,
            notification_type='like'
        ).delete()

        # Check if the post owner still qualifies for a discount
        post_owner = post.user
        if not post_owner.is_discount_eligible():
            post_owner.is_discount_eligible = False
            post_owner.save()

        return Response({
            "message": "Like removed.",
            "is_liked": False,
            "like_count": post.likes.count()
        }, status=status.HTTP_200_OK)

    # Add the like
    Like.objects.create(user=request.user, post=post)

    # Create a notification when the like is added
    notification_message = f"{request.user.username} liked your design"
    Notification.objects.create(
        user=post.design.user,  # The owner of the design
        action_user=request.user,  # The user who liked the post
        design=post.design,
        notification_type='like',
        message=notification_message
    )

    # Check if the post owner qualifies for a discount
    post_owner = post.user
    if post_owner.is_discount_eligible():
        post_owner.is_discount_eligible = True
        post_owner.save()

    return Response({
        "message": "Like added.",
        "is_liked": True,
        "like_count": post.likes.count()
    }, status=status.HTTP_201_CREATED)


 


# Toggle favorite (add or remove)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

    # Use get_or_create for toggling favorite, and delete if already exists
    favorite, created = Favorite.objects.get_or_create(user=request.user, post=post)

    if not created:  # If the favorite already exists, remove it
        favorite.delete()

        # Remove the favorite notification if it exists
        Notification.objects.filter(user=post.user, action_user=request.user, design=post.design, notification_type='favorite').delete()

        return Response({
            "message": "Favorite removed.",
            "is_favorited": False,
            "favorite_count": post.favorites.count()
        }, status=status.HTTP_200_OK)

    # Create a notification when the favorite is added
    notification_message = f"{request.user.username} favorited your design"
    Notification.objects.create(
        user=post.design.user,  # The owner of the design
        action_user=request.user,  # The user who added to favorites
        design=post.design,
        notification_type='favorite',
        message=notification_message
    )

    return Response({
        "message": "Favorite added.",
        "is_favorited": True,
        "favorite_count": post.favorites.count()
    }, status=status.HTTP_201_CREATED)

# Delete a comment
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response({"error": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)

    # Allow admin to delete any comment or user to delete their own comments
    if request.user.username != 'admin' and comment.user != request.user:
        return Response({"error": "You can only delete your own comments."}, status=status.HTTP_403_FORBIDDEN)

    # Delete the notification related to this comment if it exists
    Notification.objects.filter(user=comment.post.design.user, action_user=request.user, design=comment.post.design, notification_type='comment').delete()

    comment.delete()
    return Response({"message": "Comment deleted."}, status=status.HTTP_204_NO_CONTENT)




@api_view(['GET'])
def get_comments(request, post_id):
    try:
        # Fetch all comments for the given post
        comments = Comment.objects.filter(post_id=post_id).select_related('user')
        
        # Serialize the comments
        serializer = CommentSerializer(comments, many=True)
        
        # Return the list of comments as a response
        return Response({'comments': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_favorites(request):
    """
    Get all designs favorited by the authenticated user.
    """
    favorites = Favorite.objects.filter(user=request.user)
    designs = [favorite.post.design for favorite in favorites]

    # Pass the request to the serializer's context
    serializer = DesignSerializer(designs, many=True, context={'request': request})

    return Response({"favorites": serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_liked(request):
    """
    Get all designs liked by the authenticated user.
    """
    liked_designs = Like.objects.filter(user=request.user)
    designs = [like.post.design for like in liked_designs]

    # Pass the request to the serializer's context
    serializer = DesignSerializer(designs, many=True, context={'request': request})

    return Response({"liked": serializer.data}, status=status.HTTP_200_OK)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_like(request, design_id):
    try:
        # Get the post linked to the design
        post = Post.objects.get(design__id=design_id)
        # Get the like by the user
        like = Like.objects.get(user=request.user, post=post)
        like.delete()
        return Response({'success': 'Like removed.'})
    except Post.DoesNotExist:
        return Response({'error': 'Post not found for this design.'}, status=404)
    except Like.DoesNotExist:
        return Response({'error': 'Like not found.'}, status=404)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_favorite(request, design_id):
    try:
        # Get the post linked to the design
        post = Post.objects.get(design__id=design_id)
        # Get the favorite by the user for this post
        favorite = Favorite.objects.get(user=request.user, post=post)
        favorite.delete()
        return Response({"message": "Removed from favorites successfully."}, status=204)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found for this design.'}, status=404)
    except Favorite.DoesNotExist:
        return Response({"error": "Favorite not found."}, status=404)

    


 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    user = request.user

    # Get all notifications for the user, ordered by the creation date (most recent first)
    notifications = Notification.objects.filter(user=user).order_by('-created_at')

    # Serialize the notifications
    serializer = NotificationSerializer(notifications, many=True)

    return Response({'notifications': serializer.data}, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, notification_id):
    try:
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        notifications.update(is_read=True)
        return Response({"message": "All notifications marked as read."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

    notification.delete()

    return Response({"message": "Notification deleted."}, status=status.HTTP_204_NO_CONTENT)



@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure the user is logged in
def add_to_cart(request):
    user = request.user
    design_id = request.data.get('design_id')

    # Validate if design_id is provided
    if not design_id:
        return Response({"error": "Design ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the design exists
    design = get_object_or_404(Design, id=design_id)

    # Check if the item is already in the cart
    if Chart.objects.filter(user=user, design=design).exists():
        return Response({"error": "This item is already in your cart."}, status=status.HTTP_400_BAD_REQUEST)

    # Calculate the discounted price if the user is eligible
    price = design.price
    if user.is_discount_eligible():
        price *= Decimal('0.75')  # Apply a 25% discount

    # Add the item to the cart
    cart_item = Chart.objects.create(user=user, design=design, price=price)  # Assuming `Chart` has a `price` field
    return Response({"message": "Item added to cart successfully!"}, status=status.HTTP_201_CREATED)



@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure the user is logged in
def view_cart(request):
    user = request.user
    cart_items = Chart.objects.filter(user=user)
    serializer = ChartSerializer(cart_items, many=True)
    return Response(serializer.data, status=200)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure the user is logged in
def delete_from_cart(request, cart_id):
    user = request.user
    cart_item = get_object_or_404(Chart, id=cart_id, user=user)
    cart_item.delete()
    return Response({"message": "Item removed from cart successfully!"}, status=status.HTTP_200_OK)












@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_posts(request):
    """
    Fetch all posts by the authenticated user.
    """
    user_posts = Post.objects.filter(user=request.user).order_by('-created_at')
    serializer = PostSerializer(user_posts, many=True, context={'request': request})
    return Response(serializer.data)

#cloud secret key = 6qL3HdWcb3HJ72iqIGnDMRkVNd8
#cloud api key = 428318487815239

# =======================================================================================
#recipe :  a76c916b-1ea8-4a18-b378-07ec7f18e164
#bill : Kd+wOqFRk0btkCgQc7HYxRU2OuxA6xbq0W3JekY6FNs=

def resize_image(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))

    # Resize the image to 1176 x 2060px
    img = img.resize((1176, 2060))

    # Save the resized image to a buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)  # Ensure the pointer is at the start of the buffer

    return buffer

# Function to upload image to Cloudinary and return the URL
def upload_to_cloudinary(image_buffer):
    response = upload(image_buffer)
    return response['url']  # Return the URL of the uploaded image








@api_view(['POST', 'GET'])
def test(request):
    api_key = "iffjgbnj8L+n8rjqBnhuAhJ6b/F1x7hFNO0H8B43h9w="
    recipe_id = "b906a8c2-8670-4f6e-acf0-b2a9832e82eb"


    design_id = request.data.get("design")
    phone_number = request.data.get("phone_number")
    address = request.data.get("address")
    city = request.data.get("city")
    country = request.data.get("country")
    first_name = request.data.get("firstname")
    last_name = request.data.get("lastname")  
    email = request.data.get("email")   
    sku = request.data.get("sku")
     
    try:
        design = Design.objects.get(id=design_id)
    except Design.DoesNotExist:
        return Response({"error": "Design not found"}, status=status.HTTP_404_NOT_FOUND)
    
    order_data = {
        "Items": [
            {
                "SKU": sku,
                "Quantity": 1,
                "Images": [
                    {
                        "Url": design.image_url,
                        "UseUrlAsImageID": False,  # Use URL as image source
                        "Position": { 
                            "X": 0.5,  # Center image on X-axis
                            "Y": 0.5,  # Center image on Y-axis
                            "ScaleX": 1.0,  # Scale to fit
                            "ScaleY": 1.0,  # Scale to fit
                            "Rotation": 0,  # No rotation needed
                        },
                        "PrintArea": {
                            "Width": 1176 ,  # Use the actual print area width
                            "Height": 2060,  # Use the actual print area height
                        }
                    }
                ]
            }
        ],
        "ShipToAddress": {
            "FirstName": first_name,
            "LastName": last_name,
            "Line1": "123 Main St",
            "City": city,
            "State": "NY",
            "PostalCode": "10001",
            "CountryCode": country,
            "Phone": phone_number,  # Ensure phone_number is included here
            "Email": email, 
        },
        "BillingAddress": {
            "FirstName": first_name,
            "LastName": last_name,
            "Line1": "123 Main St",
            "City": city,
            "State": "NY",
            "PostalCode": "10001",
            "CountryCode": 'US',
            "Phone": phone_number,  # Include phone_number in billing if required
            "Email": email,  
        },
        "Payment": {
            "CurrencyCode": "USD",
            "PartnerBillingKey": "iffjgbnj8L+n8rjqBnhuAhJ6b/F1x7hFNO0H8B43h9w=" #============================================<<<<<<<<<<<<<<<<<<<<<<<<
        },
        "IsPackingSlipEnabled": True,  # Explicitly enable packing slips
    }
  
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.print.io/api/orders?recipeId={recipe_id}"
    res = requests.post(url=url, headers=headers, json=order_data) 
    print("Response Status Code:", res.status_code)
    print("Response JSON:", res.json()) 
    if res.status_code == 200:
        return Response(res.json(), status=status.HTTP_201_CREATED)
    else:
        return Response({"error": res.json()}, status=res.status_code)
  





@api_view(['GET'])
def get_phone_cases(request):

    GOOTEN_API_KEY = "Kd+wOqFRk0btkCgQc7HYxRU2OuxA6xbq0W3JekY6FNs="
    recipe_id = "a76c916b-1ea8-4a18-b378-07ec7f18e164"
    GOOTEN_PRODUCTS_URL = "https://api.print.io/api/v/6/source/api/products"

    """
    Fetch all phone case types from Gooten API.
    """
    try:
        # Include the API key as a query parameter
        params = {
            "apiKey": GOOTEN_API_KEY,
        }
        response = requests.get(GOOTEN_PRODUCTS_URL, params=params)
        response_data = response.json()

        # Filter phone case products
        phone_cases = [
            product for product in response_data.get("Products", [])
            if "phone case" in product.get("Name", "").lower()
        ]

        # Return the filtered list
        return Response({"phone_cases": phone_cases}, status=response.status_code)
    
    except Exception as e:
        return Response({"error": str(e)}, status=500)
    

    

@api_view(["GET"])
def get_templates(request):
    api_key = "Kd+wOqFRk0btkCgQc7HYxRU2OuxA6xbq0W3JekY6FNs="
    recipe_id = "a76c916b-1ea8-4a18-b378-07ec7f18e164"
    
    # Construct the request URL
    url = f"https://api.print.io/api/v/5/source/api/producttemplates/?recipeid={recipe_id}&sku=PremiumPhoneCase-iPhone-15-pro-SnapCaseGloss"
    
    # Set the headers with API key and content type
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Send GET request to Gooten API
        res = requests.get(url, headers=headers)

        # Check for successful response
        if res.status_code == 200:
            # Parse the JSON response
            data = res.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            # Handle non-200 responses
            return Response({"error": res.content.decode()}, status=res.status_code)
    
    except Exception as e:
        # Handle any request exceptions
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    








@api_view(['POST'])
def creatte_order(request):
    """
    API view to create an order using the OrderSerializer.
    Validates the quantity to ensure it does not exceed 9.
    """
    # Get the order data from the request
    order_data = request.data

    # Check if the quantity is greater than 9user_design_archive
    try:
        quantity = int(order_data.get('quantity', 1))  # Default to 1 if quantity is not provided
    except ValueError:
        return Response(
            {"error": "Invalid quantity. It must be an integer."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if quantity > 9:
        return Response(
            {"error": "Quantity cannot exceed 9."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Proceed with serialization and saving the order if quantity is valid
    serializer = OrderSerializer(data=order_data)
    
    if serializer.is_valid():
        # Save the order with the authenticated user, if applicable
        user = request.user if request.user.is_authenticated else None
        serializer.save(user=user)
        return Response(
            {"message": "Order created successfully", "order": serializer.data},
            status=status.HTTP_201_CREATED
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 
@csrf_exempt  # Disable CSRF for testing purposes
@api_view(['DELETE'])  # Allow only DELETE method for this view
def cancel_order(request, order_id): 
    try:
        # Get the order object by its ID
        order = Order.objects.get(id=order_id)
        
        # Ensure the order status is 'pending' before allowing deletion
        if order.status == 'pending':
            order.delete()  # Delete the order
            return Response({"message": "Order has been deleted successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Order cannot be deleted. It is either completed or canceled."}, status=status.HTTP_400_BAD_REQUEST)

    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

     
@api_view(['GET'])
def get_user_orders(request):
    """
    API view to get all orders for the authenticated user.
    """
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication credentials were not provided."},
            status=status.HTTP_403_FORBIDDEN
        )

    # Filter orders by the authenticated user
    orders = Order.objects.filter(user=request.user)

    # Serialize the orders and return them
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def cancel_order(request, order_id):          
    """
    API view to cancel an order by its ID.
    """
    try:
        # Fetch the order
        order = Order.objects.get(id=order_id)

        # Check if the order can be canceled
        if order.status == 'canceled':
            return Response(
                {"message": "Order is already canceled."},
                status=status.HTTP_400_BAD_REQUEST
            )     
        elif order.status == 'completed':
            return Response(
                {"message": "Completed orders cannot be canceled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the status to 'canceled'
        order.status = 'canceled'
        order.save()

        return Response(
            {"message": f"Order {order.id} has been canceled successfully."},
            status=status.HTTP_200_OK
        )

    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    # Replace with your actual API token
    api_token = 'J5O5PrGXT4q0Qvs75Z16JIOvs4BmB5Gk5ZqusZe6'
    
    # Example order data
    order_data = {
        "external_id": "4235234213",
        "shipping": "STANDARD",
        "recipient": {
            "name": "John Smith",
            "company": "John Smith Inc",
            "address1": "19749 Dearborn St",
            "address2": "string",
            "city": "Chatsworth",
            "state_code": "CA",
            "state_name": "California",
            "country_code": "US",
            "country_name": "United States",
            "zip": "91311",
            "phone": "2312322334",
            "email": "firstname.secondname@domain.com",
            "tax_number": "123.456.789-10"
        },
        "items": [
            {
                "id": 1,
                "external_id": "item-1",
                "variant_id": 1,
                "sync_variant_id": 1,
                "external_variant_id": "variant-1",
                "warehouse_product_variant_id": 1,
                "product_template_id": 1,
                "external_product_id": "template-123",
                "quantity": 1,
                "price": "13.00",
                "retail_price": "13.00",
                "name": "Enhanced Matte Paper Poster 18×24",
                "product": {
                    "variant_id": 3001,
                    "product_id": 301,
                    "image": "https://files.cdn.printful.com/products/71/5309_1581412541.jpg",
                    "name": "Bella + Canvas 3001 Unisex Short Sleeve Jersey T-Shirt with Tear Away Label (White / 4XL)"
                },
                "files": [
                    {
                        "type": "default",
                        "url": "https://www.example.com/files/tshirts/example.png",
                        "options": [
                            {
                                "id": "template_type",
                                "value": "native"
                            }
                        ],
                        "filename": "shirt1.png",
                        "visible": True,
                        "position": {
                            "area_width": 1800,
                            "area_height": 2400,
                            "width": 1800,
                            "height": 1800,
                            "top": 300,
                            "left": 0,
                            "limit_to_print_area": True
                        }
                    }
                ],
                "options": [
                    {
                        "id": "OptionKey",
                        "value": "OptionValue"
                    }
                ],
                "sku": None,
                "discontinued": True,
                "out_of_stock": True
            }
        ],
        "retail_costs": {
            "currency": "USD",
            "subtotal": "10.00",
            "discount": "0.00",
            "shipping": "5.00",
            "tax": "0.00"
        },
        "gift": {
            "subject": "To John",
            "message": "Have a nice day"
        },
        "packing_slip": {
            "email": "your-name@your-domain.com",
            "phone": "+371 28888888",
            "message": "Message on packing slip",
            "logo_url": "http://www.your-domain.com/packing-logo.png",
            "store_name": "Your store name",
            "custom_order_id": "kkk2344lm"
        }
    }

    # Make the request to the Printful API
    response = requests.post(
        'https://api.printful.com/orders/',
        headers={
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        },
        json=order_data
    )

    # Handle the response
    if response.status_code == 200:
        return Response(response.json(), status=200)
    else:
        return Response({
            'error': 'Failed to communicate with Printful',
            'details': response.json()  # More details from the Printful response
        }, status=response.status_code)







class TestOrderView(APIView):
    def post(self, request, *args, **kwargs):
        # Example static order payload for Printful API
        test_order_payload = {
            "external_id": "test-order-123",
            "shipping": "STANDARD",
            "recipient": {
                "name": "John Doe",
                "company": "Test Company",
                "address1": "123 Test St",
                "address2": "",
                "city": "Test City",
                "state_code": "CA",
                "country_code": "US",
                "zip": "90001",
                "phone": "1234567890",
                "email": "john.doe@example.com",
            },
            "items": [
                {
                    "variant_id": "670e2c2e90d783",  # Example product variant (a t-shirt in this case)
                    "quantity": 1,
                    "name": "Test Product",
                    "files": [
                        {
                            "type": "default",
                            "url": "https://www.example.com/files/design.png"
                        }
                    ]
                }
            ]
        }
        
        try:
            # Send the test order to Printful
            response = requests.post(
                "https://api.printful.com/orders",
                json=test_order_payload,
                headers={
                    "Authorization": f"Bearer {settings.PRINTFUL_API_TOKEN}",
                    "Content-Type": "application/json",
                }
            )
            
            # Check for successful response
            response.raise_for_status()
            
            # Return the successful response from Printful
            return Response(response.json(), status=status.HTTP_200_OK)
        
        except requests.exceptions.HTTPError as http_err:
            return Response(
                {"error": "Failed to communicate with Printful", "details": str(http_err)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as err:
            return Response(
                {"error": "An unexpected error occurred", "details": str(err)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )















@api_view(['POST'])
def create_product_view(request):
    design_id = request.data.get('design_id')

    if not design_id:
        return Response({"error": "Design ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    design = get_object_or_404(Design, id=design_id)
    image_url = design.image.url  # Ensure this URL is valid and accessible

    api_token = 'J5O5PrGXT4q0Qvs75Z16JIOvs4BmB5Gk5ZqusZe6'  # Replace with your actual API token
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "name": "Your Custom Product Name",
        "type": "apparel",
        "variants": [
            {
                "variant_id": "670e2c2e90d783",  # Ensure this ID is valid
                "files": [
                    {
                        "type": "default",
                        "url": image_url,  # Your image URL from the database
                        "visible": True,
                        "position": {
                            "area_width": 1800,
                            "area_height": 2400,
                            "width": 1800,
                            "height": 1800,
                            "top": 300,
                            "left": 0,
                            "limit_to_print_area": True
                        }
                    }
                ],
                "options": []  # Add actual options if needed
            }
        ]
    }

    response = requests.post("https://api.printful.com/products", json=payload, headers=headers)

    if response.status_code in (200, 201):
        return Response(response.json(), status=status.HTTP_201_CREATED)
    else:
        return Response(response.json(), status=response.status_code)


from rest_framework_simplejwt.tokens import RefreshToken


@api_view(['POST'])
def registerview(request):
    if request.method == "POST":
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
             
            # Check if a profile picture was uploaded
            profile_pic = request.FILES.get('profile_pic')
            if profile_pic:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(profile_pic, folder="profile_pics")
                # Update the user profile with the Cloudinary URL
                user.profile_pic = upload_result['url']
                user.save()

            # Create JWT tokens for the new user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            # Return response with tokens and user data
            return Response({
                'user': serializer.data,
                'access_token': access_token,
                'refresh_token': str(refresh)
            }, status=status.HTTP_201_CREATED)
        else:
            # Return validation errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        







@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_view(request):
    user = request.user

    # Handle profile picture with a default path if not present


    profile_data = {
        "id" : user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "profile_pic": user.profile_pic
    }
    
    return Response(profile_data)











@api_view(['GET'])
def user_list(request):
    try:
        users = CustomUser.objects.all()  # Get all users
        serializer = UserSerializer(users, many=True)  # Serialize the list of users
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    




@api_view(['GET'])
def user_detail(request, id):
    try:
        user = CustomUser.objects.get(id=id)  # Get user by id
        serializer = UserSerializer(user)  # Serialize the user
        return Response(serializer.data)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    





@api_view(['GET'])
def most_liked_designs(request):
    print("[most_liked_designs] Request user:", request.user, "Authenticated:", request.user.is_authenticated)
    try:
        # Fetch designs with their related post like counts
        designs = Design.objects.annotate(
            like_count=Count('posts__likes')
        ).filter(like_count__gt=0)  # Get designs with at least one like

        # Limit the designs by the most likes (using Python)
        designs = sorted(designs, key=lambda x: x.like_count, reverse=True)[:16]

        if not designs:
            return Response({'message': 'No liked designs available'}, status=status.HTTP_200_OK)

        # Fetch posts related to these designs
        posts = Post.objects.filter(design__in=designs).select_related('design', 'user')
        post_serializer = PostSerializer(posts, many=True, context={'request': request})

        return Response(post_serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def most_added_to_cart_designs(request):
    try:
        # Fetch designs with their related cart counts
        designs = Design.objects.annotate(
            cart_count=Count('chart')
        ).filter(cart_count__gt=0)  # Get designs with at least one cart addition

        if not designs.exists():
            return Response({'message': 'No designs added to cart yet'}, status=status.HTTP_200_OK)

        # Sort the designs by cart count in descending order (using Python)
        designs = sorted(designs, key=lambda x: x.cart_count, reverse=True)[:10]

        # Fetch posts related to these top 10 designs
        posts = Post.objects.filter(design__in=designs).select_related('design', 'user')
        post_serializer = PostSerializer(posts, many=True, context={'request': request})

        return Response(post_serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)      
    


from django.contrib.auth import get_user_model

from django.db.models import Count, Sum
      

from django.db.models import Count, Sum, Q

@api_view(['GET'])
def search(request):
    query = request.GET.get('query', '')  # Get the search query from the request
    as_user_id = request.query_params.get('as_user')  # Get the user ID to check likes/favorites for
    print(f"Search request - query: {query}, as_user_id: {as_user_id}")
    print(f"Current user: {request.user.username if request.user.is_authenticated else 'Not authenticated'}")
    print(f"All query params: {request.query_params}")
    
    if query:
        try:
            # Get the custom User model
            User = get_user_model()

            # Search in the Post model (including hashtags)
            posts = Post.objects.filter(
                Q(caption__icontains=query) |  # Case-insensitive search for caption
                Q(description__icontains=query) |  # Case-insensitive search for description
                Q(design__modell__icontains=query) |  # Search in the design's modell field
                Q(design__sku__icontains=query) |  # Search in the design's SKU
                Q(design__type__icontains=query) |  # Search in the design's type
                Q(design__theclass__icontains=query) |  # Search in the design's theclass field
                Q(hashtags__name__icontains=query)  # Search in hashtags (many-to-many relationship)
            ).select_related('design', 'user').prefetch_related('hashtags').distinct()  # Preload related data and ensure unique results

            # Search in the User model
            users = User.objects.filter(
                Q(username__icontains=query) |  # Case-insensitive search for username
                Q(first_name__icontains=query) |  # Case-insensitive search for first name
                Q(last_name__icontains=query) |  # Case-insensitive search for last name
                Q(email__icontains=query)  # Case-insensitive search for email
            ).annotate(
                total_posts=Count('post', distinct=True),  # Count distinct posts for each user
                total_likes=Count('post__likes', distinct=True)  # Count distinct Like objects across user's posts 
            )

            # Set up context for serializer
            context = {'request': request}
            if as_user_id:
                try:
                    as_user = CustomUser.objects.get(pk=as_user_id)
                    context['as_user'] = as_user
                    print(f"Using as_user from query param: {as_user.username}")
                except CustomUser.DoesNotExist:
                    print(f"User {as_user_id} not found, using request.user if authenticated")
                    if request.user.is_authenticated:
                        context['as_user'] = request.user
            elif request.user.is_authenticated:
                print(f"No as_user provided, but user is authenticated: {request.user.username}")
                context['as_user'] = request.user
            else:
                print("No as_user provided and no authenticated user")

            # Serialize the results
            post_serializer = PostSerializer(posts, many=True, context=context)

            # Manually include total_posts and total_likes in user serialization
            user_data = []
            for user in users:
                user_data.append({
                    'id': user.id, 
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'profile_pic': user.profile_pic,
                    'total_posts': user.total_posts,
                    'total_likes': user.total_likes if user.total_likes is not None else 0
                })

            # Combine and return the results
            return Response({
                'posts': post_serializer.data,
                'users': user_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'message': 'No search query provided.'}, status=status.HTTP_400_BAD_REQUEST)
 
 


    

@api_view(['GET', 'POST'])
def fetch_stickers(request):
    # Replace with your actual Flaticon API key
    api_key = 'FPSXf8d02bb7c934441eae5a6b32275a4f9a' 
    url = 'https://api.freepik.com/v1/icons'
    
    headers = {
        "x-freepik-api-key": api_key,
    }
    
    # Default pagination parameters
    page = 1  # Start at page 1
    limit = 100  # Limit the results per page, e.g., 100 per page
    total_stickers = 0  # Track the total number of stickers fetched
    required_stickers = 200  # Set the minimum number of stickers required
    all_icons = []  # List to store all fetched stickers
    params = {
      # Keyword to filter icons by type
    'page': page,
    'limit': limit,  
"term":"emoji",
"filters[shape]":"lineal-color"   
} 
    try:      
        while total_stickers < required_stickers:
            # Add pagination parameters to the request  
            response = requests.get(url, headers=headers, params=params) 
            response.raise_for_status()  # Raise an error for HTTP 4xx/5xx responses
            data = response.json()  

            icons = data.get('data', [])  
            all_icons.extend(icons)  # Add icons from the current page to the list
            total_stickers += len(icons)  # Increment the total stickers count

            # If there are fewer icons than requested, stop fetching
            if len(icons) < limit:
                break
             
            # Move to the next page
            page += 1

        return JsonResponse({"data": all_icons[:required_stickers]}, safe=False)  # Return only up to 200 stickers

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': 'Failed to fetch resources', 'details': str(e)}, status=500)
    



@api_view(['GET', 'POST'])
def fetch_emoji(request):
    # Replace with your actual Flaticon API key
    # Your Emoji API key
    access_key = 'e4aece1920eea4d2634a2d31588b7b9a8362f89a'
    
    # Emoji API URL with your access key
    url = f"https://emoji-api.com/categories/travel-places?access_key={access_key}"
    
    try:
        # Making a GET request to the Emoji API
        response = requests.get(url)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Get the emoji data
        emojis = response.json()
        
        # Return the emoji data as JSON
        return Response({"data": emojis}, status=200)
    
    except requests.exceptions.RequestException as e:
        # Handle any errors that occurred during the request
        return Response({'error': 'Failed to fetch emojis', 'details': str(e)}, status=500)
    

@api_view(['GET'])
def get_user_details(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Get user statistics
        total_posts = Post.objects.filter(user=user).count()
        total_likes = Like.objects.filter(post__user=user).count()
        total_comments = Comment.objects.filter(post__user=user).count()
        total_favorites = Favorite.objects.filter(post__user=user).count()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'profile_pic': user.profile_pic,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'is_staff': user.is_staff,
            'status': user.status,
            'statistics': {
                'total_posts': total_posts,
                'total_likes': total_likes,
                'total_comments': total_comments,
                'total_favorites': total_favorites,
            }
        })
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['GET'])
def top_users_by_likes(request):
    try:
        # Annotate users with the total likes on their posts
        users = CustomUser.objects.annotate(
            total_likes=Count('post__likes', distinct=True),
            total_posts=Count('post', distinct=True)       
        ).filter(total_likes__gt=0).order_by('-total_likes')[:5]
        data = [
            {
                'user_id': user.id,     
                'username': user.username,
                'profile_pic': user.profile_pic,    
                 'email' : user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'total_likes': user.total_likes,
                'total_posts': user.total_posts  # Add total posts
            }
            for user in users
        ]
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def top_users_by_posts(request):
    try:
        # Annotate users with the total likes on their posts and total posts
        users = CustomUser.objects.annotate(
            total_likes=Count('post__likes', distinct=True),
            total_posts=Count('post', distinct=True)
        ).filter(total_posts__gt=0).order_by('-total_posts')[:4]  # Order by total posts
        
        data = [
            {
                'user_id': user.id,
                'username': user.username,
                'profile_pic': user.profile_pic,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'total_likes': user.total_likes,
                'total_posts': user.total_posts  # Add total posts
            }
            for user in users
        ]
        
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])

def recent_posts(request):
    """
    Retrieves the most recent posts.
    """
    # Retrieve the most recent posts, ordered by creation date (descending)
    posts = Post.objects.all().order_by('-created_at')[:10]  # Adjust number as needed

    # Serialize the posts
    serializer = PostSerializer(posts, many=True, context={'request': request})

    return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.exceptions import NotFound
@api_view(['GET'])
def get_post_by_id(request, id):
    try:
        post = Post.objects.select_related('user', 'design').get(id=id)
        
        # Get user's other posts
        user_posts = Post.objects.filter(user=post.user).exclude(id=id).order_by('-created_at')[:5]
        
        # Set up context for serializer
        as_user_id = request.query_params.get('as_user')
        context = {'request': request}
        if as_user_id:
            try:
                as_user = CustomUser.objects.get(pk=as_user_id)
                context['as_user'] = as_user
            except CustomUser.DoesNotExist:
                if request.user.is_authenticated:
                    context['as_user'] = request.user
        elif request.user.is_authenticated:
            context['as_user'] = request.user
        
        # Use the updated PostSerializer which now includes user_details and comments
        post_data = PostSerializer(post, context=context).data
        user_posts_data = PostSerializer(user_posts, many=True, context=context).data
        
        return Response({
            **post_data,
            'user_posts': user_posts_data
        })
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

#live_UCW4Io0BICBZ2jeolZMWZhisEanGXIaJIZYPhvcktIY1aD7Mhf3AVoLLMgGxVytN





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_thecurrent_user(request):
    print("Request user:", request.user)
    return Response({
        'username': request.user.username,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_orders_view(request):
    if request.user.username != 'admin':
        return Response({'detail': 'Forbidden'}, status=403)
    
    orders = Order.objects.all().order_by('-id')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)




class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def reports_view(request):
    """
    List all reports or create a new report.
    Only admin users can list reports, but any authenticated user can create reports.
    """
    if request.method == 'GET':
        # Get filter parameters
        status_filter = request.query_params.get('status', 'all')
        content_type = request.query_params.get('content_type', 'all')
        search_term = request.query_params.get('search', '')

        # Base queryset with default ordering
        reports = Report.objects.all().order_by('-id')  # Default ordering by ID descending

        # Apply filters
        if status_filter != 'all':
            reports = reports.filter(status=status_filter)
        if content_type != 'all':
            reports = reports.filter(content_type=content_type)
        if search_term:
            reports = reports.filter(
                Q(reason__icontains=search_term) |
                Q(reported_by__username__icontains=search_term)
            )

        # Serialize reports with content details
        serialized_reports = []
        for report in reports:
            report_data = ReportSerializer(report).data
            content_details = None

            try:
                if report.content_type == 'post':
                    post = Post.objects.get(id=report.content_id)
                    content_details = {
                        'post_id': post.id,
                        'caption': post.caption,
                        'description': post.description,
                        'created_at': post.created_at,
                        'user': post.user.username,
                        'user_id': post.user.id,  # Add the user_id here
                        'image_url': post.design.image_url,
                        'design__modell': post.design.modell,
                        'design__type': post.design.type,
                        'design__price': float(post.design.price),
                        'comments': [
                            {
                                'id': comment.id,
                                'content': comment.content,
                                'created_at': comment.created_at,
                                'user': comment.user.username,
                                'user_id': comment.user.id,
                                'profile_pic': comment.user.profile_pic
                            }
                            for comment in post.comments.all().order_by('-created_at')
                        ]
                    }
                elif report.content_type == 'comment':
                    comment = Comment.objects.get(id=report.content_id)
                    content_details = {
                        'content': comment.content,
                        'created_at': comment.created_at,
                        'user': comment.user.username,
                        'user_id': comment.user.id,  # Add the user_id here
                        'profile_pic': comment.user.profile_pic,
                        'post_id': comment.post.id,
                        'post_caption': comment.post.caption,
                        'post_description': comment.post.description,
                        'post_image_url': comment.post.design.image_url,
                        'post_user': comment.post.user.username,
                        'post_user_id': comment.post.user.id,  # Add the post user_id here
                        'post_created_at': comment.post.created_at,
                        'design__modell': comment.post.design.modell,
                        'design__type': comment.post.design.type,
                        'design__price': float(comment.post.design.price)
                    }
            except (Post.DoesNotExist, Comment.DoesNotExist):
                content_details = {'error': 'Content no longer exists'}

            report_data['content_details'] = content_details
            serialized_reports.append(report_data)

        return Response(serialized_reports)

    elif request.method == 'POST':
        # Any authenticated user can create a report
        serializer = ReportSerializer(data=request.data)
        if serializer.is_valid():
            # Check if the content exists
            content_type = serializer.validated_data['content_type']
            content_id = serializer.validated_data['content_id']

            try:
                if content_type == 'post':
                    Post.objects.get(id=content_id)
                elif content_type == 'comment':
                    Comment.objects.get(id=content_id)
            except (Post.DoesNotExist, Comment.DoesNotExist):
                return Response(
                    {"error": f"{content_type.capitalize()} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if user has already reported this content
            existing_report = Report.objects.filter(
                content_type=content_type,
                content_id=content_id,
                reported_by=request.user
            ).first()

            if existing_report:
                return Response(
                    {"error": f"You have already reported this {content_type}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer.save(reported_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_report_status(request, report_id):
    """
    Update the status of a report.
    Only admin users can access this endpoint.
    """
    if request.user.username != 'admin':
        return Response({'detail': 'Forbidden'}, status=403)

    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'detail': 'Report not found'}, status=404)

    action = request.data.get('action')
    if action == 'resolve':
        report.status = 'resolved'
    elif action == 'dismiss':
        report.status = 'reviewed'
    else:
        return Response({'detail': 'Invalid action'}, status=400)

    report.save()
    
    # Get updated report data with content details
    report_data = ReportSerializer(report).data
    
    # Add content details
    if report.content_type == 'post':
        try:
            post = Post.objects.get(id=report.content_id)
            report_data['content_details'] = {
                'post_id': post.id,  # Add the post ID
                'caption': post.caption,
                'description': post.description,
                'created_at': post.created_at,
                'user': post.user.username,
                'image_url': post.design.image_url,
                'design__modell': post.design.modell,
                'design__type': post.design.type,
                'design__price': float(post.design.price),
                'comments': [
                    {
                        'id': comment.id,
                        'content': comment.content,
                        'created_at': comment.created_at,
                        'user': comment.user.username,
                        'user_id': comment.user.id,
                        'profile_pic': comment.user.profile_pic
                    }
                    for comment in post.comments.all().order_by('-created_at')
                ]
            }
        except Post.DoesNotExist:
            report_data['content_details'] = {'error': 'Post not found'}
    
    elif report.content_type == 'comment':
        try:
            comment = Comment.objects.get(id=report.content_id)
            report_data['content_details'] = {
                'content': comment.content,
                'created_at': comment.created_at,
                'user': comment.user.username,
                'profile_pic': comment.user.profile_pic,
                'post_id': comment.post.id,
                'post_caption': comment.post.caption,
                'post_description': comment.post.description,
                'post_image_url': comment.post.design.image_url,
                'post_user': comment.post.user.username,
                'post_created_at': comment.post.created_at,
                'design__modell': comment.post.design.modell,
                'design__type': comment.post.design.type,
                'design__price': float(comment.post.design.price)
            }
        except Comment.DoesNotExist:
            report_data['content_details'] = {'error': 'Comment not found'}
    
    return Response(report_data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def announcements_view(request):
    if request.method == 'GET':
        announcements = Announcement.objects.all()
        serializer = AnnouncementSerializer(announcements, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Check if user is admin
        if not request.user.is_staff:
            return Response({'error': 'Only admins can create announcements'}, status=403)
        
        data = request.data.copy()
        announcement_type = data.get('type', 'text')
        
        # Handle image upload
        if announcement_type == 'image':
            image = request.FILES.get('image')
            if not image:
                return Response({'error': 'Image is required for image announcements'}, status=400)
            
            # Check if we already have 6 image announcements
            image_count = Announcement.objects.filter(type='image').count()
            if image_count >= 6:
                return Response({'error': 'Maximum of 6 image announcements allowed'}, status=400)
            
            # Upload image to Cloudinary
            try:
                image_buffer = BytesIO(image.read())
                image_url = upload_to_cloudinary(image_buffer)
                data['image_url'] = image_url
                data['position'] = image_count + 1  # Set position for ordering
            except Exception as e:
                return Response({'error': f'Failed to upload image: {str(e)}'}, status=500)
        
        serializer = AnnouncementSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_announcement(request, announcement_id):
    if not request.user.is_staff:
        return Response({'error': 'Only admins can delete announcements'}, status=403)
    
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        
        # If it's an image announcement, update positions of other image announcements
        if announcement.type == 'image':
            # Get all image announcements with position greater than the deleted one
            later_announcements = Announcement.objects.filter(
                type='image',
                position__gt=announcement.position
            )
            # Decrement their positions
            for ann in later_announcements:
                ann.position -= 1
                ann.save()
        
        announcement.delete()
        return Response(status=204)
    except Announcement.DoesNotExist:
        return Response({'error': 'Announcement not found'}, status=404)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_announcement_position(request, announcement_id):
    if not request.user.is_staff:
        return Response({'error': 'Only admins can update announcement positions'}, status=403)
    
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        if announcement.type != 'image':
            return Response({'error': 'Only image announcements can be repositioned'}, status=400)
        
        new_position = request.data.get('position')
        if new_position is None:
            return Response({'error': 'New position is required'}, status=400)
        
        new_position = int(new_position)
        if new_position < 1 or new_position > 6:
            return Response({'error': 'Position must be between 1 and 6'}, status=400)
        
        old_position = announcement.position
        
        # Update positions of other announcements
        if new_position > old_position:
            # Moving down: decrement positions of announcements in between
            Announcement.objects.filter(
                type='image',
                position__gt=old_position,
                position__lte=new_position
            ).update(position=models.F('position') - 1)
        else:
            # Moving up: increment positions of announcements in between
            Announcement.objects.filter(
                type='image',
                position__gte=new_position,
                position__lt=old_position
            ).update(position=models.F('position') + 1)
        
        announcement.position = new_position
        announcement.save()
        
        return Response({'message': 'Position updated successfully'})
    except Announcement.DoesNotExist:
        return Response({'error': 'Announcement not found'}, status=404)
    except ValueError:
        return Response({'error': 'Invalid position value'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    """
    Get enhanced analytics data for the admin dashboard.
    Only admin users can access this endpoint.
    """
    try:
        if request.user.username != 'admin':
            return Response({'detail': 'Forbidden'}, status=403)

        # Get date range from query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        print(f"Fetching analytics with date range: {start_date} to {end_date}")

        # Base querysets with date filtering
        base_filter = {}
        if start_date:
            base_filter['created_at__gte'] = start_date
        if end_date:
            base_filter['created_at__lte'] = end_date

        # Design Analytics
        designs = Design.objects.filter(**base_filter)
        print(f"Found {designs.count()} designs")
        
        # Calculate revenue and order count from orders first, excluding canceled orders
        order_revenue = Order.objects.filter(
            **base_filter,
            status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
        ).values('modell').annotate(
            total_revenue=Sum(F('price') * F('quantity')),
            order_count=Count('id')
        )
        
        design_stats = {
            'total_designs': designs.count(),
            'by_class': list(designs.values('theclass').annotate(
                count=Count('id'),
                total_likes=Count('posts__likes', distinct=True),
                total_posts=Count('posts', distinct=True)
            ).order_by('-count')),
            'by_model': list(designs.values('modell').annotate(
                count=Count('id'),
                avg_price=Avg('price'),
                total_revenue=Coalesce(
                    Subquery(
                        order_revenue.filter(
                            modell=OuterRef('modell')
                        ).values('total_revenue')
                    ),
                    Value(0),
                    output_field=DecimalField()
                ),
                order_count=Coalesce(
                    Subquery(
                        order_revenue.filter(
                            modell=OuterRef('modell')
                        ).values('order_count')
                    ),
                    Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-count')),
            'by_type': list(designs.values('type').annotate(
                count=Count('id'),
                total_revenue=Coalesce(
                    Subquery(
                        Order.objects.filter(
                            type=OuterRef('type'),
                            **base_filter,
                            status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
                        ).values('type').annotate(
                            total_revenue=Sum(F('price') * F('quantity')),
                            order_count=Count('id')
                        ).values('total_revenue')
                    ),
                    Value(0),
                    output_field=DecimalField()
                ),
                order_count=Coalesce(
                    Subquery(
                        Order.objects.filter(
                            type=OuterRef('type'),
                            **base_filter,
                            status__in=['pending', 'processing', 'shipped', 'delivered']
                        ).values('type').annotate(
                            order_count=Count('id')
                        ).values('order_count')
                    ),
                    Value(0),
                    output_field=IntegerField()
                )
            ).order_by('-count')),
            'stock_status': list(designs.values('stock').annotate(count=Count('id'))),
            'most_posted_class': list(designs.values('theclass')
                .annotate(post_count=Count('posts'))
                .order_by('-post_count')[:5]),
            'most_posted_model': list(designs.values('modell')
                .annotate(post_count=Count('posts'))
                .order_by('-post_count')[:5])
        }
        print("Design stats:", design_stats)

        # Post Analytics
        posts = Post.objects.filter(**base_filter)
        print(f"Found {posts.count()} posts")
        
        post_stats = {
            'top_liked': list(posts.annotate(
                like_count=Count('likes')
            ).filter(like_count__gt=0).order_by('-like_count').select_related('design', 'user').values(
                'id', 'caption', 'like_count', 'description', 'created_at',
                'design__image_url', 'design__modell', 'design__type', 'design__price',
                'user__username','user__profile_pic'
            )[:15]), 
            'top_commented': list(posts.annotate(
                comment_count=Count('comments')
            ).filter(comment_count__gt=0).order_by('-comment_count').select_related('design').values(
                'id', 'caption', 'comment_count', 'description', 'created_at',
                'design__image_url', 'design__modell', 'design__type', 'design__price',
                'user__username', 'user__profile_pic'
            )[:15]),
            'top_favorited': list(posts.annotate(
                favorite_count=Count('favorites')
            ).filter(favorite_count__gt=0).order_by('-favorite_count').select_related('design').values(
                'id', 'caption', 'favorite_count', 'description', 'created_at',
                'design__image_url', 'design__modell', 'design__type', 'design__price',
                'user__username','user__profile_pic'
            )[:15]),
            'time_series': list(posts.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date'))
        }
        print("Post stats:", post_stats)

        # Order Analytics
        orders = Order.objects.filter(**base_filter)
        print(f"Found {orders.count()} orders")
        
        # Calculate total revenue first, excluding canceled orders
        revenue_subquery = Order.objects.filter(
            id=OuterRef('id'),
            status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
        ).annotate(
            revenue=ExpressionWrapper(
                F('price') * Cast('quantity', FloatField()),
                output_field=DecimalField()
            )
        ).values('revenue')

        total_revenue = orders.filter(
            status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
        ).aggregate(
            total=Sum(Subquery(revenue_subquery))
        )['total'] or 0

        order_stats = {
            'total_orders': orders.count(),
            'total_revenue': total_revenue,
            'by_model': list(orders.filter(
                status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
            ).values('modell').annotate(
                quantity=Sum('quantity'),
                revenue=Sum(Subquery(revenue_subquery))
            ).order_by('-quantity')),
            'by_type': list(orders.filter(
                status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
            ).values('type').annotate(
                quantity=Sum('quantity'),
                revenue=Sum(Subquery(revenue_subquery))
            ).order_by('-quantity')),
            'status_distribution': list(orders.values('status').annotate(
                count=Count('id'),
                revenue=Sum(Subquery(revenue_subquery))
            )),
            'by_location': list(orders.filter(
                status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
            ).values('country', 'city').annotate(
                count=Count('id'),
                revenue=Sum(Subquery(revenue_subquery))
            ).order_by('-count')[:10]),
            'most_ordered_models': list(orders.filter(
                status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
            ).values('modell')
                .annotate(order_count=Count('id'))
                .order_by('-order_count')[:5]),
            'most_ordered_types': list(orders.filter(
                status__in=['pending', 'processing', 'shipped', 'delivered']  # Exclude canceled orders
            ).values('type')
                .annotate(order_count=Count('id'))
                .order_by('-order_count')[:5])
        }
        print("Order stats:", order_stats)

        # User Engagement Analytics
        users = CustomUser.objects.all()
        print(f"Found {users.count()} users")
        
        user_stats = {
            'most_active': list(users.annotate(
                post_count=Count('post', distinct=True),
                like_count=Count('post__likes', distinct=True),
                comment_count=Count('post__comments', distinct=True),
                activity_score=ExpressionWrapper(
                    (Count('post', distinct=True) * 3) +  # Posts are weighted more heavily
                    Count('post__likes', distinct=True) +  # Each like contributes to activity
                    (Count('post__comments', distinct=True) * 2),  # Comments are weighted more than likes
                    output_field=IntegerField()
                )
            ).order_by('-activity_score')[:5].values(
                'id', 
                'username', 
                'post_count', 
                'like_count', 
                'comment_count',
                'activity_score'
            )),
            'discount_eligible': list(users.annotate(
                total_likes=Count('post__likes'),
                total_posts=Count('post')
            ).filter(total_likes__gte=4).values('id', 'username', 'total_likes', 'total_posts')),
            'engagement_heatmap': list(Post.objects.annotate(
                hour=ExtractHour('created_at'),
                day=ExtractDay('created_at')
            ).values('hour', 'day').annotate(
                count=Count('id')
            ).order_by('day', 'hour'))
        }
        print("User stats:", user_stats)

        # Time-based Analytics
        time_stats = {
            'designs_over_time': list(designs.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')),
            'engagement_over_time': list(Post.objects.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                likes=Count('likes'),
                comments=Count('comments'),
                favorites=Count('favorites')
            ).order_by('date'))
        }
        print("Time stats:", time_stats)

        response_data = {
            'designs': design_stats,
            'posts': post_stats,
            'orders': order_stats,
            'users': user_stats,
            'time_series': time_stats
        }
        print("Final response data:", response_data)

        return Response(response_data)

    except Exception as e:
        print(f"Error in admin_analytics: {str(e)}")
        return Response({'error': str(e)}, status=500)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """
    API view to update an order's status. Only accessible by admin users.
    """
    if request.user.username != 'admin':
        return Response({'detail': 'Forbidden'}, status=403)
    
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.data.get('status')
        
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = new_status
        order.save()
        
        serializer = OrderSerializer(order)
        return Response(serializer.data)
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found."}, status=status.HTTP_404_NOT_FOUND)

    content = request.data.get('content')
    if not content:
        return Response({"error": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Create the comment
    comment = Comment.objects.create(user=request.user, post=post, content=content)

    # Create a notification for the post owner when a comment is added
    notification_message = f"{request.user.username} commented on your design: {content}"
    Notification.objects.create(
        user=post.design.user,  # The owner of the design
        action_user=request.user,  # The user who commented
        design=post.design,
        notification_type='comment',
        message=notification_message
    )

    return Response({"message": "Comment added.", "comment": CommentSerializer(comment).data}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def phone_products(request):

    
    if request.method == 'GET':
        print(f"Phone products request from user: {request.user.username}")
        products = PhoneProduct.objects.all()
        print(f"Found {products.count()} phone products in database")
        serializer = PhoneProductSerializer(products, many=True)
        print(f"Serialized data: {serializer.data}")
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Require authentication only for POST (creating products)

            
        data = request.data.copy()
        # Set the URL based on the model name and type
        model_name = data.get('modell', '').lower().replace(' ', '_')
        product_type = data.get('type', '')
        
        # Determine the folder based on product type
        folder = 'tough' if 'rubber' in product_type.lower() else 'normal'
        data['url'] = f'/{folder}/{model_name}.png'
        
        serializer = PhoneProductSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def phone_product_detail(request, product_id):
    if request.user.username != 'admin':
        return Response({"error": "Only admin users can access this endpoint"}, status=403)
    
    try:
        product = PhoneProduct.objects.get(id=product_id)
    except PhoneProduct.DoesNotExist:
        return Response(status=404)
    
    if request.method == 'GET':
        serializer = PhoneProductSerializer(product)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
     print("Incoming data:", request.data)  # <-- Add this
     serializer = PhoneProductSerializer(product, data=request.data, partial=True)
     if serializer.is_valid():
        serializer.save()
        Design.objects.filter(modell=product.modell, type=product.type).update(
            stock=product.stock,
            price=product.price
        )
        return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        product.delete()
        return Response(status=204)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user_status(request, user_id):
    try:
        # Check if the requesting user is an admin
        if request.user.username != 'admin':
            return Response(
                {"error": "Only administrators can update user status."},
                status=status.HTTP_403_FORBIDDEN
            ) 

        # Get the user to update
        user = CustomUser.objects.get(id=user_id)
        
        # Get the new status from the request data
        new_status = request.data.get('status')
        suspension_duration = request.data.get('suspension_duration')  # Duration in days
        
        # Validate the new status
        if new_status not in dict(CustomUser.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status value."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the user's status
        user.status = new_status
        
        # Handle suspension duration
        if new_status == 'suspended' and suspension_duration:
            try:
                duration_days = int(suspension_duration)
                user.suspension_end_date = timezone.now() + timezone.timedelta(days=duration_days)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid suspension duration."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif new_status != 'suspended':
            user.suspension_end_date = None
            
        user.save()
        
        # Return the updated user data
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "status": user.status,
            "suspension_end_date": user.suspension_end_date
        })
        
    except CustomUser.DoesNotExist:
        return Response(
            {"error": "User not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.user
            
            # Check user status
            if user.status == 'suspended':
                if user.suspension_end_date:
                    remaining_time = user.suspension_end_date - timezone.now()
                    days_remaining = remaining_time.days
                    hours_remaining = remaining_time.seconds // 3600
                    
                    if days_remaining > 0:
                        message = f"Your account has been suspended. You can log in again in {days_remaining} days."
                    else:
                        message = f"Your account has been suspended. You can log in again in {hours_remaining} hours."
                else:
                    message = f"Your account has been suspended for {user.suspension_duration}"
                    
                return Response(
                    {"detail": message},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif user.status == 'banned':
                return Response(
                    {"detail": "Your account has been banned."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # If user is active, proceed with normal token generation
            return super().post(request, *args, **kwargs)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_posts(request):
    try:
        # Check if user is admin
        if  request.user.username != 'admin':
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all posts with related data
        posts = Post.objects.select_related(
            'user',
            'design'
        ).prefetch_related(
            'likes',
            'comments',
            'favorites'
        ).order_by('-created_at')

        # Serialize the posts
        posts_data = []
        for post in posts:
            post_data = {
                'id': post.id,
                'caption': post.caption,
                'description': post.description,
                'created_at': post.created_at,
                'user__id': post.user.id,
                'user__username': post.user.username,
                'user__profile_pic': post.user.profile_pic,
                'user__status': post.user.status,
                'design__id': post.design.id,
                'design__image_url': post.design.image_url,
                'design__modell': post.design.modell,
                'design__type': post.design.type,
                'design__price': post.design.price,
                'like_count': post.likes.count(),
                'comment_count': post.comments.count(),
                'favorite_count': post.favorites.count()
            }
            posts_data.append(post_data)

        return Response(posts_data)
    except Exception as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow anonymous access
def create_anonymous_design(request):
    """
    Creates a design without requiring user authentication.
    The design will be stored with a temporary ID and can be associated with a user later.
    """
    try:
        # Get design data from request
        image_url = request.data.get('image_url')
        stock = request.data.get('stock', True)
        modell = request.data.get('modell')
        type = request.data.get('type')
        sku = request.data.get('sku', 'none')
        price = request.data.get('price')
        
        if not all([image_url, modell, type, price]):
            return Response(
                {"error": "Missing required fields: image_url, modell, type, price"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            price = Decimal(price)
            if price < 0:
                raise serializers.ValidationError("Price cannot be negative.")
        except Exception:
            return Response(
                {"error": "Invalid price format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create design without user (anonymous)
        design = Design.objects.create(
            image_url=image_url,
            user=None,  # No user associated initially
            stock=stock,
            modell=modell,
            type=type,
            sku=sku,
            price=price
        )

        # Try to classify the design
        try:
            classification = classify_design(design)  # Now returns a dict
            design.theclass = classification.get('category', 'unknown')
            design.color1 = classification.get('color1', '')
            design.color2 = classification.get('color2', '')
            design.color3 = classification.get('color3', '')
            design.save()
        except Exception as e:
            print(f"Error in classification: {e}")

        # Return design data with a temporary identifier
        serializer = DesignSerializer(design)
        return Response({
            **serializer.data,
            'is_anonymous': True,
            'temp_id': f"temp_{design.id}"  # Temporary ID for frontend
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def associate_anonymous_design(request):
    """
    Associates an anonymous design with the authenticated user.
    """
    try:
        design_id = request.data.get('design_id')
        if not design_id:
            return Response(
                {"error": "Design ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(f"Attempting to associate design {design_id} with user {request.user.username}")

        # Remove 'temp_' prefix if present
        if design_id.startswith('temp_'):
            design_id = design_id.replace('temp_', '')

        try:
            design = Design.objects.get(id=design_id, user=None)
            print(f"Found anonymous design: {design.id}, current user: {design.user}")
        except Design.DoesNotExist:
            print(f"Design {design_id} not found or already has a user")
            return Response(
                {"error": "Anonymous design not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Associate the design with the authenticated user
        design.user = request.user
        design.save()
        
        print(f"Design {design.id} associated with user {request.user.username}")

        serializer = DesignSerializer(design)
        response_data = {
            **serializer.data,
            'is_anonymous': False,
            'message': 'Design successfully associated with your account'
        }
        
        print(f"Returning response: {response_data}")
        
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in associate_anonymous_design: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def test_design_null_user(request, design_id):
    """
    Test endpoint to check if a design can have a null user
    """
    try:
        design = Design.objects.get(id=design_id)
        return Response({
            'design_id': design.id,
            'user': design.user.username if design.user else None,
            'is_anonymous': design.user is None,
            'can_have_null_user': True  # This will fail if the migration hasn't been applied
        })
    except Design.DoesNotExist:
        return Response({'error': 'Design not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def test_create_null_user_design(request):
    """
    Test endpoint to check if we can create a design with a null user
    """
    try:
        # Try to create a design with a null user
        design = Design.objects.create(
            image_url="https://test.com/test.jpg",
            user=None,  # This should work if the migration is applied
            stock=True,
            modell="test",
            type="test",
            sku="test",
            price=10.00
        )
        
        return Response({
            'success': True,
            'design_id': design.id,
            'user': design.user.username if design.user else None,
            'is_anonymous': design.user is None
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_design_user(request, design_id):
    """
    Simple endpoint to update a design's user directly
    """
    try:
        design = Design.objects.get(id=design_id)
        design.user = request.user
        design.save()
        
        serializer = DesignSerializer(design)
        return Response({
            **serializer.data,
            'message': f'Design {design_id} now belongs to {request.user.username}'
        })
    except Design.DoesNotExist:
        return Response({'error': 'Design not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import OrderSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def checkout_order(request):
    """
    Create a new order with multiple items (checkout process).
    Accepts order info and a list of items.
    """
    print('checkout_order called')
    print('Request data:', request.data)
    order_data = request.data.copy()
    user = request.user if request.user.is_authenticated else None
    serializer = OrderSerializer(data=order_data)
    if serializer.is_valid():
        order = serializer.save(user=user)
        print('Order created:', order.id, 'user:', order.user)
        return Response({
            "message": "Order created successfully",
            "order": serializer.data
        }, status=status.HTTP_201_CREATED)
    print('Order creation failed:', serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def associate_orders(request):
    print(f"Associate orders called by user: {request.user.username}")
    orders_data = request.data.get('orders', [])
    print(f"Orders data received: {orders_data}")
    if not orders_data:
        print("No orders provided")
        return Response({'error': 'No orders provided.'}, status=400)
    updated = 0
    for order in orders_data:
        order_id = order.get('id')
        print(f"Processing order ID: {order_id}")
        if not order_id:
            continue
        try:
            db_order = Order.objects.get(id=order_id, user__isnull=True)
            print(f"Found anonymous order: {db_order.id}")
            db_order.user = request.user
            db_order.save()
            updated += 1
            print(f"Order {db_order.id} associated with user {request.user.username}")
        except Order.DoesNotExist:
            print(f"Order {order_id} not found or already has user")
            continue
    print(f"Total orders associated: {updated}")
    return Response({'message': f'{updated} orders associated.'}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_order_history(request):
    print(f"User order history called by user: {request.user.username}")
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    print(f"Found {orders.count()} orders for user {request.user.username}")
    serializer = OrderSerializer(orders, many=True)
    print(f"Serialized orders: {serializer.data}")
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_orders_debug(request):
    """
    Debug endpoint to check all orders in the database
    """
    print(f"Debug orders called by user: {request.user.username}")
    
    # Get all orders
    all_orders = Order.objects.all()
    print(f"Total orders in database: {all_orders.count()}")
    
    # Get orders for this specific user
    user_orders = Order.objects.filter(user=request.user)
    print(f"Orders for user {request.user.username}: {user_orders.count()}")
    
    # Get orders with no user (anonymous)
    anonymous_orders = Order.objects.filter(user__isnull=True)
    print(f"Anonymous orders: {anonymous_orders.count()}")
    
    # Sample some orders
    sample_orders = []
    for order in all_orders[:5]:  # First 5 orders
        sample_orders.append({
            'id': order.id,
            'user': order.user.username if order.user else 'Anonymous',
            'email': order.email,
            'status': order.status,
            'created_at': order.created_at.isoformat() if order.created_at else None
        })
    
    return Response({
        'total_orders': all_orders.count(),
        'user_orders': user_orders.count(),
        'anonymous_orders': anonymous_orders.count(),
        'sample_orders': sample_orders,
        'current_user': request.user.username,
        'current_user_id': request.user.id
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_likes_favorites(request, post_id):
    """
    Debug endpoint to check like/favorite relationships for a specific post
    """
    try:
        post = Post.objects.get(id=post_id)
        
        # Get all likes for this post
        likes = Like.objects.filter(post=post)
        like_users = [like.user.username for like in likes]
        
        # Get all favorites for this post
        favorites = Favorite.objects.filter(post=post)
        favorite_users = [fav.user.username for fav in favorites]
        
        # Check if current user has liked/favorited
        current_user_liked = likes.filter(user=request.user).exists()
        current_user_favorited = favorites.filter(user=request.user).exists()
        
        return Response({
            'post_id': post_id,
            'post_caption': post.caption,
            'current_user': request.user.username,
            'all_likes': like_users,
            'all_favorites': favorite_users,
            'current_user_liked': current_user_liked,
            'current_user_favorited': current_user_favorited,
            'like_count': likes.count(),
            'favorite_count': favorites.count(),
        })
        
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_liked_posts(request):
    """
    Get all posts liked by the authenticated user.
    """
    liked_posts = Post.objects.filter(likes__user=request.user).distinct().order_by('-created_at')
    serializer = PostSerializer(liked_posts, many=True, context={'request': request})
    return Response({"liked_posts": serializer.data}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_favorited_posts(request):
    """
    Get all posts favorited by the authenticated user.
    """
    favorited_posts = Post.objects.filter(favorites__user=request.user).distinct().order_by('-created_at')
    serializer = PostSerializer(favorited_posts, many=True, context={'request': request})
    return Response({"favorited_posts": serializer.data}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_user_most_liked_posts(request, user_id):
    """Get user's posts ordered by most likes"""
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Get user's posts with like count, ordered by most likes
        posts = Post.objects.filter(user=user).annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            favorite_count=Count('favorites', distinct=True)
        ).order_by('-like_count', '-created_at')
        
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

@api_view(['GET'])
def get_user_most_commented_posts(request, user_id):
    """Get user's posts ordered by most comments"""
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Get user's posts with comment count, ordered by most comments
        posts = Post.objects.filter(user=user).annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            favorite_count=Count('favorites', distinct=True)
        ).order_by('-comment_count', '-created_at')
        
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)



