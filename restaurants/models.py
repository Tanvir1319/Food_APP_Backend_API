from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Restaurant(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurants')
    name = models.CharField(max_length=255)
    cuisine_type = models.CharField(max_length=255)
    address = models.TextField()
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    delivery_radius_km = models.DecimalField(max_digits=5, decimal_places=2)
    is_open = models.BooleanField(default=True)
    prep_time_buffer_minutes = models.IntegerField(default=15)
    operating_hours = models.JSONField(default=dict, blank=True)
    price_range = models.CharField(max_length=10, default='$$')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.00)
    dietary_flags = models.JSONField(default=list, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_dietary_flag = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"

class ModifierGroup(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='modifier_groups')
    name = models.CharField(max_length=255)
    is_required = models.BooleanField(default=False)
    min_selections = models.IntegerField(default=0)
    max_selections = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.name} (for {self.menu_item.name})"

class ModifierOption(models.Model):
    modifier_group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=255)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (+{self.additional_price})"
