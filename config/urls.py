from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Customise admin site
admin.site.site_header = "Maecky Sounds Admin"
admin.site.site_title = "Maecky Sounds"
admin.site.index_title = "Store Management"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/v1/auth/", include("apps.users.urls.auth")),
    path("api/v1/users/", include("apps.users.urls.users")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/categories/", include("apps.products.category_urls")),
    path("api/v1/brands/", include("apps.products.brand_urls")),
    path("api/v1/search/", include("apps.products.search_urls")),
    path("api/v1/cart/", include("apps.orders.cart_urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/reviews/", include("apps.reviews.urls")),
    path("api/v1/wishlist/", include("apps.wishlist.urls")),
    path("api/v1/coupons/", include("apps.coupons.urls")),
    path("api/v1/admin/analytics/", include("apps.analytics.urls")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)