from django.db import models
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant, MenuItem
from accounts_consumer.models import Address

User = get_user_model()

class PromoCode(models.Model):
    DISCOUNT_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed'),
    )
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField()

    def __str__(self):
        return self.code

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='carts')
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    special_instructions = models.TextField(null=True, blank=True)
    modifiers_snapshot = models.JSONField(default=dict, blank=True)

class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('preparing', 'Preparing'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='new')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL)
    special_instructions = models.TextField(null=True, blank=True)
    delivery_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL)
    
    prep_time_buffer_minutes = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    modifiers_snapshot = models.JSONField(default=dict, blank=True)

class OrderTracking(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='tracking')
    courier_name = models.CharField(max_length=255, null=True, blank=True)
    courier_phone = models.CharField(max_length=50, null=True, blank=True)
    courier_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    courier_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    polyline_route = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
