from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, AuthenticationFailed
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from accounts_consumer.models import CustomerProfile, Address
from django.db import transaction

User = get_user_model()

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'title', 'street_address', 'city', 'area', 'latitude', 'longitude', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['first_name', 'last_name', 'profile_picture_url', 'preferences']

class CustomerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = ['email', 'password', 'phone_number', 'first_name', 'last_name']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        email = validated_data['email']
        username = email.split('@')[0]
        # Make sure username is unique if needed
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            role='customer',
            auth_provider='email',
            **validated_data
        )
        user.set_password(password)
        user.save()

        CustomerProfile.objects.get_or_create(
            user=user,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'preferences': {}
            }
        )
        return user

class ConsumerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('password')

        user = authenticate(username=email, password=password)
        if not user:
            # Fallback if username authentication was needed
            try:
                user_obj = User.objects.get(email__iexact=email)
                if user_obj.check_password(password):
                    user = user_obj
            except User.DoesNotExist:
                user = None

        if not user:
            raise AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationFailed("User account is inactive.")

        if user.role != 'customer':
            raise PermissionDenied("Invalid portal for merchant accounts.")

        refresh = RefreshToken.for_user(user)
        profile, _ = CustomerProfile.objects.get_or_create(user=user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'phone_number': user.phone_number,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
            }
        }

class ConsumerSocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'apple'])
    email = serializers.EmailField()
    social_id = serializers.CharField(required=False, allow_blank=True, default='')
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    profile_picture_url = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        provider = attrs.get('provider')
        social_id = attrs.get('social_id', '')
        first_name = attrs.get('first_name', '')
        last_name = attrs.get('last_name', '')
        picture = attrs.get('profile_picture_url', '')

        with transaction.atomic():
            user = User.objects.filter(email__iexact=email).first()
            if user:
                if user.role != 'customer':
                    raise PermissionDenied("Invalid portal for merchant accounts.")
                if not user.social_id and social_id:
                    user.social_id = social_id
                if user.auth_provider == 'email':
                    user.auth_provider = provider
                user.save()
                profile, _ = CustomerProfile.objects.get_or_create(user=user)
                if not profile.first_name and first_name:
                    profile.first_name = first_name
                if not profile.last_name and last_name:
                    profile.last_name = last_name
                if not profile.profile_picture_url and picture:
                    profile.profile_picture_url = picture
                profile.save()
            else:
                username = email.split('@')[0]
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    role='customer',
                    auth_provider=provider,
                    social_id=social_id
                )
                user.set_unusable_password()
                user.save()

                profile, _ = CustomerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'profile_picture_url': picture,
                        'preferences': {}
                    }
                )

            refresh = RefreshToken.for_user(user)

            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'auth_provider': user.auth_provider,
                    'first_name': profile.first_name,
                    'last_name': profile.last_name,
                }
            }

class ConsumerUserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='customer_profile.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='customer_profile.last_name', required=False, allow_blank=True)
    profile_picture_url = serializers.CharField(source='customer_profile.profile_picture_url', required=False, allow_blank=True, allow_null=True)
    preferences = serializers.JSONField(source='customer_profile.preferences', required=False)
    addresses = AddressSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'role', 'auth_provider', 'first_name', 'last_name', 'profile_picture_url', 'preferences', 'addresses']
        read_only_fields = ['id', 'email', 'role', 'auth_provider', 'addresses']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('customer_profile', {})
        
        # Update user fields
        if 'phone_number' in validated_data:
            instance.phone_number = validated_data['phone_number']
            instance.save()

        # Update customer profile fields
        profile, _ = CustomerProfile.objects.get_or_create(user=instance)
        for key, val in profile_data.items():
            setattr(profile, key, val)
        profile.save()

        return instance


from restaurants.models import Restaurant

class RestaurantConsumerSerializer(serializers.ModelSerializer):
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'cuisine_type', 'address', 'price_range', 
            'rating', 'dietary_flags', 'is_open', 'prep_time_buffer_minutes', 
            'delivery_radius_km', 'latitude', 'longitude', 'distance_km'
        ]

class SemanticSearchRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True, max_length=500)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)


from restaurants.models import Category, MenuItem, ModifierGroup, ModifierOption

class ConsumerModifierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModifierOption
        fields = ['id', 'name', 'additional_price', 'is_available']

class ConsumerModifierGroupSerializer(serializers.ModelSerializer):
    options = ConsumerModifierOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = ['id', 'name', 'is_required', 'min_selections', 'max_selections', 'options']

class ConsumerMenuItemSerializer(serializers.ModelSerializer):
    modifier_groups = ConsumerModifierGroupSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'image_url', 'is_available', 'is_dietary_flag', 'modifier_groups']

class ConsumerCategorySerializer(serializers.ModelSerializer):
    menu_items = serializers.SerializerMethodField()

from restaurants.models import Category, MenuItem, ModifierGroup, ModifierOption

class ConsumerModifierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModifierOption
        fields = ['id', 'name', 'additional_price', 'is_available']

class ConsumerModifierGroupSerializer(serializers.ModelSerializer):
    options = ConsumerModifierOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ModifierGroup
        fields = ['id', 'name', 'is_required', 'min_selections', 'max_selections', 'options']

class ConsumerMenuItemSerializer(serializers.ModelSerializer):
    modifier_groups = ConsumerModifierGroupSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'image_url', 'is_available', 'is_dietary_flag', 'modifier_groups']

class ConsumerCategorySerializer(serializers.ModelSerializer):
    menu_items = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'display_order', 'menu_items']
        
    def get_menu_items(self, obj):
        # We prefetch all items, so we can just iterate the cached items
        items = [item for item in obj.menu_items.all() if item.is_available]
        return ConsumerMenuItemSerializer(items, many=True).data

from decimal import Decimal

class CartValidationSerializer(serializers.Serializer):
    promo_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class OrderCreateSerializer(serializers.Serializer):
    cart_id = serializers.IntegerField(required=False, allow_null=True)
    promo_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tip_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), required=False)
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    delivery_address_id = serializers.IntegerField(required=False, allow_null=True)

class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(choices=['bkash', 'nagad', 'card', 'wallet', 'cod'])

class OrderTrackingSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(source='id')
    status = serializers.CharField()
    courier_name = serializers.CharField(source='tracking.courier_name', allow_null=True, required=False)
    courier_phone = serializers.CharField(source='tracking.courier_phone', allow_null=True, required=False)
    courier_lat = serializers.DecimalField(source='tracking.courier_lat', max_digits=9, decimal_places=6, allow_null=True, required=False)
    courier_lng = serializers.DecimalField(source='tracking.courier_lng', max_digits=9, decimal_places=6, allow_null=True, required=False)
    destination_lat = serializers.DecimalField(source='tracking.destination_lat', max_digits=9, decimal_places=6, allow_null=True, required=False)
    destination_lng = serializers.DecimalField(source='tracking.destination_lng', max_digits=9, decimal_places=6, allow_null=True, required=False)
    polyline_route = serializers.CharField(source='tracking.polyline_route', allow_null=True, required=False)
