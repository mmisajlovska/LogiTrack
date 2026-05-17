from django import forms
from django.forms import ModelForm
from .models import Order, Product, Client, MaintenanceTask, Warehouse, WarehouseSlot, StorageZone


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ['order_id', 'product', 'client', 'customer_name', 'quantity', 'cost', 'status']
        widgets = {
            'order_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter order ID'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter customer name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cost', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=Order.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'client', 'warehouse_slot', 'quantity', 'rent_type', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Stock Keeping Unit'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'warehouse_slot': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity'}),
            'rent_type': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class ClientForm(ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
        }


class MaintenanceTaskForm(ModelForm):
    class Meta:
        model = MaintenanceTask
        fields = ['warehouse', 'title', 'due_date', 'status']
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task title'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class WarehouseForm(ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'location', 'total_capacity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Warehouse name'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Warehouse location'}),
            'total_capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total capacity'}),
        }


class WarehouseSlotForm(ModelForm):
    class Meta:
        model = WarehouseSlot
        fields = ['zone', 'slot_number', 'capacity', 'is_occupied']
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'slot_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Slot number'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Slot capacity'}),
            'is_occupied': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StorageZoneForm(ModelForm):
    class Meta:
        model = StorageZone
        fields = ['name', 'zone_code', 'warehouse', 'category', 'total_slots']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zone name'}),
            'zone_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique zone code'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'total_slots': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total slots'}),
        }


class ProductSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or SKU...',
            'name': 'search'
        })
    )
