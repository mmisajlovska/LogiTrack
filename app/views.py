from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db import transaction
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta

from .models import Order, Product, Client, Warehouse, StorageZone, WarehouseSlot, MaintenanceTask, ShipmentLog
from .forms import OrderForm, OrderStatusForm, ProductForm, ClientForm, MaintenanceTaskForm, ProductSearchForm, WarehouseForm, WarehouseSlotForm, StorageZoneForm


def sync_slot_occupied_status(slot):
	if not slot:
		return

	slot.refresh_from_db()
	slot.is_occupied = slot.products.exists()
	slot.save(update_fields=['is_occupied'])


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
	"""Dashboard showing key warehouse statistics and recent activity"""
    
	def get(self, request):
		# Calculate statistics
		total_stock = Product.objects.aggregate(total=Sum('quantity'))['total'] or 0
        
		to_be_shipped = Order.objects.filter(status='to_be_shipped').count()
		picked = Order.objects.filter(status='picked').count()
		delivered = Order.objects.filter(status='delivered').count()
		total_orders = Order.objects.count()
        
		# Warehouse capacity
		warehouses = Warehouse.objects.all()
        
		# Recent orders (last 10)
		recent_orders = Order.objects.all().order_by('-created_at')[:10]
        
		# Low stock products (quantity < 10)
		low_stock = Product.objects.filter(quantity__lt=10).order_by('quantity')[:5]
        
		# Upcoming maintenance tasks
		today = datetime.now().date()
		upcoming_maintenance = MaintenanceTask.objects.filter(
			due_date__gte=today,
			status__in=['upcoming', 'overdue']
		).order_by('due_date')[:5]
        
		context = {
			'total_stock': total_stock,
			'to_be_shipped': to_be_shipped,
			'picked': picked,
			'delivered': delivered,
			'total_orders': total_orders,
			'warehouses': warehouses,
			'recent_orders': recent_orders,
			'low_stock': low_stock,
			'upcoming_maintenance': upcoming_maintenance,
		}
		return render(request, 'warehouse/dashboard.html', context)


@method_decorator(login_required, name='dispatch')
class OrderListView(ListView):
	"""List all orders with filtering by status"""
	model = Order
	template_name = 'warehouse/orders/list.html'
	context_object_name = 'orders'
	paginate_by = 10
    
	def get_queryset(self):
		status = self.request.GET.get('status', '')
		queryset = Order.objects.all().order_by('-created_at')
		if status:
			queryset = queryset.filter(status=status)
		return queryset
    
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['statuses'] = [
			('', 'All'),
			('to_be_shipped', 'To Be Shipped'),
			('picked', 'Picked'),
			('packed', 'Packed'),
			('sent', 'Sent'),
			('delivered', 'Delivered'),
			('returned', 'Returned'),
			('cancelled', 'Cancelled'),
			('unpaid', 'Unpaid'),
		]
		context['current_status'] = self.request.GET.get('status', '')
		return context


@method_decorator(login_required, name='dispatch')
class OrderDetailView(DetailView):
	"""View order details with shipment log history"""
	model = Order
	template_name = 'warehouse/orders/detail.html'
	context_object_name = 'order'
    
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['logs'] = ShipmentLog.objects.filter(order=self.object).order_by('-changed_at')
		context['status_form'] = OrderStatusForm()
		return context


@method_decorator(login_required, name='dispatch')
class OrderCreateView(CreateView):
	"""Create a new order"""
	model = Order
	form_class = OrderForm
	template_name = 'warehouse/orders/form.html'
	success_url = reverse_lazy('warehouse:order-list')
    
	def form_valid(self, form):
		with transaction.atomic():
			product = Product.objects.select_for_update().get(pk=form.cleaned_data['product'].pk)
			quantity = form.cleaned_data['quantity']
			if quantity > product.quantity:
				form.add_error('quantity', f'Not enough quantity available for this product. Only {product.quantity} left.')
				return self.form_invalid(form)

			self.object = form.save(commit=False)
			self.object.save()
			product.quantity -= quantity
			product.save(update_fields=['quantity'])

		messages.success(self.request, f"Order {self.object.order_id} created successfully!")
		return redirect(self.get_success_url())


@method_decorator(login_required, name='dispatch')
class OrderUpdateView(UpdateView):
	"""Update an existing order"""
	model = Order
	form_class = OrderForm
	template_name = 'warehouse/orders/form.html'
    
	def get_success_url(self):
		return reverse_lazy('warehouse:order-detail', kwargs={'pk': self.object.pk})
    
	def form_valid(self, form):
		with transaction.atomic():
			original_order = Order.objects.select_for_update().get(pk=self.object.pk)
			new_product = Product.objects.select_for_update().get(pk=form.cleaned_data['product'].pk)
			new_quantity = form.cleaned_data['quantity']

			if original_order.product_id == new_product.pk:
				available_quantity = new_product.quantity + original_order.quantity
				if new_quantity > available_quantity:
					form.add_error('quantity', f'Not enough quantity available for this product. Only {available_quantity} left.')
					return self.form_invalid(form)

				new_product.quantity = available_quantity - new_quantity
				new_product.save(update_fields=['quantity'])
			else:
				old_product = Product.objects.select_for_update().get(pk=original_order.product_id)
				available_quantity = new_product.quantity
				if new_quantity > available_quantity:
					form.add_error('quantity', f'Not enough quantity available for this product. Only {available_quantity} left.')
					return self.form_invalid(form)

				old_product.quantity += original_order.quantity
				new_product.quantity -= new_quantity
				old_product.save(update_fields=['quantity'])
				new_product.save(update_fields=['quantity'])

			self.object = form.save()

		messages.success(self.request, "Order updated successfully!")
		return redirect(self.get_success_url())


@method_decorator(login_required, name='dispatch')
class OrderStatusUpdateView(View):
	"""Quick update order status via AJAX or form"""
    
	def post(self, request, pk):
		order = get_object_or_404(Order, pk=pk)
		form = OrderStatusForm(request.POST)
        
		if form.is_valid():
			new_status = form.cleaned_data['status']
			old_status = order.status
            
			# Create shipment log entry
			ShipmentLog.objects.create(
				order=order,
				previous_status=old_status,
				new_status=new_status,
				note=f"Status changed from {old_status} to {new_status}"
			)
            
			order.status = new_status
			order.save()
			messages.success(request, f"Order status updated to {new_status}")
		else:
			messages.error(request, "Invalid status")
        
		return redirect('warehouse:order-detail', pk=order.pk)


@method_decorator(login_required, name='dispatch')
class StorageMapView(View):
	"""Display storage zones and warehouse slots in a grid layout"""
    
	def get(self, request):
		warehouses = Warehouse.objects.prefetch_related('storagezone_set').all()
        
		# Build context with zones grouped by warehouse
		warehouse_data = []
		for warehouse in warehouses:
			zones = []
			for zone in warehouse.storagezone_set.all():
				slots = zone.warehouseslot_set.all().order_by('slot_number')
				zone_data = {
					'zone': zone,
					'slots': slots,
					'occupied_count': slots.filter(is_occupied=True).count(),
					'total_slots': slots.count(),
				}
				zones.append(zone_data)
			warehouse_data.append({
				'warehouse': warehouse,
				'zones': zones,
			})
        
		context = {
			'warehouse_data': warehouse_data,
		}
		return render(request, 'warehouse/storage/map.html', context)


@method_decorator(login_required, name='dispatch')
class StorageZoneDetailView(DetailView):
	"""Show all slots for a single zone"""
	model = StorageZone
	template_name = 'warehouse/zones/detail.html'
	context_object_name = 'zone'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['slots'] = self.object.warehouseslot_set.all().order_by('slot_number')
		return context


@method_decorator(login_required, name='dispatch')
class WarehouseSlotDetailView(DetailView):
	"""Show details for a single warehouse slot"""
	model = WarehouseSlot
	template_name = 'warehouse/slots/detail.html'
	context_object_name = 'slot'

	def get_queryset(self):
		return WarehouseSlot.objects.select_related('zone__warehouse').prefetch_related('products__client')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['products'] = self.object.products.select_related('client').all().order_by('name')
		return context


@method_decorator(login_required, name='dispatch')
class StorageZoneListView(ListView):
	"""List all storage zones"""
	model = StorageZone
	template_name = 'warehouse/zones/list.html'
	context_object_name = 'zones'
	paginate_by = 10
	ordering = ['warehouse__name', 'name']

	def get_queryset(self):
		return StorageZone.objects.select_related('warehouse').all().order_by('warehouse__name', 'name')


@method_decorator(login_required, name='dispatch')
class StorageZoneCreateView(CreateView):
	"""Create a new storage zone"""
	model = StorageZone
	form_class = StorageZoneForm
	template_name = 'warehouse/zones/form.html'
	success_url = reverse_lazy('warehouse:zone-list')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Zone {form.instance.name} created successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class StorageZoneUpdateView(UpdateView):
	"""Update an existing storage zone"""
	model = StorageZone
	form_class = StorageZoneForm
	template_name = 'warehouse/zones/form.html'
	success_url = reverse_lazy('warehouse:zone-list')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Zone {form.instance.name} updated successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class WarehouseSlotUpdateView(UpdateView):
	"""Update an existing warehouse slot"""
	model = WarehouseSlot
	form_class = WarehouseSlotForm
	template_name = 'warehouse/slots/form.html'
	context_object_name = 'slot'

	def get_success_url(self):
		return reverse_lazy('warehouse:zone-detail', kwargs={'pk': self.object.zone.pk})

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Slot {form.instance.slot_number} updated successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class StorageZoneDeleteView(View):
	"""Delete a storage zone when it is empty"""

	def post(self, request, pk):
		zone = get_object_or_404(StorageZone, pk=pk)
		if zone.warehouseslot_set.exists():
			messages.error(request, f"Zone {zone.name} cannot be deleted while it still has slots.")
			return redirect('warehouse:zone-list')

		zone_name = zone.name
		zone.delete()
		messages.success(request, f"Zone {zone_name} deleted successfully!")
		return redirect('warehouse:zone-list')


@method_decorator(login_required, name='dispatch')
class WarehouseCreateView(CreateView):
	"""Create a new warehouse"""
	model = Warehouse
	form_class = WarehouseForm
	template_name = 'warehouse/warehouses/form.html'
	success_url = reverse_lazy('warehouse:dashboard')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Warehouse {form.instance.name} created successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class WarehouseUpdateView(UpdateView):
	"""Update an existing warehouse"""
	model = Warehouse
	form_class = WarehouseForm
	template_name = 'warehouse/warehouses/form.html'
	success_url = reverse_lazy('warehouse:dashboard')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Warehouse {form.instance.name} updated successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class WarehouseDeleteView(View):
	"""Delete a warehouse"""

	def post(self, request, pk):
		warehouse = get_object_or_404(Warehouse, pk=pk)
		warehouse_name = warehouse.name
		warehouse.delete()
		messages.success(request, f"Warehouse {warehouse_name} deleted successfully!")
		return redirect('warehouse:dashboard')


@method_decorator(login_required, name='dispatch')
class WarehouseSlotCreateView(CreateView):
	"""Create a new warehouse slot"""
	model = WarehouseSlot
	form_class = WarehouseSlotForm
	template_name = 'warehouse/slots/form.html'

	def get_success_url(self):
		return reverse_lazy('warehouse:zone-detail', kwargs={'pk': self.object.zone.pk})

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Slot {form.instance.slot_number} created successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class ProductDetailApiView(View):
	"""Return product details for the storage-map modal"""

	def get(self, request, pk):
		product = get_object_or_404(Product.objects.select_related('client', 'warehouse_slot__zone'), pk=pk)
		return JsonResponse({
			'id': product.pk,
			'name': product.name,
			'sku': product.sku,
			'quantity': product.quantity,
			'client': product.client.name,
			'slot': product.warehouse_slot.slot_number if product.warehouse_slot else None,
			'zone': product.warehouse_slot.zone.name if product.warehouse_slot else None,
		})


@method_decorator(login_required, name='dispatch')
class ProductListView(ListView):
	"""List all products with search capability"""
	model = Product
	template_name = 'warehouse/products/list.html'
	context_object_name = 'products'
	paginate_by = 12
    
	def get_queryset(self):
		queryset = Product.objects.all().order_by('-allocated_on')
		search = self.request.GET.get('search', '')
		if search:
			queryset = queryset.filter(
				Q(name__icontains=search) | Q(sku__icontains=search)
			)
		return queryset
    
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['search_form'] = ProductSearchForm()
		context['search_query'] = self.request.GET.get('search', '')
		return context


@method_decorator(login_required, name='dispatch')
class ProductCreateView(CreateView):
	"""Create a new product"""
	model = Product
	form_class = ProductForm
	template_name = 'warehouse/products/form.html'
	success_url = reverse_lazy('warehouse:product-list')
    
	def form_valid(self, form):
		previous_slot = None
		with transaction.atomic():
			response = super().form_valid(form)
			if self.object.warehouse_slot:
				sync_slot_occupied_status(self.object.warehouse_slot)
				previous_slot = self.object.warehouse_slot

		messages.success(self.request, f"Product {form.instance.name} created successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class ProductUpdateView(UpdateView):
	"""Update an existing product"""
	model = Product
	form_class = ProductForm
	template_name = 'warehouse/products/form.html'
	success_url = reverse_lazy('warehouse:product-list')
    
	def form_valid(self, form):
		old_slot = Product.objects.filter(pk=self.object.pk).values_list('warehouse_slot_id', flat=True).first()
		with transaction.atomic():
			response = super().form_valid(form)
			if old_slot:
				sync_slot_occupied_status(WarehouseSlot.objects.filter(pk=old_slot).first())
			if self.object.warehouse_slot:
				sync_slot_occupied_status(self.object.warehouse_slot)
		messages.success(self.request, "Product updated successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class ProductDeleteView(View):
	"""Delete a product"""
    
	def post(self, request, pk):
		product = get_object_or_404(Product, pk=pk)
		slot = product.warehouse_slot
		product_name = product.name
		product.delete()
		sync_slot_occupied_status(slot)
		messages.success(request, f"Product {product_name} deleted successfully!")
		return redirect('warehouse:product-list')


@method_decorator(login_required, name='dispatch')
class ClientListView(ListView):
	"""List all clients"""
	model = Client
	template_name = 'warehouse/clients/list.html'
	context_object_name = 'clients'
	paginate_by = 10
	ordering = ['name']


@method_decorator(login_required, name='dispatch')
class ClientCreateView(CreateView):
	"""Create a new client"""
	model = Client
	form_class = ClientForm
	template_name = 'warehouse/clients/form.html'
	success_url = reverse_lazy('warehouse:client-list')
    
	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Client {form.instance.name} created successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class ClientUpdateView(UpdateView):
	"""Update an existing client"""
	model = Client
	form_class = ClientForm
	template_name = 'warehouse/clients/form.html'
	success_url = reverse_lazy('warehouse:client-list')
    
	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, "Client updated successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class ClientDeleteView(View):
	"""Delete a client"""
    
	def post(self, request, pk):
		client = get_object_or_404(Client, pk=pk)
		client_name = client.name
		client.delete()
		messages.success(request, f"Client {client_name} deleted successfully!")
		return redirect('warehouse:client-list')


@method_decorator(login_required, name='dispatch')
class MaintenanceListView(ListView):
	"""List all maintenance tasks"""
	model = MaintenanceTask
	template_name = 'warehouse/maintenance/list.html'
	context_object_name = 'tasks'
	paginate_by = 10
	ordering = ['-due_date']


@method_decorator(login_required, name='dispatch')
class MaintenanceCreateView(CreateView):
	"""Create a new maintenance task"""
	model = MaintenanceTask
	form_class = MaintenanceTaskForm
	template_name = 'warehouse/maintenance/form.html'
	success_url = reverse_lazy('warehouse:maintenance-list')
    
	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, f"Maintenance task created successfully!")
		return response


@method_decorator(login_required, name='dispatch')
class MaintenanceUpdateView(UpdateView):
	"""Update an existing maintenance task"""
	model = MaintenanceTask
	form_class = MaintenanceTaskForm
	template_name = 'warehouse/maintenance/form.html'
	success_url = reverse_lazy('warehouse:maintenance-list')
    
	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, "Maintenance task updated successfully!")
		return response
