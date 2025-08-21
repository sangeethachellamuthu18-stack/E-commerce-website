from django.contrib import admin
from users.models import Order, OrderItem, ShippingAddress
from .models import Product, AdminRegister

# Inline for Order Items
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'quantity', 'unit_price', 'total_price', 'image_url')
    can_delete = False

# Inline for Shipping Address
class ShippingAddressInline(admin.TabularInline):
    model = ShippingAddress
    extra = 0
    readonly_fields = ('full_name', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'phone', 'is_default')
    can_delete = False

# Main Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'grand_total', 'payment_status', 'order_date')
    list_filter = ('status', 'payment_status', 'order_date')
    search_fields = ('order_number', 'user__username', 'user__email')
    readonly_fields = ('order_number', 'user', 'subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'grand_total', 'payment_method', 'transaction_id', 'ip_address', 'order_date')
    inlines = [OrderItemInline, ShippingAddressInline]
    list_editable = ('status', 'payment_status')

# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock')
    search_fields = ('name',)

# AdminRegister Admin
@admin.register(AdminRegister)
class AdminRegisterAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')
