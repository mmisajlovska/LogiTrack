from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Orders
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order-update'),
    path('orders/<int:pk>/status/', views.OrderStatusUpdateView.as_view(), name='order-status-update'),
    
    # Storage Map
    path('storage/', views.StorageMapView.as_view(), name='storage-map'),
    path('zones/', views.StorageZoneListView.as_view(), name='zone-list'),
    path('zones/<int:pk>/', views.StorageZoneDetailView.as_view(), name='zone-detail'),
    path('zones/create/', views.StorageZoneCreateView.as_view(), name='zone-create'),
    path('zones/<int:pk>/update/', views.StorageZoneUpdateView.as_view(), name='zone-update'),
    path('zones/<int:pk>/delete/', views.StorageZoneDeleteView.as_view(), name='zone-delete'),
    path('warehouses/create/', views.WarehouseCreateView.as_view(), name='warehouse-create'),
    path('warehouses/<int:pk>/update/', views.WarehouseUpdateView.as_view(), name='warehouse-update'),
    path('warehouses/<int:pk>/delete/', views.WarehouseDeleteView.as_view(), name='warehouse-delete'),
    path('slots/<int:pk>/', views.WarehouseSlotDetailView.as_view(), name='slot-detail'),
    path('slots/create/', views.WarehouseSlotCreateView.as_view(), name='slot-create'),
    path('slots/<int:pk>/update/', views.WarehouseSlotUpdateView.as_view(), name='slot-update'),
    path('api/product/<int:pk>/', views.ProductDetailApiView.as_view(), name='product-api'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    
    # Clients
    path('clients/', views.ClientListView.as_view(), name='client-list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client-create'),
    path('clients/<int:pk>/update/', views.ClientUpdateView.as_view(), name='client-update'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client-delete'),
    
    # Maintenance
    path('maintenance/', views.MaintenanceListView.as_view(), name='maintenance-list'),
    path('maintenance/create/', views.MaintenanceCreateView.as_view(), name='maintenance-create'),
    path('maintenance/<int:pk>/update/', views.MaintenanceUpdateView.as_view(), name='maintenance-update'),
]
