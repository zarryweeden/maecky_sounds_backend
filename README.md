# Maecky Sounds Backend

Django REST API backend for the Maecky Sounds e-commerce store — Nairobi's premier music instrument retailer.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.x + Django REST Framework |
| Database | PostgreSQL |
| Cache / Queue | Redis |
| Task Queue | Celery + Celery Beat |
| Authentication | django-allauth + djangorestframework-simplejwt (HttpOnly cookies) |
| Storage | AWS S3 (production) / local (development) |
| Payments | M-Pesa Daraja API + Stripe |
| Email | SMTP (Gmail / SendGrid) |
| Monitoring | Sentry |

---

## Quick Start (Development)

### 1. Clone and set up environment
```bash
git clone https://github.com/yourorg/maeckysounds-backend.git
cd maeckysounds-backend

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your local values
```

Minimum required for local dev:
```bash
SECRET_KEY=any-long-random-string-at-least-50-chars
DEBUG=True
DATABASE_URL=postgres://postgres:password@localhost:5432/maeckysounds
REDIS_URL=redis://127.0.0.1:6379/0
FRONTEND_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### 3. Set up the database
```bash
# Create the PostgreSQL database
createdb maeckysounds

# Run migrations
python manage.py migrate

# Seed with demo data
python manage.py seed_data
```

### 4. Run the development server
```bash
# Terminal 1 — Django
python manage.py runserver

# Terminal 2 — Celery worker (optional for local dev)
celery -A config.celery_app worker --loglevel=info

# Terminal 3 — Celery Beat scheduler (optional)
celery -A config.celery_app beat --loglevel=info
```

The API is now available at `http://localhost:8000/api/v1/`

**Admin panel:** `http://localhost:8000/store-management/`
**Credentials:** `admin@maeckysounds.co.ke` / `admin123`

---

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project → Enable Google+ API
3. Credentials → Create OAuth 2.0 Client ID
4. Set Authorized redirect URI to:
```
   http://localhost:8000/accounts/google/login/callback/
```
5. Add your Client ID and Secret to `.env`:
```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
```
6. In Django admin → Sites → Set domain to `localhost:8000`
7. In Django admin → Social Applications → Add Google:
   - Provider: Google
   - Client ID: (from step 4)
   - Secret Key: (from step 4)
   - Sites: move `localhost:8000` to Chosen sites

**OAuth flow:**
```
Frontend → GET /api/v1/auth/google/  (starts allauth flow)
         → Google consent screen
         → GET /api/v1/auth/google/finish/  (issues JWT cookies)
         → Redirect to frontend /account
```

---

## M-Pesa Setup (Daraja API)

### Sandbox (Development)

1. Register at [Safaricom Developer Portal](https://developer.safaricom.co.ke/)
2. Create an app → get Consumer Key and Consumer Secret
3. Use the test credentials:
```bash
   MPESA_CONSUMER_KEY=your-sandbox-consumer-key
   MPESA_CONSUMER_SECRET=your-sandbox-consumer-secret
   MPESA_SHORTCODE=174379
   MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
   MPESA_ENVIRONMENT=sandbox
```
4. For callbacks in local dev, use [ngrok](https://ngrok.com/):
```bash
   ngrok http 8000
   # Copy the https URL and set:
   MPESA_CALLBACK_URL=https://your-ngrok-url.ngrok.io/api/v1/payments/mpesa/callback/
```

### Payment Flow
```
POST /api/v1/payments/mpesa/initiate/
  { "order_id": "uuid", "phone": "0712345678" }
  → Safaricom sends STK Push to customer's phone
  → Customer enters PIN
  → Safaricom calls /api/v1/payments/mpesa/callback/
  → Backend confirms payment, updates order to CONFIRMED
  → Sends confirmation email
```

**Test phone number for sandbox:** `254708374149`

---

## Stripe Setup

1. Create account at [stripe.com](https://stripe.com)
2. Get test keys from Dashboard → Developers → API Keys
3. Add to `.env`:
```bash
   STRIPE_PUBLIC_KEY=pk_test_...
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
```
4. For local webhook testing:
```bash
   stripe listen --forward-to localhost:8000/api/v1/payments/stripe/webhook/
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1/`

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `auth/signup/` | Create account |
| POST | `auth/login/` | Sign in |
| POST | `auth/logout/` | Sign out |
| POST | `auth/token/refresh/` | Refresh access token |
| GET | `auth/session/` | Get current user |
| GET | `auth/google/` | Start Google OAuth |

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `products/` | List + filter products |
| GET | `products/{slug}/` | Product detail |
| GET | `products/featured/` | Featured products |
| GET | `products/new-arrivals/` | New arrivals |
| GET | `products/on-sale/` | Sale products |
| GET | `products/bestsellers/` | Best sellers |

**Filter params:** `?category=guitars&brand=fender&min_price=10000&max_price=200000&in_stock=true&is_new=true&is_sale=true&rating=4&ordering=price`

### Cart

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `cart/` | Get cart |
| POST | `cart/items/` | Add item |
| PATCH | `cart/items/{id}/` | Update qty |
| DELETE | `cart/items/{id}/` | Remove item |
| DELETE | `cart/clear/` | Clear cart |
| POST | `cart/coupon/apply/` | Apply coupon |
| DELETE | `cart/coupon/remove/` | Remove coupon |
| POST | `cart/merge/` | Merge guest cart after login |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `orders/` | Place order |
| GET | `orders/history/` | Order history |
| GET | `orders/{order_number}/` | Order detail |
| POST | `orders/{order_number}/cancel/` | Cancel order |

### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `payments/mpesa/initiate/` | Start M-Pesa STK Push |
| POST | `payments/mpesa/callback/` | Safaricom webhook |
| POST | `payments/stripe/initiate/` | Create Stripe PaymentIntent |
| POST | `payments/stripe/confirm/` | Confirm Stripe payment |
| POST | `payments/stripe/webhook/` | Stripe webhook |

---

## Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage report
pytest --cov=apps --cov-report=html
open htmlcov/index.html
```

---

## Connecting to the React Frontend

The frontend (`FRONTEND_URL=http://localhost:3000`) communicates with this backend via:

1. **Base URL:** Set `VITE_API_BASE_URL=http://localhost:8000/api/v1` in the frontend `.env`
2. **CSRF:** The backend sets a `csrftoken` cookie — include it in POST/PUT/DELETE requests as `X-CSRFToken` header
3. **Auth:** JWT tokens are in HttpOnly cookies — the frontend does not access them directly
4. **Cart merge:** After login, call `POST /api/v1/cart/merge/` with `{ session_key: "..." }` to merge guest cart

### Example: Axios configuration for the frontend
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  withCredentials: true,  // Required for JWT cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach CSRF token to mutating requests
api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];

  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// Auto-refresh token on 401
api.interceptors.response.use(
  response => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        await api.post('/auth/token/refresh/');
        return api(error.config);
      } catch {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## Production Deployment (Heroku / Railway)
```bash
# Set production settings
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=your-production-secret-key-min-50-chars
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://...
REDIS_URL=redis://...
COOKIE_SECURE=True
CORS_ALLOWED_ORIGINS=https://yourfrontend.vercel.app

# Run migrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data  # Optional: seed demo data

# Procfile handles web + worker + beat processes
```

---

## Project Structure
```
maeckysounds-backend/
├── config/           — Django settings (base, dev, prod) + URLs + Celery
├── apps/
│   ├── users/        — Custom user model, JWT auth, Google OAuth, addresses
│   ├── products/     — Products, categories, brands, tags, search
│   ├── inventory/    — Stock management, reservation, audit log
│   ├── orders/       — Cart (guest + auth), orders, order items
│   ├── payments/     — M-Pesa Daraja, Stripe, payment records
│   ├── reviews/      — Product reviews, ratings, helpful votes
│   ├── wishlist/     — Saved items, move-to-cart
│   ├── coupons/      — Discount codes, validation, usage tracking
│   ├── blog/         — Blog posts, categories
│   ├── notifications/— Email templates, Celery tasks
│   └── analytics/    — Admin dashboard, sales reports, low stock
├── templates/emails/ — HTML email templates
├── tests/            — pytest test suite
└── scripts/          — Management commands (seed_data)
```

---

## Coupon Codes (Demo)

| Code | Discount | Minimum Order |
|------|----------|---------------|
| `WELCOME10` | 10% off | KES 5,000 |
| `SAVE20` | 20% off (max KES 20,000) | KES 50,000 |
| `FREESHIP` | Free shipping | No minimum |
| `NAIROBI15` | 15% off | KES 10,000 |

---

## License

Proprietary — Maecky Sounds Ltd, Nairobi, Kenya. All rights reserved.