from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User  # Added User import
from django.db import ProgrammingError, OperationalError  # Moved import to top
from django.db.models import Sum

from .forms import ProductForm
from .models import AdminRegister, Product, Order, OrderItem
from users.models import UsersRegister
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from users.models import Order, OrderItem  # Import from users app
from django.db.models import Q

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            admin = AdminRegister.objects.get(email=email)
            if check_password(password, admin.password):
                request.session['admin_email'] = admin.email
                messages.success(request, 'Login successful!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid email or password')
        except AdminRegister.DoesNotExist:
            messages.error(request, 'Invalid email or password')

        return render(request, 'admin_panel/admin_login.html')

    return render(request, 'admin_panel/admin_login.html')


def admin_register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        re_enter_password = request.POST.get("re_enter_password")

        if password != re_enter_password:
            messages.error(request, "Passwords don't match")
            return redirect("admin_register")

        if AdminRegister.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("admin_register")

        AdminRegister.objects.create(
            name=name,
            email=email,
            phone=phone,
            password=make_password(password),
        )
        messages.success(request, "Admin Registration Successful")
        return redirect("admin_login")

    return render(request, "admin_panel/admin_register.html")


def admin_dashboard(request):
    if 'admin_email' not in request.session:
        return redirect('admin_login')

    try:
        # Try to access UsersRegister table first
        customers_count = UsersRegister.objects.count()
        recent_users = UsersRegister.objects.all().order_by('-created_at')[:5]
    except (ProgrammingError, OperationalError):
        # Fallback to User model if UsersRegister doesn't exist
        customers_count = User.objects.count()
        recent_users = User.objects.all().order_by('-date_joined')[:5]

    try:
        orders_count = Order.objects.count()
        total_revenue = Order.objects.aggregate(total=Sum('grand_total'))['total'] or 0
    except (ProgrammingError, OperationalError):
        orders_count = 0
        total_revenue = 0

    try:
        products_count = Product.objects.count()
    except (ProgrammingError, OperationalError):
        products_count = 0

    context = {
        "customers_count": customers_count,
        "orders_count": orders_count,
        "products_count": products_count,
        "total_revenue": total_revenue,
        "recent_users": recent_users,
    }

    return render(request, 'admin_panel/dashboard.html', context)


def admin_customer(request):
    if 'admin_email' not in request.session:
        return redirect('admin_login')

    customers = User.objects.all().order_by('-date_joined')
    return render(request, "admin_panel/customers.html", {"customers": customers})


def admin_orders(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')

    # Base queryset - use users.Order model
    orders = Order.objects.all().select_related('user').prefetch_related('items')

    # Apply status filter
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Apply search filter
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        ).distinct()

    # Order by most recent first
    orders = orders.order_by('-order_date')

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'selected_status': status_filter,
        'search_query': search_query,
    }
    return render(request, 'admin_panel/orders.html', context)


def admin_products(request):
    if 'admin_email' not in request.session:
        return redirect('admin_login')

    products = Product.objects.all().order_by('-id')
    return render(request, 'admin_panel/products.html', {'products': products})


def add_product(request):
    if 'admin_email' not in request.session:
        return redirect('admin_login')

    if request.method == "POST":
        name = request.POST.get('name')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        description = request.POST.get('description')
        category = request.POST.get('category')
        image = request.FILES.get('image')

        if not name or not price or not stock or not description:
            messages.error(request, "All fields are required.")
            return redirect('add_product')

        Product.objects.create(
            name=name,
            price=price,
            stock=stock,
            description=description,
            category=category,
            image=image,
        )
        messages.success(request, "Product added successfully!")
        return redirect('admin_products')

    return render(request, 'admin_panel/add_product.html')


def edit_product(request, product_id):
    if 'admin_email' not in request.session:
        return redirect('admin_login')

    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully!")
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)

    return render(request, 'admin_panel/edit_product.html', {'form': form, 'product': product})


def delete_product(request, product_id):
    if 'admin_email' not in request.session:
        return redirect('admin_login')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully!")
        return redirect('admin_products')

    return render(request, 'admin_panel/confirm_delete.html', {'product': product})


def logout(request):
    if 'admin_email' in request.session:
        del request.session['admin_email']
    messages.success(request, "Logged out successfully!")
    return redirect('admin_login')