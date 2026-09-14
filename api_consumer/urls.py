from django.urls import path
from .views import (
    ConsumerRegisterView,
    ConsumerLoginView,
    ConsumerSocialAuthView,
    ConsumerProfileView,
    ConsumerAddressListCreateView,
    ConsumerRestaurantListView,
    ConsumerSemanticSearchView,
    ConsumerRestaurantMenuView,
    ConsumerMenuItemModifiersView,
    ConsumerCartValidateView,
    ConsumerOrderCreateView,
    ConsumerPaymentInitiateView,
    PaymentWebhookView,
    ConsumerOrderTrackView,
    ConsumerCommunicationMaskView
)

urlpatterns = [
    path('consumer/auth/register/', ConsumerRegisterView.as_view(), name='consumer-register'),
    path('consumer/auth/login/', ConsumerLoginView.as_view(), name='consumer-login'),
    path('consumer/auth/social/', ConsumerSocialAuthView.as_view(), name='consumer-social-auth'),
    path('consumer/profile/', ConsumerProfileView.as_view(), name='consumer-profile'),
    path('consumer/addresses/', ConsumerAddressListCreateView.as_view(), name='consumer-addresses'),
    path('consumer/restaurants/', ConsumerRestaurantListView.as_view(), name='consumer-restaurant-list'),
    path('consumer/search/semantic/', ConsumerSemanticSearchView.as_view(), name='consumer-semantic-search'),
    path('consumer/restaurants/<int:restaurant_id>/menu/', ConsumerRestaurantMenuView.as_view(), name='consumer-restaurant-menu'),
    path('consumer/menu-items/<int:item_id>/modifiers/', ConsumerMenuItemModifiersView.as_view(), name='consumer-menu-item-modifiers'),
    path('consumer/cart/validate/', ConsumerCartValidateView.as_view(), name='consumer-cart-validate'),
    path('consumer/orders/', ConsumerOrderCreateView.as_view(), name='consumer-order-create'),
    path('consumer/payments/initiate/', ConsumerPaymentInitiateView.as_view(), name='consumer-payment-initiate'),
    path('consumer/payments/webhook/', PaymentWebhookView.as_view(), name='consumer-payment-webhook'),
    path('consumer/orders/<int:order_id>/track/', ConsumerOrderTrackView.as_view(), name='consumer-order-track'),
    path('consumer/communications/mask/', ConsumerCommunicationMaskView.as_view(), name='consumer-communication-mask'),
]

