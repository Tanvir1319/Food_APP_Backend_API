# Food App API Endpoints

---

## ⚙️ Environment Setup

Before running the server, copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Environment variables supported:
* `SECRET_KEY`: Django secret key
* `DEBUG`: Set to `True` for development, `False` for production
* `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: PostgreSQL connection credentials
* `OPENAI_API_KEY`: (Optional) API key for natural language conversational search

---

## 🏬 Merchant Panel API

> **🧪 MERCHANT TESTING TOKEN (Valid for 1 Year):**
> 
> Belongs to `merchant_user_1` (`merchant1@example.com` / `password123`):
> ```
> eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxODIwOTI2MDIyLCJpYXQiOjE3ODkzOTAwMjIsImp0aSI6IjZmN2M1Njk3NjU4NTQxNWY5NjhmZTJmODA4OThhMDZiIiwidXNlcl9pZCI6IjEifQ.vSuu90Z2FF_G1n5b9apOyAqngsEWopKKUsoF1rwuj84
> ```
> Header: `Authorization: Bearer <token>`

**POST** http://127.0.0.1:8000/api/merchant/auth/register/
- **What it does:** Role-verified registration endpoint for new restaurant owners and kitchen staff. Validates credentials and provisions merchant accounts.
- **Token Needed:** No
- **Sample Body:**
  ```json
  {
    "email": "newowner@restaurant.com",
    "password": "securepassword123"
  }
  ```
- **Success Response (201 Created):**
  ```json
  {
    "message": "Merchant account registered successfully.",
    "email": "newowner@restaurant.com",
    "role": "merchant_owner"
  }
  ```

**POST** http://127.0.0.1:8000/api/merchant/auth/login/
- **What it does:** Authenticates a merchant. Only users with roles `merchant_owner` or `kitchen_staff` are allowed. Returns JWT access and refresh tokens.
- **Token Needed:** No
- **Sample Body:**
  ```json
  {
    "email": "merchant1@example.com",
    "password": "password123"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1...",
    "access": "eyJhbGciOiJIUzI1...",
    "role": "merchant_owner",
    "email": "merchant1@example.com",
    "restaurant_id": 1
  }
  ```

**GET** http://127.0.0.1:8000/api/merchant/profile/
- **What it does:** Fetches the authenticated merchant's profile and linked restaurant data.
- **Token Needed:** Yes (Merchant Token)

**GET** http://127.0.0.1:8000/api/merchant/menu-items/
- **What it does:** Lists all menu items grouped by category for the authenticated merchant's restaurant.
- **Token Needed:** Yes (Merchant Token)

**POST** http://127.0.0.1:8000/api/merchant/menu-items/
- **What it does:** Creates a new menu item along with optional nested modifier groups (e.g. Spice Level, Size).
- **Token Needed:** Yes (Merchant Token)
- **Sample Body:**
  ```json
  {
    "category": 1,
    "name": "Smoked BBQ Smash Burger",
    "description": "Double beef patty with smoky BBQ sauce, cheddar cheese, and crispy onions.",
    "price": "8.99",
    "image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
    "is_available": true,
    "is_dietary_flag": "Halal",
    "modifier_groups": [
      {
        "name": "Choose Spice Level",
        "is_required": true,
        "min_selections": 1,
        "max_selections": 1,
        "options": [
          {
            "name": "Mild",
            "additional_price": "0.00",
            "is_available": true
          },
          {
            "name": "Extra Spicy",
            "additional_price": "0.50",
            "is_available": true
          }
        ]
      },
      {
        "name": "Add-ons",
        "is_required": false,
        "min_selections": 0,
        "max_selections": 2,
        "options": [
          {
            "name": "Extra Cheese Slice",
            "additional_price": "1.00",
            "is_available": true
          },
          {
            "name": "Jalapenos",
            "additional_price": "0.75",
            "is_available": true
          }
        ]
      }
    ]
  }
  ```

**PATCH** http://127.0.0.1:8000/api/merchant/menu-items/1/toggle-stock/
- **What it does:** Instantly toggles the `is_available` stock status of a specific menu item. (Replace `1` with any menu item ID belonging to your restaurant).
- **Token Needed:** Yes (Merchant Token)
- **Sample Body:**
  ```json
  {
    "is_available": true
  }
  ```

**GET** http://127.0.0.1:8000/api/merchant/analytics/summary/
- **What it does:** Provides a summary of daily revenue, total orders, and top-selling items.
- **Token Needed:** Yes (Merchant Token)

**GET** http://127.0.0.1:8000/api/merchant/analytics/ratings/
- **What it does:** Provides an average star rating, rating breakdown (1 to 5 stars), and a paginated list of all customer reviews.
- **Token Needed:** Yes (Merchant Token)

**GET** http://127.0.0.1:8000/api/merchant/settings/
- **What it does:** Fetches restaurant operational settings like operating hours, prep time, open/close status, and delivery radius.
- **Token Needed:** Yes (Merchant Token)

**PATCH** http://127.0.0.1:8000/api/merchant/settings/
- **What it does:** Updates operational settings (partially updates open status, prep time buffer, delivery radius, etc.).
- **Token Needed:** Yes (Merchant Token)
- **Sample Body:**
  ```json
  {
    "is_open": true,
    "prep_time_buffer_minutes": 20,
    "delivery_radius_km": 7.5
  }
  ```

**GET** http://127.0.0.1:8000/api/merchant/orders/
- **What it does:** Fetches active orders. You can optionally filter by status (e.g. `?status=new`).
- **Token Needed:** Yes (Merchant Token)

**PATCH** http://127.0.0.1:8000/api/merchant/orders/16/status/
- **What it does:** Updates order status (e.g. `preparing`, `ready_for_pickup`, `out_for_delivery`, `delivered`, `rejected`), sets custom prep time, or rejects with a reason. (Order `16` is pre-seeded for testing).
- **Token Needed:** Yes (Merchant Token)
- **Sample Body (Accepting / Updating Order):**
  ```json
  {
    "status": "preparing",
    "prep_time_buffer_minutes": 25
  }
  ```
- **Sample Body (Rejecting Order):**
  ```json
  {
    "status": "rejected",
    "rejection_reason": "Out of ingredients for the main course."
  }
  ```

---

## 🛒 Consumer App API

> **🧪 CONSUMER TESTING TOKEN (Valid for 1 Year):**
> 
> Belongs to `customer_john` (`customer.john@example.com` / `password123`):
> ```
> eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxODIwOTI5Nzk4LCJpYXQiOjE3ODkzOTM3OTgsImp0aSI6IjNmYWFhNWNlZmU2YzQ0MDVhYTg0OGZlODAwNTljOWFhIiwidXNlcl9pZCI6IjE0In0.T7FspGCURAytANy7psXgQJKjV-lLZjlX4ULT8bWTyGo
> ```
> Header: `Authorization: Bearer <token>`

**POST** http://127.0.0.1:8000/api/consumer/auth/register/
- **What it does:** Registers a new consumer customer account with hashed password and auto-created profile.
- **Token Needed:** No
- **Sample Body:**
  ```json
  {
    "email": "customer@example.com",
    "password": "password123",
    "phone_number": "+1234567890",
    "first_name": "John",
    "last_name": "Doe"
  }
  ```

**POST** http://127.0.0.1:8000/api/consumer/auth/login/
- **What it does:** Authenticates a customer (strictly rejects merchants with 403) and issues JWT access and refresh tokens.
- **Token Needed:** No
- **Sample Body:**
  ```json
  {
    "email": "customer.john@example.com",
    "password": "password123"
  }
  ```

**POST** http://127.0.0.1:8000/api/consumer/auth/social/
- **What it does:** Handles social auth token exchange for Google or Apple logins, provisioning accounts and issuing JWT tokens.
- **Token Needed:** No
- **Sample Body:**
  ```json
  {
    "provider": "google",
    "email": "alex.google@example.com",
    "social_id": "google_123456789",
    "first_name": "Alex",
    "last_name": "Smith"
  }
  ```

**GET** http://127.0.0.1:8000/api/consumer/profile/
- **What it does:** Fetches the logged-in consumer's profile, phone number, dietary/cuisine preferences, and saved delivery addresses.
- **Token Needed:** Yes (Consumer Token)

**PATCH** http://127.0.0.1:8000/api/consumer/profile/
- **What it does:** Partially updates consumer profile details like first name, phone number, and preferences.
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "first_name": "Johnny",
    "phone_number": "+1999888777",
    "preferences": {
      "dietary": "Halal",
      "spice_level": "Hot"
    }
  }
  ```

**GET** http://127.0.0.1:8000/api/consumer/addresses/
- **What it does:** Lists all saved delivery addresses for the authenticated consumer.
- **Token Needed:** Yes (Consumer Token)

**POST** http://127.0.0.1:8000/api/consumer/addresses/
- **What it does:** Adds a new delivery address for the consumer (e.g. Home, Office) with latitude, longitude, and default toggle.
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "title": "Home",
    "street_address": "Road 12, Banani",
    "city": "Dhaka",
    "area": "Banani",
    "latitude": 23.7937,
    "longitude": 90.4066,
    "is_default": true
  }
  ```

**GET** http://127.0.0.1:8000/api/consumer/restaurants/
- **What it does:** Lists filterable restaurants with distance calculation & delivery radius filtering using user coordinates (`lat`, `lng`).
- **Query Parameters:** `lat`, `lng`, `cuisine`, `price_range` (`$`, `$$`, `$$$`), `min_rating`, `dietary_flag` (`vegan`, `halal`), `search`.
- **Token Needed:** No (Public discovery catalog)
- **Example with Geolocation:**
  `http://127.0.0.1:8000/api/consumer/restaurants/?lat=23.7937&lng=90.4066`
- **Example with Filters:**
  `http://127.0.0.1:8000/api/consumer/restaurants/?cuisine=Thai&dietary_flag=vegan&price_range=$$$`

**POST** http://127.0.0.1:8000/api/consumer/search/semantic/
- **What it does:** Natural language conversational search translating unstructured prompts into database querysets.
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "prompt": "Find me spicy Thai food under 500 BDT with a high rating near Gulshan",
    "latitude": 23.7892,
    "longitude": 90.4140
  }
  ```

**GET** http://127.0.0.1:8000/api/consumer/restaurants/1/menu/
- **What it does:** Fetches the full categorized menu of restaurant `1`. (Replace `1` with any restaurant ID).
- **Token Needed:** No

**GET** http://127.0.0.1:8000/api/consumer/menu-items/1/modifiers/
- **What it does:** Fetches all modifier groups (e.g. Spice Level, Size) and nested options for menu item `1`.
- **Token Needed:** No

**POST** http://127.0.0.1:8000/api/consumer/cart/validate/
- **What it does:** Performs real-time validation of active cart items, recalculates totals securely from the DB, and checks promo codes.
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "promo_code": "WELCOME10"
  }
  ```

**POST** http://127.0.0.1:8000/api/consumer/orders/
- **What it does:** Finalizes an order securely. Converts the active cart into an Order within an atomic transaction.
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "delivery_address_id": 1,
    "promo_code": "WELCOME10",
    "tip_amount": "20.00",
    "special_instructions": "Please ring the bell"
  }
  ```

**POST** http://127.0.0.1:8000/api/consumer/payments/initiate/
- **What it does:** Initializes payment processing (bKash, Nagad, Card, Wallet, or COD). Generates a transaction ID and mock gateway URL. (Order `200` is pre-seeded in payable status).
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "order_id": 200,
    "payment_method": "bkash"
  }
  ```

**POST** http://127.0.0.1:8000/api/consumer/payments/webhook/
- **What it does:** Asynchronous webhook to handle gateway callbacks. Updates transaction and order status securely and logs the payload.
- **Token Needed:** No (External Webhook)
- **Sample Body:**
  ```json
  {
    "transaction_id": "TXN_MOCK_1",
    "status": "success"
  }
  ```

**GET** http://127.0.0.1:8000/api/consumer/orders/201/track/
- **What it does:** Provides live tracking data for order `201` including courier coordinates and polyline routes.
- **Token Needed:** Yes (Consumer Token)

**POST** http://127.0.0.1:8000/api/consumer/communications/mask/
- **What it does:** Establishes a secure masked VoIP proxy session for anonymous customer-rider communication on order `201`.
- **Token Needed:** Yes (Consumer Token)
- **Sample Body:**
  ```json
  {
    "order_id": 201
  }
  ```
