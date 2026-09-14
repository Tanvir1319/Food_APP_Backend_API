from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()

class MaskedCommunicationSession(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='communication_sessions')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_sessions')
    rider = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='rider_sessions')
    virtual_customer_number = models.CharField(max_length=50)
    virtual_rider_number = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
