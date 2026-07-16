import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import Inventory
from apps.products.models import Product, ProductVariant
from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    ApplyCouponSerializer,
    PlaceOrderSerializer,
    OrderSerializer,
    OrderListSerializer,
)
from .utils import calculate_shipping, get_estimated_delivery, build_shipping_address_snapshot
from apps.users.permissions import IsOwnerOrAdmin

logger = logging.getLogger(__name__)


# ── Cart Helpers ──────────────────────────────────────────────────────────────

def get_or_create_cart(request):
    """
    Retrieve or create a cart for the current user or session.
    Authenticated users get a user-linked cart.
    Guests get a session-linked cart.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={"user": request.user},
        )
        return cart

    # Guest cart via session
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    cart, _ = Cart.objects.get_or_create(
        session_key=session_key,
        is_active=True,
        user__isnull=True,
        defaults={"session_key": session_key},
    )
    return cart


# ── Cart Views ────────────────────────────────────────────────────────────────

class CartDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(
            cart,
            context={"request": request},
        )
        return Response(serializer.data)


class CartAddItemView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        variant_id = serializer.validated_data.get("variant_id")
        quantity = serializer.validated_data["quantity"]

        # Validate product
        try:
            product = (
                Product.objects.select_related("inventory")
                .prefetch_related("images")
                .get(id=product_id, is_active=True)
            )
        except Product.DoesNotExist:
            return Response(
                {"status": "error", "message": "Product not found or is unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate stock
        try:
            inv = product.inventory
            if inv.track_inventory and not inv.allow_backorder:
                if inv.available < quantity:
                    return Response(
                        {
                            "status": "error",
                            "message": f"Only {inv.available} units of '{product.name}' are available.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except Inventory.DoesNotExist:
            pass

        # Validate variant
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(
                    id=variant_id, product=product, is_active=True
                )
            except ProductVariant.DoesNotExist:
                return Response(
                    {"status": "error", "message": "Product variant not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        cart = get_or_create_cart(request)

        # Add or update cart item
        existing = cart.items.filter(product=product, variant=variant).first()
        if existing:
            new_qty = existing.quantity + quantity
            try:
                inv = product.inventory
                if inv.track_inventory and not inv.allow_backorder:
                    new_qty = min(new_qty, inv.available)
            except Exception:
                pass
            existing.quantity = new_qty
            existing.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(
                cart=cart,
                product=product,
                variant=variant,
                quantity=quantity,
                unit_price=variant.effective_price if variant else product.effective_price,
            )

        cart.refresh_from_db()
        return Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemUpdateView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, item_id):
        cart = get_or_create_cart(request)
        try:
            item = cart.items.select_related("product__inventory").get(id=item_id)
        except CartItem.DoesNotExist:
            return Response(
                {"status": "error", "message": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_qty = serializer.validated_data["quantity"]

        # Validate against stock
        try:
            inv = item.product.inventory
            if inv.track_inventory and not inv.allow_backorder:
                if new_qty > inv.available:
                    return Response(
                        {
                            "status": "error",
                            "message": f"Only {inv.available} units available.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except Exception:
            pass

        item.quantity = new_qty
        item.save(update_fields=["quantity"])

        cart.refresh_from_db()
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request, item_id):
        cart = get_or_create_cart(request)
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response(
                {"status": "error", "message": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.delete()
        cart.refresh_from_db()
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartClearView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        cart.coupon = None
        cart.save(update_fields=["coupon"])
        return Response(
            {"status": "success", "message": "Cart cleared."},
            status=status.HTTP_200_OK,
        )


class CartApplyCouponView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        from apps.coupons.models import Coupon
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            return Response(
                {"status": "error", "message": "Invalid or expired coupon code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = get_or_create_cart(request)
        user = request.user if request.user.is_authenticated else None

        is_valid, error_msg = coupon.is_valid(user, cart)
        if not is_valid:
            return Response(
                {"status": "error", "message": error_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart.coupon = coupon
        cart.save(update_fields=["coupon"])

        discount = coupon.calculate_discount(cart)

        return Response(
            {
                "status": "success",
                "message": f"Coupon applied! You save KES {discount:,}.",
                "discount_amount": discount,
                "cart": CartSerializer(cart, context={"request": request}).data,
            }
        )


class CartRemoveCouponView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart = get_or_create_cart(request)
        cart.coupon = None
        cart.save(update_fields=["coupon"])
        return Response(
            {
                "status": "success",
                "message": "Coupon removed.",
                "cart": CartSerializer(cart, context={"request": request}).data,
            }
        )


class CartSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        return Response(
            {
                "subtotal": cart.subtotal,
                "discount_amount": cart.discount_amount,
                "shipping_cost": cart.shipping_cost,
                "total": cart.total,
                "total_items": cart.total_items,
            }
        )


class CartMergeView(APIView):
    """
    Called after login to merge a guest cart into the user's cart.
    Frontend should call this immediately after a successful login
    if the user had items in their guest cart.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_key = request.data.get("session_key")
        if not session_key:
            return Response(
                {"status": "error", "message": "session_key is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get guest cart
        try:
            guest_cart = Cart.objects.get(
                session_key=session_key,
                is_active=True,
                user__isnull=True,
            )
        except Cart.DoesNotExist:
            return Response(
                {"status": "success", "message": "No guest cart found to merge."}
            )

        # Get or create user cart
        user_cart, _ = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={"user": request.user},
        )

        user_cart.merge_with(guest_cart)

        return Response(
            {
                "status": "success",
                "message": "Cart merged successfully.",
                "cart": CartSerializer(user_cart, context={"request": request}).data,
            }
        )


# ── Order Views ───────────────────────────────────────────────────────────────

class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get active cart
        try:
            cart = Cart.objects.prefetch_related(
                "items__product__inventory",
                "items__product__images",
                "items__variant",
            ).get(user=request.user, is_active=True)
        except Cart.DoesNotExist:
            return Response(
                {"status": "error", "message": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not cart.items.exists():
            return Response(
                {"status": "error", "message": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate all items are still in stock
        for item in cart.items.all():
            try:
                inv = item.product.inventory
                if inv.track_inventory and not inv.allow_backorder:
                    if inv.available < item.quantity:
                        return Response(
                            {
                                "status": "error",
                                "message": (
                                    f"'{item.product.name}' only has {inv.available} "
                                    f"units in stock but your cart has {item.quantity}."
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            except Inventory.DoesNotExist:
                pass

        # Build address snapshot
        address_data = data["shipping_address"]
        shipping_address = build_shipping_address_snapshot(address_data)

        # Calculate totals
        subtotal = cart.subtotal
        discount_amount = cart.discount_amount
        shipping_cost = calculate_shipping(subtotal, data["delivery_method"])
        total = max(0, subtotal - discount_amount + shipping_cost)

        # Create the order
        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_cost=shipping_cost,
            total=total,
            delivery_method=data["delivery_method"],
            shipping_address=shipping_address,
            estimated_delivery=get_estimated_delivery(data["delivery_method"]),
            coupon=cart.coupon,
            coupon_code=cart.coupon.code if cart.coupon else "",
            customer_email=request.user.email,
            customer_name=request.user.full_name or shipping_address.get("full_name", ""),
            customer_phone=shipping_address.get("phone", request.user.phone),
            customer_notes=data.get("customer_notes", ""),
        )

        # Create order items and reserve inventory
        for item in cart.items.select_related("product", "variant"):
            # Build product image URL
            primary_img = ""
            try:
                primary = item.product.images.filter(is_primary=True).first()
                if not primary:
                    primary = item.product.images.first()
                if primary:
                    primary_img = request.build_absolute_uri(primary.image.url)
            except Exception:
                pass

            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_sku=item.product.sku,
                variant_name=(
                    f"{item.variant.name}: {item.variant.value}" if item.variant else ""
                ),
                product_image=primary_img,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.line_total,
            )

            # Reserve inventory
            try:
                item.product.inventory.reserve(
                    quantity=item.quantity,
                    reference=order.order_number,
                    note=f"Reserved for order {order.order_number}",
                )
            except Exception as e:
                logger.warning(f"Could not reserve inventory for {item.product.sku}: {e}")

        # Record initial status
        from apps.orders.models import OrderStatusHistory
        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.PENDING,
            note="Order placed successfully.",
            changed_by=request.user,
        )

        # Mark cart as converted
        cart.is_active = False
        cart.save(update_fields=["is_active"])

        # Fire confirmation email
        from apps.notifications.tasks import send_order_confirmation_email
        send_order_confirmation_email.delay(str(order.id))

        # Build payment instructions
        payment_instructions = _build_payment_instructions(
            order, data["payment_method"], request
        )

        return Response(
            {
                "status": "success",
                "order": OrderSerializer(order, context={"request": request}).data,
                "payment": payment_instructions,
            },
            status=status.HTTP_201_CREATED,
        )


def _build_payment_instructions(order, payment_method, request):
    """Return frontend-ready payment instructions per method."""
    if payment_method == "mpesa":
        return {
            "method": "mpesa",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "amount": order.total,
            "instruction": (
                "Go to M-Pesa → Lipa na M-Pesa → Pay Bill, "
                "Business Number: 123456, Account: your order number."
            ),
            "initiate_url": f"/api/v1/payments/mpesa/initiate/",
        }
    if payment_method == "card":
        return {
            "method": "card",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "amount": order.total,
            "initiate_url": f"/api/v1/payments/stripe/initiate/",
        }
    if payment_method == "paypal":
        return {
            "method": "paypal",
            "order_id": str(order.id),
            "amount": order.total,
            "initiate_url": f"/api/v1/payments/paypal/initiate/",
        }
    return {
        "method": "bank",
        "order_id": str(order.id),
        "amount": order.total,
        "bank_name": "Equity Bank Kenya",
        "account_name": "Maecky Sounds Ltd",
        "account_number": "0540295071291",
        "reference": order.order_number,
    }


class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    lookup_field = "order_number"

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related("items", "status_history__changed_by")


class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_number):
        try:
            order = Order.objects.prefetch_related("items__product__inventory").get(
                order_number=order_number,
                user=request.user,
            )
        except Order.DoesNotExist:
            return Response(
                {"status": "error", "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not order.can_cancel():
            return Response(
                {
                    "status": "error",
                    "message": (
                        f"Order {order_number} cannot be cancelled. "
                        f"Current status: {order.get_status_display()}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Release reserved inventory
        for item in order.items.all():
            if item.product:
                try:
                    item.product.inventory.release(
                        quantity=item.quantity,
                        reference=order.order_number,
                        note=f"Released — order {order.order_number} cancelled by customer.",
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not release inventory for {item.product_sku}: {e}"
                    )

        order.transition_to(
            Order.Status.CANCELLED,
            note="Cancelled by customer.",
            changed_by=request.user,
        )

        return Response(
            {
                "status": "success",
                "message": f"Order {order_number} has been cancelled.",
                "order": OrderSerializer(order, context={"request": request}).data,
            }
        )