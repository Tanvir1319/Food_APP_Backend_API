from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from restaurants.models import Restaurant, Category, MenuItem
from .serializers import CategorySerializer, MenuItemSerializer, StockToggleSerializer
from rest_framework.exceptions import PermissionDenied, ValidationError

class MerchantMenuListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_restaurant(self):
        # We assume the merchant is the owner of a restaurant
        # For staff members, there would typically be a relationship, but let's check owner for now
        # Return first restaurant owned by the user, or raise 403
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if not restaurant:
            raise PermissionDenied("You do not own any restaurants.")
        return restaurant

    def get(self, request, *args, **kwargs):
        restaurant = self.get_restaurant()
        categories = Category.objects.filter(restaurant=restaurant).prefetch_related('menu_items__modifier_groups__options')
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        restaurant = self.get_restaurant()
        data = request.data
        
        # Validation for price and modifier prices
        price = data.get('price', 0)
        try:
            if float(price) < 0:
                raise ValidationError("Price cannot be negative.")
        except ValueError:
            raise ValidationError("Invalid price format.")
            
        modifier_groups = data.get('modifier_groups', [])
        for mg in modifier_groups:
            for opt in mg.get('options', []):
                opt_price = opt.get('additional_price', 0)
                try:
                    if float(opt_price) < 0:
                        raise ValidationError("Modifier option price cannot be negative.")
                except ValueError:
                    raise ValidationError("Invalid modifier option price format.")

        # Validation for category belonging to restaurant
        category_id = data.get('category')
        if not category_id:
            raise ValidationError("Category is required.")
        
        try:
            category = Category.objects.get(id=category_id, restaurant=restaurant)
        except Category.DoesNotExist:
            return Response({"error": "Category does not exist or does not belong to your restaurant."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Add restaurant context implicitly if serializer doesn't take it, but wait, MenuItem needs restaurant.
        # Let's pass it by modifying data or serializer context.
        # MenuItem model has 'restaurant' field.
        
        # It's better to explicitly save with restaurant
        serializer = MenuItemSerializer(data=data)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save(restaurant=restaurant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MerchantMenuItemStockToggleView(APIView):
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, item_id, *args, **kwargs):
        # 404 if item doesn't exist
        menu_item = get_object_or_404(MenuItem, id=item_id)
        
        # 403 if not owner
        if menu_item.restaurant.owner != request.user:
            raise PermissionDenied("You do not have permission to modify this item.")
            
        serializer = StockToggleSerializer(menu_item, data=request.data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.db.models import Sum, Count, F, Avg
from django.db.models.functions import TruncDay
from orders.models import Order, OrderItem
from analytics.models import Review
from .serializers import ReviewSerializer
from rest_framework.pagination import PageNumberPagination

class MerchantAnalyticsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({'error': 'Restaurant profile not found for this user.'}, status=status.HTTP_403_FORBIDDEN)

        # Aggregate daily revenue using database truncation
        daily_sales = (
            Order.objects.filter(restaurant=restaurant, status='delivered')
            .annotate(date=TruncDay('created_at'))
            .values('date')
            .annotate(total_revenue=Sum('total_amount'), total_orders=Count('id'))
            .order_by('-date')
        )

        # Aggregate top selling items
        top_items = (
            OrderItem.objects.filter(order__restaurant=restaurant, order__status='delivered')
            .values(item_name=F('menu_item__name'))
            .annotate(units_sold=Sum('quantity'), revenue_generated=Sum(F('quantity') * F('unit_price')))
            .order_by('-units_sold')[:5]
        )

        return Response({
            'daily_sales_performance': list(daily_sales),
            'top_selling_items': list(top_items)
        }, status=status.HTTP_200_OK)

class MerchantAnalyticsRatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({'error': 'Restaurant profile not found for this user.'}, status=status.HTTP_403_FORBIDDEN)
            
        reviews = Review.objects.filter(restaurant=restaurant)
        
        average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0
        
        rating_breakdown = list(
            reviews.values('rating')
            .annotate(count=Count('id'))
            .order_by('-rating')
        )
        
        # Format breakdown to ensure 1-5 stars are represented even if 0
        breakdown_dict = {str(r['rating']): r['count'] for r in rating_breakdown}
        formatted_breakdown = {str(i): breakdown_dict.get(str(i), 0) for i in range(1, 6)}
        
        # Paginate reviews
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_reviews = paginator.paginate_queryset(reviews.order_by('-created_at'), request)
        serializer = ReviewSerializer(paginated_reviews, many=True)
        
        return paginator.get_paginated_response({
            'average_rating': round(average_rating, 2),
            'total_reviews': reviews.count(),
            'rating_breakdown': formatted_breakdown,
            'reviews': serializer.data
        })


from .serializers import RestaurantSettingsSerializer

class MerchantSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({'error': 'Restaurant profile not found for this user.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = RestaurantSettingsSerializer(restaurant)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({'error': 'Restaurant profile not found for this user.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RestaurantSettingsSerializer(restaurant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Restaurant settings updated successfully.',
                'settings': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from .serializers import OrderSerializer, OrderStatusUpdateSerializer

class MerchantOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({'error': 'Restaurant profile not found for this user.'}, status=status.HTTP_403_FORBIDDEN)
            
        orders = Order.objects.filter(restaurant=restaurant).select_related('user').prefetch_related('items__menu_item')
        
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
            
        orders = orders.order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MerchantOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, order_id):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if not restaurant:
            return Response({'error': 'Restaurant profile not found for this user.'}, status=status.HTTP_403_FORBIDDEN)

        # Securely fetch order ensuring it belongs exclusively to the merchant's restaurant
        order = get_object_or_404(Order, id=order_id, restaurant=restaurant)

        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': f'Order #{order.id} status successfully updated.',
                'order_details': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import MerchantTokenObtainPairSerializer

class MerchantLoginView(TokenObtainPairView):
    serializer_class = MerchantTokenObtainPairSerializer

class MerchantProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        allowed_roles = ['merchant_owner', 'kitchen_staff']
        if user.role not in allowed_roles:
            return Response({'error': 'Unauthorized merchant profile access.'}, status=status.HTTP_403_FORBIDDEN)

        restaurant = user.restaurants.first()
        
        profile_data = {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'restaurant': {
                'id': restaurant.id if restaurant else None,
                'name': restaurant.name if restaurant else 'Unassigned',
                'cuisine_type': restaurant.cuisine_type if restaurant else None,
                'address': restaurant.address if restaurant else None,
            } if restaurant else None
        }
        return Response(profile_data, status=status.HTTP_200_OK)

from .serializers import MerchantRegisterSerializer
from rest_framework.permissions import AllowAny

class MerchantRegisterView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = MerchantRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Merchant account registered successfully.",
                "email": user.email,
                "role": user.role
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
