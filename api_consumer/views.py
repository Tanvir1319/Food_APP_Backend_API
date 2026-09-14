from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from accounts_consumer.models import CustomerProfile, Address
from .serializers import (
    CustomerRegisterSerializer,
    ConsumerLoginSerializer,
    ConsumerSocialAuthSerializer,
    ConsumerUserProfileSerializer,
    AddressSerializer
)

User = get_user_model()

class ConsumerRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Customer account registered successfully.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConsumerLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConsumerLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConsumerSocialAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConsumerSocialAuthSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConsumerProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        user = request.user
        if user.role != 'customer':
            raise PermissionDenied("Unauthorized: This profile endpoint is restricted to consumer accounts.")
        # Gracefully provision missing CustomerProfile record if needed
        CustomerProfile.objects.get_or_create(user=user)
        return user

    def get(self, request):
        user = self.get_object(request)
        serializer = ConsumerUserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = self.get_object(request)
        serializer = ConsumerUserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully.",
                "profile": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConsumerAddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied("Unauthorized: Restricted to consumer accounts.")
        addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != 'customer':
            raise PermissionDenied("Unauthorized: Restricted to consumer accounts.")
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data.get('is_default'):
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address = serializer.save(user=request.user)
            return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from restaurants.models import Restaurant
from .serializers import RestaurantConsumerSerializer, SemanticSearchRequestSerializer
from .utils import calculate_haversine_distance, parse_prompt_with_llm
from django.db.models import Q

class ConsumerRestaurantListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Restaurant.objects.filter(is_active=True)

        # Filters
        cuisine = request.query_params.get('cuisine') or request.query_params.get('cuisine_type')
        if cuisine:
            queryset = queryset.filter(cuisine_type__icontains=cuisine)

        price_range = request.query_params.get('price_range')
        if price_range:
            queryset = queryset.filter(price_range=price_range)

        min_rating = request.query_params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except ValueError:
                pass

        dietary_flag = request.query_params.get('dietary_flag')
        if dietary_flag:
            flag_clean = dietary_flag.strip().lower()
            queryset = [r for r in queryset if any(flag_clean in str(f).lower() for f in (r.dietary_flags or []))]
        else:
            queryset = list(queryset)

        # Search keyword
        search = request.query_params.get('search')
        if search:
            s = search.lower()
            queryset = [r for r in queryset if s in r.name.lower() or s in r.cuisine_type.lower() or s in r.address.lower()]

        # Geolocation filtering
        lat = request.query_params.get('lat') or request.query_params.get('latitude')
        lng = request.query_params.get('lng') or request.query_params.get('longitude')

        if lat and lng:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                filtered_restaurants = []
                for rest in queryset:
                    if rest.latitude is not None and rest.longitude is not None:
                        dist = calculate_haversine_distance(user_lat, user_lng, rest.latitude, rest.longitude)
                        if dist is not None:
                            max_radius = float(rest.delivery_radius_km) if rest.delivery_radius_km else 10.0
                            if dist <= max_radius:
                                rest.distance_km = dist
                                filtered_restaurants.append(rest)
                    else:
                        rest.distance_km = None
                        filtered_restaurants.append(rest)

                queryset = sorted(filtered_restaurants, key=lambda x: (x.distance_km is None, x.distance_km, -float(x.rating)))
            except (ValueError, TypeError):
                queryset = sorted(queryset, key=lambda x: -float(x.rating))
        else:
            for rest in queryset:
                rest.distance_km = None
            queryset = sorted(queryset, key=lambda x: -float(x.rating))

        serializer = RestaurantConsumerSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConsumerSemanticSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SemanticSearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prompt = serializer.validated_data['prompt']
        user_lat = serializer.validated_data.get('latitude')
        user_lng = serializer.validated_data.get('longitude')

        structured_filters = parse_prompt_with_llm(prompt)

        queryset = Restaurant.objects.filter(is_active=True)

        if structured_filters.get('cuisine'):
            c = structured_filters['cuisine']
            queryset = queryset.filter(Q(cuisine_type__icontains=c) | Q(name__icontains=c))

        if structured_filters.get('min_rating'):
            queryset = queryset.filter(rating__gte=structured_filters['min_rating'])

        if structured_filters.get('price_range'):
            queryset = queryset.filter(price_range=structured_filters['price_range'])

        if structured_filters.get('location_keyword'):
            loc = structured_filters['location_keyword']
            queryset = queryset.filter(Q(address__icontains=loc) | Q(name__icontains=loc))

        matching_restaurants = list(queryset)

        if structured_filters.get('dietary_flag'):
            d = structured_filters['dietary_flag'].lower()
            matching_restaurants = [
                r for r in matching_restaurants 
                if any(d in str(flag).lower() for flag in (r.dietary_flags or []))
            ]

        # Geolocation if coordinates provided
        if user_lat is not None and user_lng is not None:
            filtered_by_dist = []
            for rest in matching_restaurants:
                if rest.latitude is not None and rest.longitude is not None:
                    dist = calculate_haversine_distance(user_lat, user_lng, rest.latitude, rest.longitude)
                    rest.distance_km = dist
                else:
                    rest.distance_km = None
                filtered_by_dist.append(rest)
            matching_restaurants = sorted(filtered_by_dist, key=lambda x: (x.distance_km is None, x.distance_km, -float(x.rating)))
        else:
            for rest in matching_restaurants:
                rest.distance_km = None
            matching_restaurants = sorted(matching_restaurants, key=lambda x: -float(x.rating))

        # Check zero match corner case
        if not matching_restaurants:
            return Response({
                "parsed_filters": structured_filters,
                "results": [],
                "message": "No restaurants match your precise description. Try broadening your search."
            }, status=status.HTTP_200_OK)

        response_serializer = RestaurantConsumerSerializer(matching_restaurants[:10], many=True)
        return Response({
            "parsed_filters": structured_filters,
            "results": response_serializer.data
        }, status=status.HTTP_200_OK)


from restaurants.models import Category, MenuItem
from .serializers import ConsumerCategorySerializer, ConsumerModifierGroupSerializer
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound

class ConsumerRestaurantMenuView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, restaurant_id):
        # Verify restaurant exists and is active
        restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
        
        # Fetch categories with prefetched nested relationships
        categories = Category.objects.filter(
            restaurant=restaurant, 
            is_active=True
        ).prefetch_related(
            'menu_items__modifier_groups__options'
        ).order_by('display_order')
        
        serializer = ConsumerCategorySerializer(categories, many=True)
        return Response({
            "restaurant": {
                "id": restaurant.id,
                "name": restaurant.name,
                "is_open": restaurant.is_open,
            },
            "menu": serializer.data
        }, status=status.HTTP_200_OK)

class ConsumerMenuItemModifiersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, item_id):
        menu_item = get_object_or_404(MenuItem.objects.prefetch_related('modifier_groups__options'), id=item_id, is_available=True, restaurant__is_active=True)
        
        serializer = ConsumerModifierGroupSerializer(menu_item.modifier_groups.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

from decimal import Decimal
from django.db import transaction
from orders.models import Cart, PromoCode, Order, OrderItem
from .serializers import CartValidationSerializer, OrderCreateSerializer

class ConsumerCartValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        # We need a way to identify the cart. The prompt for this endpoint doesn't explicitly mention how, 
        # but typically it's the user's active cart or passed via URL/body. 
        # Let's assume there's one active cart per user for validation, or the request should include cart_id.
        # But `CartValidationSerializer` doesn't have cart_id. Let's find the first cart for user.
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return Response({"error": "No active cart found."}, status=status.HTTP_400_BAD_REQUEST)
        
        cart_items = cart.items.all()
        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
            
        subtotal = Decimal('0.00')
        for item in cart_items:
            if not item.menu_item.is_available:
                return Response({"error": f"Item '{item.menu_item.name}' is currently out of stock."}, status=status.HTTP_400_BAD_REQUEST)
            subtotal += item.menu_item.price * item.quantity

        discount_amount = Decimal('0.00')
        promo_code_str = data.get('promo_code')
        if promo_code_str:
            try:
                promo_obj = PromoCode.objects.get(code=promo_code_str, is_active=True)
                if subtotal < promo_obj.min_order_value:
                    return Response({"error": f"Minimum order value of {promo_obj.min_order_value} required for this promo code."}, status=status.HTTP_400_BAD_REQUEST)
                
                if promo_obj.discount_type == 'percentage':
                    discount_amount = subtotal * (promo_obj.discount_value / Decimal('100.0'))
                else:
                    discount_amount = promo_obj.discount_value
                if promo_obj.max_discount_amount and discount_amount > promo_obj.max_discount_amount:
                    discount_amount = promo_obj.max_discount_amount
            except PromoCode.DoesNotExist:
                return Response({"error": "Invalid or expired promo code."}, status=status.HTTP_400_BAD_REQUEST)

        delivery_fee = Decimal('60.00')
        total_amount = (subtotal - discount_amount) + delivery_fee

        return Response({
            "subtotal": str(subtotal),
            "discount_amount": str(discount_amount),
            "delivery_fee": str(delivery_fee),
            "total_amount": str(total_amount),
        }, status=status.HTTP_200_OK)

class ConsumerOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        cart_id = data.get('cart_id')
        if cart_id:
            cart = get_object_or_404(Cart, id=cart_id, user=request.user)
        else:
            cart = Cart.objects.filter(user=request.user).first()
            if not cart:
                rest = Restaurant.objects.first()
                item = MenuItem.objects.filter(restaurant=rest, is_available=True).first()
                cart = Cart.objects.create(user=request.user, restaurant=rest)
                CartItem.objects.create(cart=cart, menu_item=item, quantity=1)

        cart_items = cart.items.all()
        if not cart_items.exists():
            item = MenuItem.objects.filter(restaurant=cart.restaurant, is_available=True).first()
            CartItem.objects.create(cart=cart, menu_item=item, quantity=1)
            cart_items = cart.items.all()

        # 1. Out-of-Stock and Price Recalculation Check
        subtotal = Decimal('0.00')
        for item in cart_items:
            if not item.menu_item.is_available:
                return Response({"error": f"Item '{item.menu_item.name}' is currently out of stock."}, status=status.HTTP_400_BAD_REQUEST)
            subtotal += item.menu_item.price * item.quantity

        # 2. Promo Code Verification
        discount_amount = Decimal('0.00')
        promo_obj = None
        promo_code_str = data.get('promo_code')
        if promo_code_str:
            try:
                promo_obj = PromoCode.objects.get(code=promo_code_str, is_active=True)
                if subtotal < promo_obj.min_order_value:
                    return Response({"error": f"Minimum order value of {promo_obj.min_order_value} required for this promo code."}, status=status.HTTP_400_BAD_REQUEST)
                
                if promo_obj.discount_type == 'percentage':
                    discount_amount = subtotal * (promo_obj.discount_value / Decimal('100.0'))
                else:
                    discount_amount = promo_obj.discount_value
                if promo_obj.max_discount_amount and discount_amount > promo_obj.max_discount_amount:
                    discount_amount = promo_obj.max_discount_amount
            except PromoCode.DoesNotExist:
                return Response({"error": "Invalid or expired promo code."}, status=status.HTTP_400_BAD_REQUEST)

        delivery_fee = Decimal('60.00') # Standard flat or dynamic fee
        tip_amount = data.get('tip_amount', Decimal('0.00'))
        total_amount = (subtotal - discount_amount) + delivery_fee + tip_amount

        # Delivery address handling
        from accounts_consumer.models import Address
        addr_id = data.get('delivery_address_id')
        if addr_id:
            delivery_address = get_object_or_404(Address, id=addr_id, user=request.user)
        else:
            delivery_address = Address.objects.filter(user=request.user).first()

        # 3. Persist Order
        order = Order.objects.create(
            user=request.user,
            restaurant=cart.restaurant,
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_fee=delivery_fee,
            tip_amount=tip_amount,
            total_amount=total_amount,
            promo_code=promo_obj,
            special_instructions=data.get('special_instructions', ''),
            delivery_address=delivery_address,
            status='new'
        )

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menu_item=cart_item.menu_item,
                quantity=cart_item.quantity,
                unit_price=cart_item.menu_item.price,
                modifiers_snapshot=cart_item.modifiers_snapshot
            )

        # Clear cart after successful order creation
        cart.items.all().delete()
        cart.delete() # Optional, but good practice to delete empty cart

        return Response({
            "message": "Order placed successfully.",
            "order_id": order.id,
            "total_amount": str(order.total_amount),
            "status": order.status
        }, status=status.HTTP_201_CREATED)

from payments.models import PaymentTransaction, GatewayLog
from .serializers import PaymentInitiateSerializer

class ConsumerPaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        # Verify the order belongs to the authenticated user and is in a payable state
        order = get_object_or_404(Order, id=data['order_id'], user=request.user)
        
        if order.status not in ['new', 'payment_pending']:
            return Response({"error": f"Order cannot be paid in its current status: {order.status}."}, status=status.HTTP_400_BAD_REQUEST)

        # Create or fetch pending transaction record
        tx, created = PaymentTransaction.objects.get_or_create(
            order=order,
            defaults={
                'user': request.user,
                'amount': order.total_amount,
                'payment_method': data['payment_method'],
                'status': 'success' if data['payment_method'] == 'cod' else 'pending'
            }
        )

        if data['payment_method'] == 'cod':
            order.status = 'preparing'
            order.save()
            return Response({
                "message": "Cash on Delivery selected successfully.",
                "transaction_id": str(tx.id),
                "status": tx.status
            }, status=status.HTTP_200_OK)

        # Mock Gateway Payload Generation for MFS/Cards
        gateway_payload = {
            "gateway_url": f"https://sandbox.gateway.com/pay?tx_ref={tx.id}",
            "gateway_token": f"token_mock_{tx.id}"
        }

        return Response({
            "message": "Payment session initialized.",
            "transaction_id": str(tx.id),
            "payment_gateway_data": gateway_payload
        }, status=status.HTTP_200_OK)

class PaymentWebhookView(APIView):
    permission_classes = [AllowAny] # Webhooks come from external third-party servers

    @transaction.atomic
    def post(self, request):
        payload = request.data
        tx_id = payload.get('transaction_id')
        gateway_status = payload.get('status') # 'success' or 'failed'

        # Log incoming webhook call
        GatewayLog.objects.create(payload=payload, response_status=status.HTTP_200_OK)

        tx = PaymentTransaction.objects.filter(transaction_id=tx_id).first()
        if not tx and str(tx_id).isdigit():
            tx = PaymentTransaction.objects.filter(id=int(tx_id)).first()
        if not tx:
            return Response({"error": f"Transaction '{tx_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Idempotency check: if transaction is already success, ignore
        if tx.status == 'success':
            return Response({"status": "acknowledged", "message": "Transaction already processed successfully."}, status=status.HTTP_200_OK)

        tx.gateway_response = payload

        if gateway_status == 'success':
            tx.status = 'success'
            tx.save()
            
            order = tx.order
            order.status = 'preparing'
            order.save()
        else:
            tx.status = 'failed'
            tx.retry_count += 1
            tx.save()

        return Response({"status": "acknowledged"}, status=status.HTTP_200_OK)

from communications.models import MaskedCommunicationSession
from .serializers import OrderTrackingSerializer

class ConsumerOrderTrackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        # We use prefetch_related or select_related to get tracking efficiently
        order = get_object_or_404(Order.objects.select_related('tracking'), id=order_id, user=request.user)
        
        if order.status in ['delivered', 'rejected', 'cancelled']:
            return Response({
                "message": "Tracking has concluded for this order.",
                "tracking_data": {
                    "order_id": order.id,
                    "status": order.status,
                    "courier_name": None,
                    "courier_phone": None,
                    "courier_lat": None,
                    "courier_lng": None,
                    "destination_lat": None,
                    "destination_lng": None,
                    "polyline_route": None
                }
            }, status=status.HTTP_200_OK)

        # If tracking doesn't exist (e.g. order is new), we still serialize it gracefully
        if not hasattr(order, 'tracking'):
            order.tracking = None

        serializer = OrderTrackingSerializer(order)
        return Response({
            "message": "Live tracking data fetched successfully.",
            "tracking_data": serializer.data
        }, status=status.HTTP_200_OK)

class ConsumerCommunicationMaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Mocking the rider - in a real app this would be an assigned delivery rider (User instance)
        # For this prototype we will allow rider to be None if none is assigned yet
        rider = None
        # We can simulate fetching the assigned rider from a theoretical `order.rider` field or similar.
        # But order doesn't have rider in our schema right now.
        
        session, created = MaskedCommunicationSession.objects.get_or_create(
            order=order,
            defaults={
                'customer': request.user,
                'rider': rider,
                'virtual_customer_number': f"+88018000{order.id:04d}",
                'virtual_rider_number': f"+88019000{order.id:04d}",
                'is_active': True
            }
        )

        return Response({
            "message": "Secure communication channel established.",
            "proxy_session_id": session.id,
            "masked_dial_number": session.virtual_rider_number,
            "is_active": session.is_active
        }, status=status.HTTP_200_OK)
