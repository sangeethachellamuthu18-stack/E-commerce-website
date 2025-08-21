from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    path('admin_panel/register/', views.admin_register, name='admin_register'),
    path('admin_panel/dashboard', views.admin_dashboard, name='admin_dashboard'),
    path('admin_panel/customers', views.admin_customer, name='admin_customer'),  # ✅ keep only this
    path('admin_panel/orders', views.admin_orders, name='admin_orders'),
    path('admin_panel/products', views.admin_products, name='admin_products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('logout/', views.logout, name='logout'),
]
