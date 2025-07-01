# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum



class Hashtag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"#{self.name}"



class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Reference to the user
    design = models.ForeignKey('Design', on_delete=models.CASCADE, related_name='posts')  # Reference to the design
    caption = models.CharField(max_length=255)  # Caption for the post
    description = models.TextField()  # Detailed description of the post
    hashtags = models.ManyToManyField(Hashtag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Date of post creation

    def __str__(self):
        return f"Post by {self.user.username} on {self.created_at}"


class Design(models.Model):
    image_url = models.URLField()  # The image URL of the design
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)  # Reference to the user who created it (can be null for anonymous designs)
    stock = models.BooleanField()  # Availability of the design (in stock or not)
    modell = models.CharField(max_length=100)  # Model type
    type = models.CharField(max_length=100)  # Type of design (e.g., clear case, solid case)
    sku = models.CharField(max_length=100)  # SKU for the design
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Price of the design
    theclass = models.CharField(max_length=100, blank=True, null=True)  # Classification (optional)
    created_at = models.DateTimeField(auto_now_add=True)  # When the design was created
    color1 = models.CharField(max_length=30, blank=True, null=True)
    color2 = models.CharField(max_length=30, blank=True, null=True)
    color3 = models.CharField(max_length=30, blank=True, null=True)


    def __str__(self):
        if self.user:
            return f"Design by {self.user.username} on {self.created_at}"
        else:
            return f"Anonymous design on {self.created_at}"

class Chart(models.Model):
    design = models.ForeignKey('Design', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Reference to the user who created it
    added_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"Design by {self.user.username} on {self.added_at}"

    







    
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('favorite', 'Favorite'),
        ('order', 'Order'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")  # The user who will receive the notification
    action_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actions")  # The user who performed the action
    design = models.ForeignKey('Design', on_delete=models.CASCADE)  # The design related to the notification
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)  # The type of notification (like, comment, etc.)
    message = models.CharField(max_length=255)  # The message that will be shown to the user
    is_read = models.BooleanField(default=False)  # To check whether the notification has been read
    created_at = models.DateTimeField(auto_now_add=True)  # The time when the notification was created

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.created_at}"

    class Meta:
        ordering = ['-created_at']  # Notifications are ordered by creation date (most recent first)


class CustomUser(AbstractUser):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('banned', 'Banned'),
    ]
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )
    suspension_end_date = models.DateTimeField(null=True, blank=True)
    is_discount_eligible = models.BooleanField(default=False)
    profile_pic = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        default='https://res.cloudinary.com/daalfrqob/image/upload/v1730076406/default-avatar-profile-trendy-style-social-media-user-icon-187599373_jtpxbk.webp'
    )
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',  # change this
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',  # change this
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )


    def is_discount_eligible(self):
        # Check if the user's posts have received at least two likes
        return Like.objects.filter(post__user=self).count() >= 4 
        
    def update_profile(self, first_name=None, last_name=None, email=None):
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if email is not None:
            self.email = email
        self.save()




class Like(models.Model): 
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Prevent duplicate likes

    def __str__(self):
        return f"{self.user.username} liked {self.post.id}"


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on Post {self.post.id}"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Prevent duplicate favorites

    def __str__(self):
        return f"{self.user.username} favorited {self.post.id}"






 
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.IntegerField()
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    def __str__(self):
        return f"Order #{self.id} by {self.first_name} {self.last_name} ({self.email})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()  # id from frontend
    name = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.URLField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=100)
    modell = models.CharField(max_length=100, blank=True, null=True)  # Phone model (e.g., iPhone 14, Samsung S23)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.name or 'Product'} (ID: {self.product_id}) in Order #{self.order.id}"

class UserDiscount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    valid_until = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        # Check if discount is valid by time
        valid_by_time = self.valid_until is None or self.valid_until > timezone.now()
        print(f"Discount valid by time: {valid_by_time}")

        # Check if the user has sufficient likes for the discount
        total_likes = self.calculate_total_likes()
        valid_by_likes = total_likes >= 3  # Threshold for likes (e.g., 200 likes) 
        print(f"Total likes: {total_likes}, valid by likes: {valid_by_likes}")

        return valid_by_time and valid_by_likes

    def calculate_total_likes(self):
        # Calculate the total likes across all posts by this user using aggregate for efficiency
        total_likes = Post.objects.filter(user=self.user).aggregate(
            total_likes=Sum('likes__count')
        )['total_likes'] or 0
        return total_likes

    def apply_discount(self, price):
        if self.is_valid():
            return price * (1 - self.discount_percentage / 100)
        return price
    

class Report(models.Model):
    content_id = models.IntegerField()  # ID of the reported content (post or comment)
    content_type = models.CharField(max_length=10, choices=[
        ('post', 'Post'),
        ('comment', 'Comment')
    ])
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved')
    ], default='pending')
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reported_by.username} on {self.created_at}"

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], default='medium')
    status = models.CharField(max_length=10, choices=[
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ], default='draft')
    publish_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=10, choices=[
        ('text', 'Text'),
        ('image', 'Image')
    ], default='text')
    image_url = models.URLField(max_length=500, blank=True, null=True)
    position = models.IntegerField(default=0)  # For ordering image announcements in the gifts section

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    class Meta:
        ordering = ['-publish_date', '-created_at']

class PhoneProduct(models.Model):
    type = models.CharField(max_length=100)  # e.g., 'customed rubber case', 'customed clear case'
    modell = models.CharField(max_length=100)  # e.g., 'iphone 14', 'samsung s23'
    stock = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=30.00)
    url = models.URLField(max_length=500, blank=True, null=True)  # URL for the phone image

    def __str__(self):
        return f"{self.modell} - {self.type}"

    class Meta:
        unique_together = ('type', 'modell')  # Prevent duplicate products

# Create your models here.
