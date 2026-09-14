from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from restaurants.models import Restaurant, Category, MenuItem, ModifierGroup, ModifierOption
from orders.models import Order, OrderItem, Cart, CartItem, PromoCode, OrderTracking
from analytics.models import Review
from accounts_consumer.models import CustomerProfile, Address
from payments.models import PaymentTransaction, GatewayLog
from communications.models import MaskedCommunicationSession
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed database with 10 dummy records for each table in restaurants app.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding 10 dummy records for each table in restaurants app...")

        with transaction.atomic():
            # 0. Ensure 10 Users exist to act as restaurant owners or staff
            users = []
            for i in range(1, 11):
                user, _ = User.objects.get_or_create(
                    username=f'merchant_user_{i}',
                    defaults={
                        'email': f'merchant{i}@example.com',
                        'is_staff': True,
                        'role': 'merchant_owner'
                    }
                )
                user.set_password('password123')
                user.save()
                users.append(user)
            
            kitchen_staff, _ = User.objects.get_or_create(
                username='kitchen_staff_1',
                defaults={
                    'email': 'kitchen@example.com',
                    'role': 'kitchen_staff'
                }
            )
            kitchen_staff.set_password('password123')
            kitchen_staff.save()

            # 1. 10 Diverse Restaurants with Discovery Metadata
            restaurant_data = [
                ("Dhaka Spice Kitchen", "Bangladeshi", "123 Spice St, Banani, Dhaka", 8.5, "$", 4.50, ["halal"], 23.7925, 90.4078),
                ("Chittagong Mezban Ghar", "Traditional Meat", "45 Port Road, Chittagong", 10.0, "$$", 4.80, ["halal"], 22.3569, 91.7832),
                ("Sylhet Tea & Grill", "Grill & Traditional", "12 Tea Garden Rd, Sylhet", 6.0, "$$", 4.30, ["halal"], 24.8949, 91.8687),
                ("Bong Crust Pizzeria", "Italian & Fast Food", "88 Gulshan Ave, Dhaka", 5.5, "$$", 4.60, ["halal", "vegetarian"], 23.7808, 90.4192),
                ("Dragon Wok Express", "Pan-Asian", "19 Banani 11, Dhaka", 7.0, "$$", 4.40, ["halal"], 23.7937, 90.4066),
                ("Burger Artisan Lab", "Burgers & Fries", "34 Dhanmondi 27, Dhaka", 6.5, "$", 4.70, ["halal"], 23.7465, 90.3760),
                ("Old Town Biryani House", "Biryani & Kebab", "7 Nazimuddin Rd, Old Dhaka", 12.0, "$", 4.90, ["halal"], 23.7104, 90.4074),
                ("Tokyo Ramen Bar", "Japanese", "52 Pragati Sarani, Dhaka", 5.0, "$$$", 4.65, ["halal", "gluten-free"], 23.7979, 90.4234),
                ("Taco Fiesta", "Mexican", "15 Uttara Sector 3, Dhaka", 7.5, "$$", 4.35, ["halal", "vegetarian", "vegan"], 23.8759, 90.3795),
                ("Thai Orchid Lounge", "Thai", "21 Gulshan 2, Dhaka", 6.0, "$$$", 4.85, ["halal", "vegan", "gluten-free"], 23.7892, 90.4140),
            ]

            restaurants = []
            default_hours = {
                "monday": {"open": "09:00", "close": "22:00"},
                "tuesday": {"open": "09:00", "close": "22:00"},
                "wednesday": {"open": "09:00", "close": "22:00"},
                "thursday": {"open": "09:00", "close": "22:00"},
                "friday": {"open": "09:00", "close": "23:00"},
                "saturday": {"open": "10:00", "close": "23:00"},
                "sunday": {"open": "10:00", "close": "21:00"}
            }
            
            for i, (name, cuisine, addr, radius, price, rate, diet, lat, lng) in enumerate(restaurant_data):
                restaurant, _ = Restaurant.objects.update_or_create(
                    name=name,
                    defaults={
                        'owner': users[i],
                        'cuisine_type': cuisine,
                        'address': addr,
                        'is_active': True,
                        'delivery_radius_km': radius,
                        'is_open': True,
                        'prep_time_buffer_minutes': 15,
                        'operating_hours': default_hours,
                        'price_range': price,
                        'rating': rate,
                        'dietary_flags': diet,
                        'latitude': lat,
                        'longitude': lng,
                    }
                )
                restaurants.append(restaurant)

            # 2. 10 Categories
            category_data = [
                (restaurants[0], "Starters & Appetizers", 1),
                (restaurants[0], "Main Courses", 2),
                (restaurants[0], "Beverages & Drinks", 3),
                (restaurants[1], "Mezban Specials", 1),
                (restaurants[1], "Sides & Salads", 2),
                (restaurants[2], "Tandoori & Grill", 1),
                (restaurants[3], "Handcrafted Pizzas", 1),
                (restaurants[3], "Pastas & Lasagna", 2),
                (restaurants[4], "Noodles & Rice", 1),
                (restaurants[5], "Gourmet Burgers", 1),
            ]

            categories = []
            for i, (rest, cat_name, order) in enumerate(category_data):
                category, _ = Category.objects.update_or_create(
                    restaurant=rest,
                    name=cat_name,
                    defaults={
                        'display_order': order,
                        'is_active': True,
                    }
                )
                categories.append(category)

            # 3. 10 Menu Items
            menu_item_data = [
                (categories[0].restaurant, categories[0], "Crispy Samosa Platter", "Deep fried pastry with spiced potato filling", 4.99, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Vegetarian"),
                (categories[0].restaurant, categories[0], "Chicken Tikka Skewers", "Tender grilled chicken pieces infused with spices", 8.99, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
                (categories[1].restaurant, categories[1], "Special Kacchi Biryani", "Fragrant basmati rice layered with tender mutton", 16.50, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
                (categories[1].restaurant, categories[1], "Butter Chicken Delight", "Rich creamy tomato gravy with boneless chicken", 13.99, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
                (categories[2].restaurant, categories[2], "Mint Masala Chaas", "Spiced refreshing buttermilk with mint", 3.50, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Vegetarian"),
                (categories[3].restaurant, categories[3], "Traditional Beef Mezban", "Authentic spicy slow-cooked Chittagong beef", 17.00, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
                (categories[5].restaurant, categories[5], "Charcoal Grilled Tandoori", "Half chicken charred to perfection in tandoor", 12.00, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
                (categories[6].restaurant, categories[6], "Smoked Margherita Pizza", "San Marzano tomatoes, buffalo mozzarella, fresh basil", 14.50, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Vegetarian"),
                (categories[8].restaurant, categories[8], "Hakka Chicken Noodles", "Wok-tossed noodles with shredded chicken and veggies", 11.20, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
                (categories[9].restaurant, categories[9], "Smokey Double Beef Burger", "Twin smashed beef patties with cheddar and brioche bun", 12.99, "https://res.cloudinary.com/demo/image/upload/sample.jpg", True, "Halal"),
            ]

            menu_items = []
            for i, (rest, cat, name, desc, price, img, avail, dietary) in enumerate(menu_item_data):
                menu_item, _ = MenuItem.objects.update_or_create(
                    restaurant=rest,
                    name=name,
                    defaults={
                        'category': cat,
                        'description': desc,
                        'price': price,
                        'image_url': img,
                        'is_available': avail,
                        'is_dietary_flag': dietary,
                    }
                )
                menu_items.append(menu_item)

            # 4. 10 Modifier Groups
            modifier_group_data = [
                (menu_items[0], "Dipping Sauce", False, 0, 2),
                (menu_items[1], "Spice Level", True, 1, 1),
                (menu_items[2], "Rice Portion Size", True, 1, 1),
                (menu_items[2], "Egg & Salad Add-on", False, 0, 2),
                (menu_items[3], "Bread Choice", True, 1, 2),
                (menu_items[4], "Beverage Sweetness", False, 1, 1),
                (menu_items[5], "Mezban Spice Intensity", True, 1, 1),
                (menu_items[7], "Pizza Crust Style", True, 1, 1),
                (menu_items[8], "Noodle Protein Upgrade", False, 0, 1),
                (menu_items[9], "Cheese & Patty Add-ons", False, 0, 2),
            ]

            modifier_groups = []
            for i, (item, name, is_req, min_s, max_s) in enumerate(modifier_group_data):
                mg, _ = ModifierGroup.objects.update_or_create(
                    menu_item=item,
                    name=name,
                    defaults={
                        'is_required': is_req,
                        'min_selections': min_s,
                        'max_selections': max_s,
                    }
                )
                modifier_groups.append(mg)

            # 5. 10 Modifier Options
            modifier_option_data = [
                (modifier_groups[0], "Mint Chutney", 0.50, True),
                (modifier_groups[0], "Tamarind Sauce", 0.50, True),
                (modifier_groups[1], "Mild Spice", 0.00, True),
                (modifier_groups[1], "Fiery Hot", 0.75, True),
                (modifier_groups[2], "Regular Plate", 0.00, True),
                (modifier_groups[2], "Jumbo Plate", 3.00, True),
                (modifier_groups[4], "Garlic Butter Naan", 2.00, True),
                (modifier_groups[7], "Stuffed Cheese Crust", 2.50, True),
                (modifier_groups[8], "Extra Grilled Prawns", 3.50, True),
                (modifier_groups[9], "Double Smoked Cheddar", 1.50, True),
            ]

            modifier_options = []
            for i, (mg, name, add_price, avail) in enumerate(modifier_option_data):
                opt, _ = ModifierOption.objects.update_or_create(
                    modifier_group=mg,
                    name=name,
                    defaults={
                        'additional_price': add_price,
                        'is_available': avail,
                    }
                )
                modifier_options.append(opt)

            # 6. Orders & Reviews
            customer, _ = User.objects.get_or_create(username='test_customer', defaults={'email': 'cust@example.com', 'role': 'customer'})
            customer.set_password('password123')
            customer.save()
            
            now = timezone.now()
            if not Order.objects.filter(user=customer).exists():
                statuses = ['new', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered']
                for i in range(30):
                    rest = random.choice(restaurants)
                    order_date = now - timedelta(days=random.randint(0, 30))
                    
                    order, created = Order.objects.get_or_create(
                        user=customer,
                        id=i+1000, # Fake ID to allow get_or_create
                        defaults={
                            'restaurant': rest,
                            'status': random.choice(statuses),
                            'total_amount': 0.00
                        }
                    )
                    
                    if created:
                        order.created_at = order_date
                        order.save()
                        
                        total = 0
                        items_for_rest = [mi for mi in menu_items if mi.restaurant == rest]
                        if items_for_rest:
                            for _ in range(random.randint(1, 3)):
                                mi = random.choice(items_for_rest)
                                qty = random.randint(1, 3)
                                OrderItem.objects.get_or_create(order=order, menu_item=mi, defaults={'quantity': qty, 'unit_price': mi.price})
                                total += qty * mi.price
                        
                        order.total_amount = total
                        order.save()
                        
                        review, _ = Review.objects.get_or_create(
                            restaurant=rest,
                            customer=customer,
                            order=order,
                            defaults={
                                'rating': random.randint(3, 5),
                                'comment': 'Great food and service!',
                            }
                        )
                        review.created_at = order_date + timedelta(hours=2)
                        review.save()

            # 7. Additional Dummy Consumer Accounts with Profiles and Addresses
            cust1, _ = User.objects.get_or_create(
                email='customer.john@example.com',
                defaults={
                    'username': 'customer_john',
                    'role': 'customer',
                    'phone_number': '+1234567890',
                    'auth_provider': 'email'
                }
            )
            cust1.set_password('password123')
            cust1.save()

            CustomerProfile.objects.get_or_create(
                user=cust1,
                defaults={
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'preferences': {'dietary': 'Halal', 'spice_preference': 'Medium'}
                }
            )

            Address.objects.get_or_create(
                user=cust1,
                title='Home',
                defaults={
                    'street_address': 'Flat 4B, Road 12, Banani',
                    'city': 'Dhaka',
                    'area': 'Banani',
                    'latitude': 23.7937,
                    'longitude': 90.4066,
                    'is_default': True
                }
            )
            Address.objects.get_or_create(
                user=cust1,
                title='Office',
                defaults={
                    'street_address': 'Level 8, Concord Tower, Gulshan 1',
                    'city': 'Dhaka',
                    'area': 'Gulshan',
                    'latitude': 23.7781,
                    'longitude': 90.4172,
                    'is_default': False
                }
            )

            cust2, _ = User.objects.get_or_create(
                email='customer.sarah@example.com',
                defaults={
                    'username': 'customer_sarah',
                    'role': 'customer',
                    'phone_number': '+1987654321',
                    'auth_provider': 'google',
                    'social_id': 'google_oauth_sarah_12345'
                }
            )
            cust2.set_password('password123')
            cust2.save()

            CustomerProfile.objects.get_or_create(
                user=cust2,
                defaults={
                    'first_name': 'Sarah',
                    'last_name': 'Khan',
                    'preferences': {'dietary': 'Vegetarian', 'favorite_cuisine': 'Italian'}
                }
            )

            Address.objects.get_or_create(
                user=cust2,
                title='Apartment',
                defaults={
                    'street_address': 'House 45, Sector 4, Uttara',
                    'city': 'Dhaka',
                    'area': 'Uttara',
                    'latitude': 23.8683,
                    'longitude': 90.3986,
                    'is_default': True
                }
            )

            # Ensure test_customer also has a CustomerProfile
            CustomerProfile.objects.get_or_create(
                user=customer,
                defaults={
                    'first_name': 'Test',
                    'last_name': 'Customer',
                    'preferences': {}
                }
            )

        
            # 8. Seed Promo Codes
            from orders.models import PromoCode, Cart, CartItem
            PromoCode.objects.get_or_create(
                code='DISCOUNT50',
                defaults={
                    'discount_type': 'fixed',
                    'discount_value': 50.00,
                    'min_order_value': 200.00,
                    'valid_until': now + timedelta(days=365)
                }
            )
            PromoCode.objects.get_or_create(
                code='SAVE20',
                defaults={
                    'discount_type': 'percentage',
                    'discount_value': 20.00,
                    'min_order_value': 500.00,
                    'max_discount_amount': 200.00,
                    'valid_until': now + timedelta(days=365)
                }
            )
            PromoCode.objects.get_or_create(
                code='WELCOME10',
                defaults={
                    'discount_type': 'fixed',
                    'discount_value': 5.00,
                    'min_order_value': 0.00,
                    'valid_until': now + timedelta(days=365)
                }
            )

            # 9. Seed Active Carts
            cart, _ = Cart.objects.get_or_create(user=customer, restaurant=restaurants[0])
            CartItem.objects.get_or_create(
                cart=cart,
                menu_item=menu_items[0],
                defaults={'quantity': 2, 'special_instructions': 'Extra crispy'}
            )
            # Cart for customer_john (cust1)
            cart_john, _ = Cart.objects.get_or_create(id=10, defaults={'user': cust1, 'restaurant': restaurants[0]})
            CartItem.objects.get_or_create(
                cart=cart_john,
                menu_item=menu_items[0],
                defaults={'quantity': 2, 'special_instructions': 'Extra sauce'}
            )

            # Dedicated test orders for customer_john (cust1)
            addr_john = Address.objects.filter(user=cust1).first()
            Order.objects.update_or_create(
                id=200,
                defaults={
                    'user': cust1,
                    'restaurant': restaurants[0],
                    'status': 'new',
                    'subtotal': 9.98,
                    'total_amount': 69.98,
                    'delivery_address': addr_john
                }
            )
            o201, _ = Order.objects.update_or_create(
                id=201,
                defaults={
                    'user': cust1,
                    'restaurant': restaurants[0],
                    'status': 'out_for_delivery',
                    'subtotal': 18.00,
                    'total_amount': 78.00,
                    'delivery_address': addr_john
                }
            )
            OrderTracking.objects.update_or_create(
                order=o201,
                defaults={
                    'courier_name': 'Rider Ahmed',
                    'courier_phone': '+8801999999999',
                    'courier_lat': 23.7940,
                    'courier_lng': 90.4070,
                    'destination_lat': 23.7937,
                    'destination_lng': 90.4066,
                    'polyline_route': 'abc~xyz...'
                }
            )
            MaskedCommunicationSession.objects.update_or_create(
                order=o201,
                defaults={
                    'customer': cust1,
                    'virtual_customer_number': '+880180000201',
                    'virtual_rider_number': '+880190000201',
                    'is_active': True
                }
            )

        
            # 10. Seed Payment Transactions
            for o in Order.objects.all()[:5]:
                tx, _ = PaymentTransaction.objects.get_or_create(
                    order=o,
                    defaults={
                        'user': o.user,
                        'amount': o.total_amount,
                        'payment_method': 'bkash',
                        'status': 'success',
                        'transaction_id': f'TXN_MOCK_{o.id}'
                    }
                )
                GatewayLog.objects.get_or_create(
                    transaction=tx,
                    defaults={
                        'payload': {'transaction_id': str(tx.id), 'status': 'success'},
                        'response_status': 200
                    }
                )

        
            # 11. Seed Order Tracking and Masked Sessions
            for o in Order.objects.filter(status='out_for_delivery')[:3]:
                OrderTracking.objects.get_or_create(
                    order=o,
                    defaults={
                        'courier_name': 'Rider Ahmed',
                        'courier_phone': '+8801999999999',
                        'courier_lat': 23.7940,
                        'courier_lng': 90.4070,
                        'destination_lat': 23.7937,
                        'destination_lng': 90.4066,
                        'polyline_route': 'abc~xyz...'
                    }
                )
                MaskedCommunicationSession.objects.get_or_create(
                    order=o,
                    defaults={
                        'customer': o.user,
                        'virtual_customer_number': f'+88018000{o.id:04d}',
                        'virtual_rider_number': f'+88019000{o.id:04d}',
                        'is_active': True
                    }
                )

        self.stdout.write(self.style.SUCCESS("Successfully populated dummy data:"))
        self.stdout.write(f" - Restaurant count: {Restaurant.objects.count()} (at least {len(restaurants)} verified)")
        self.stdout.write(f" - Category count: {Category.objects.count()} (at least {len(categories)} verified)")
        self.stdout.write(f" - MenuItem count: {MenuItem.objects.count()} (at least {len(menu_items)} verified)")
        self.stdout.write(f" - ModifierGroup count: {ModifierGroup.objects.count()} (at least {len(modifier_groups)} verified)")
        self.stdout.write(f" - ModifierOption count: {ModifierOption.objects.count()} (at least {len(modifier_options)} verified)")
