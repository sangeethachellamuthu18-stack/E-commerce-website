from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.hashers import make_password
from admin_panel.models import Product
from .models import Wishlist, CartItem
from .models import Order, OrderItem, ShippingAddress
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib.auth import logout as auth_logout


# =======================
# User Authentication
# =======================

def users_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()  # Normalize email
        password = request.POST.get("password", "").strip()

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect("users_login")

        try:
            user_obj = User.objects.get(email=email)
            if not user_obj.is_active:
                messages.error(request, "Account is inactive. Please contact support.")
                return redirect("users_login")

            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Login successful!")
                context = {
                    'user': user,
                    'message': 'Welcome back!',
                    # Add any other context variables needed for dashboard
                }
                return render(request, 'users/dashboard.html', context)
            else:
                messages.error(request, "Incorrect password.")
                return redirect("users_login")
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return redirect("users_login")

    return render(request, "users/login.html")

def users_register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        contact = request.POST.get("contact")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords don't match")
            return redirect("users_register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("users_register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("users_register")

        # Save to Django's auth user
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)  # hashed password
        )
        user.save()

        messages.success(request, "Registration successful! Please log in.")
        return redirect("users_login")

    return render(request, "users/register.html")


# =======================
# Product Views
# =======================

@login_required
def users_dashboard(request):
    user = request.user
    wishlist_product_ids = Wishlist.objects.filter(user=user).values_list('product_id', flat=True)
    products = Product.objects.all()  # Or filter based on category/search

    context = {
        'products': products,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'users/dashboard.html', context)


# =======================
# Wishlist Views
# =======================

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'users/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"Added {product.name} to your wishlist",
            'action': 'add'
        })

    messages.success(request, f"Added {product.name} to your wishlist")
    return redirect(request.META.get('HTTP_REFERER', 'users_dashboard'))


@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(Wishlist, id=item_id, user=request.user)
    product_name = item.product.name
    item.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"Removed {product_name} from your wishlist",
            'action': 'remove'
        })

    messages.success(request, f"Removed {product_name} from your wishlist")
    return redirect('wishlist_view')


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        wishlist_item.delete()
        action = 'remove'
        message = f"Removed {product.name} from your wishlist"
    else:
        action = 'add'
        message = f"Added {product.name} to your wishlist"

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'wishlist_count': Wishlist.objects.filter(user=request.user).count()
        })

    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'users_dashboard'))


# =======================
# Cart Views
# =======================

@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')

    cart_total = sum(item.subtotal for item in cart_items)
    shipping_cost = 50 if cart_total > 0 else 0
    grand_total = cart_total + shipping_cost

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'shipping_cost': shipping_cost,
        'grand_total': grand_total,
    }
    return render(request, 'users/cart.html', context)


@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    action = request.POST.get('action')

    if action == 'increase':
        item.quantity += 1
    elif action == 'decrease' and item.quantity > 1:
        item.quantity -= 1

    item.save()

    if item.quantity < 1:
        item.delete()
        return JsonResponse({'status': 'removed'})

    return JsonResponse({
        'status': 'updated',
        'new_quantity': item.quantity,
        'new_subtotal': item.subtotal,
        'cart_total': sum(i.subtotal for i in CartItem.objects.filter(user=request.user))
    })


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return JsonResponse({
        'status': 'success',
        'cart_total': sum(i.subtotal for i in CartItem.objects.filter(user=request.user))
    })


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    with transaction.atomic():
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': 1}
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'cart_count': CartItem.objects.filter(user=request.user).count(),
            'message': f"{product.name} added to cart"
        })

    messages.success(request, f"{product.name} added to cart")
    return redirect(request.META.get('HTTP_REFERER', 'cart_view'))


# =======================
# Product Detail
# =======================

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    is_in_wishlist = Wishlist.objects.filter(
        user=request.user,
        product=product
    ).exists()

    context = {
        'product': product,
        'is_in_wishlist': is_in_wishlist,
    }
    return render(request, 'users/product_detail.html', context)


@login_required
def checkout_view(request):
    if request.method == 'POST':
        print("POST request received")

        # Process the form data
        full_name = request.POST.get('full_name')
        address_line1 = request.POST.get('address_line1')
        address_line2 = request.POST.get('address_line2')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country')
        phone = request.POST.get('phone')
        payment_method = request.POST.get('payment_method')

        # Validate required fields
        required_fields = ['full_name', 'address_line1', 'city', 'state', 'postal_code', 'country', 'phone',
                           'payment_method']
        for field in required_fields:
            if not request.POST.get(field):
                messages.error(request, f"Please fill in the {field.replace('_', ' ')} field.")
                return redirect('checkout')

        # Get cart items
        cart_items = CartItem.objects.filter(user=request.user)

        if not cart_items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect('cart_view')

        # Calculate totals
        subtotal = sum(item.subtotal for item in cart_items)
        tax = subtotal * Decimal('0.18')
        shipping = Decimal('50.00') if subtotal > 0 else Decimal('0.00')
        grand_total = subtotal + tax + shipping

        # Create order with transaction
        try:
            with transaction.atomic():
                # First create the order
                order = Order.objects.create(
                    user=request.user,
                    order_number=f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{request.user.id}",  # Generate unique order number
                    subtotal=subtotal,
                    tax_amount=tax,
                    shipping_cost=shipping,
                    grand_total=grand_total,
                    payment_method=payment_method,
                    status='pending',
                    payment_status='pending'
                )

                # Then create shipping address with the order reference
                shipping_address = ShippingAddress.objects.create(
                    user=request.user,
                    order=order,  # This is the key fix - pass the created order
                    full_name=full_name,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    country=country,
                    phone=phone
                )

                # Create order items
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item.product.id,
                        product_name=item.product.name,
                        quantity=item.quantity,
                        unit_price=item.product.price,
                        total_price=item.subtotal,
                        image_url=item.product.image.url if item.product.image else None
                    )

                # Clear the cart
                cart_items.delete()

                print(f"Order created successfully: {order.id}")
                messages.success(request, "Order placed successfully!")
                return redirect('order_success', order_id=order.id)

        except Exception as e:
            print(f"Error creating order: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f"Error processing order: {str(e)}")
            return redirect('checkout')

    # GET request - show checkout form
    cart_items = CartItem.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty!")
        return redirect('cart_view')

    subtotal = sum(item.subtotal for item in cart_items)
    tax = subtotal * Decimal('0.18')
    shipping = Decimal('50.00') if subtotal > 0 else Decimal('0.00')
    grand_total = subtotal + tax + shipping

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'grand_total': grand_total
    }
    return render(request, 'users/checkout.html', context)


@login_required
def order_success(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        return render(request, 'users/order_success.html', {'order': order})
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('users_dashboard')

def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'users/order_history.html', {'orders': orders})

def user_logout(request):
    auth_logout(request)
    # Add any additional logout logic here if needed
    return redirect('users_login')