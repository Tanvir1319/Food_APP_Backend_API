
from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()

class PaymentTransaction(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
        ('card', 'Card'),
        ('wallet', 'Wallet'),
        ('cod', 'Cash on Delivery'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway_response = models.JSONField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class GatewayLog(models.Model):
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, null=True, blank=True, related_name='gateway_logs')
    payload = models.JSONField()
    response_status = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
