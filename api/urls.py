from django.urls import path
from .views import (
    MerchantMenuListCreateView, 
    MerchantMenuItemStockToggleView, 
    MerchantAnalyticsSummaryView, 
    MerchantAnalyticsRatingsView, 
    MerchantSettingsView,
    MerchantOrderListView,
    MerchantOrderStatusUpdateView,
    MerchantLoginView,
    MerchantProfileView,
    MerchantRegisterView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('merchant/auth/register/', MerchantRegisterView.as_view(), name='merchant-register'),
    path('merchant/auth/login/', MerchantLoginView.as_view(), name='merchant-login'),
    path('merchant/auth/refresh/', TokenRefreshView.as_view(), name='merchant-token-refresh'),
    path('merchant/profile/', MerchantProfileView.as_view(), name='merchant-profile'),
    path('merchant/menu-items/', MerchantMenuListCreateView.as_view(), name='merchant-menu-list-create'),
    path('merchant/menu-items/<int:item_id>/toggle-stock/', MerchantMenuItemStockToggleView.as_view(), name='merchant-menu-stock-toggle'),
    path('merchant/analytics/summary/', MerchantAnalyticsSummaryView.as_view(), name='merchant-analytics-summary'),
    path('merchant/analytics/ratings/', MerchantAnalyticsRatingsView.as_view(), name='merchant-analytics-ratings'),
    path('merchant/settings/', MerchantSettingsView.as_view(), name='merchant-settings'),
    path('merchant/orders/', MerchantOrderListView.as_view(), name='merchant-order-list'),
    path('merchant/orders/<int:order_id>/status/', MerchantOrderStatusUpdateView.as_view(), name='merchant-order-status-update'),
]

