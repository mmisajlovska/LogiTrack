from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

# Create your models here.

class Client (models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Warehouse (models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    total_capacity = models.IntegerField()

    @property
    def used_capacity(self):
        return WarehouseSlot.objects.filter(zone__warehouse=self, is_occupied=True).count()

    @property
    def free_capacity(self):
        return self.total_capacity - self.used_capacity

    @property
    def capacity_percentage(self):
        if self.total_capacity == 0:
            return 0
        return round((self.used_capacity / self.total_capacity) * 100)

    def __str__(self):
        return self.name


class StorageZone (models.Model):
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('furniture', 'Furniture'),
        ('accessories', 'Accessories'),
        ('fresh_fruits', 'Fresh Fruits'),
        ('health_beauty', 'Health & Beauty'),
        ('home_kitchen', 'Home & Kitchen'),
        ('clothing', 'Clothing'),
        ('frozen_food', 'Frozen Food'),
        ('sporting_goods', 'Sporting Goods'),
        ('office_supplies', 'Office Supplies')
    ]
    name = models.CharField(max_length=100)
    zone_code = models.CharField(max_length=20, unique=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    total_slots = models.IntegerField()
    def __str__(self):
        return self.name
    

class WarehouseSlot (models.Model):
    zone = models.ForeignKey(StorageZone, on_delete=models.CASCADE)
    slot_number = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField(default=100)
    is_occupied = models.BooleanField(default=False)

    @property
    def used_capacity(self):
        return self.products.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def remaining_capacity(self):
        return max(self.capacity - self.used_capacity, 0)

    def refresh_occupied_status(self):
        self.is_occupied = self.products.exists()
        return self.is_occupied

    def clean(self):
        super().clean()
        if self.pk:
            if self.capacity < self.used_capacity:
                raise ValidationError({'capacity': f'Capacity cannot be lower than the {self.used_capacity} units already stored in this slot.'})

            if not self.is_occupied and self.products.exists():
                raise ValidationError({'is_occupied': 'This slot contains products and cannot be marked free.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.slot_number} ({self.zone.name} - {self.zone.category})"

    class Meta:
        unique_together = ('zone', 'slot_number')



class Product (models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    warehouse_slot = models.ForeignKey(WarehouseSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    quantity = models.IntegerField(default=0)
    rent_type = models.CharField(max_length=20, choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')], default='monthly')
    allocated_on = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)

    def clean(self):
        super().clean()
        if self.warehouse_slot and self.quantity is not None:
            other_products = Product.objects.filter(warehouse_slot=self.warehouse_slot)
            if self.pk:
                other_products = other_products.exclude(pk=self.pk)
            other_total = other_products.aggregate(total=Sum('quantity'))['total'] or 0
            available_capacity = self.warehouse_slot.capacity - other_total
            if self.quantity > available_capacity:
                raise ValidationError({'warehouse_slot': 'This slot does not have enough free capacity. Select a new slot.'})

    def __str__(self):
        return self.name
    
class Order(models.Model):
    STATUS_CHOICES = [
        ('to_be_shipped', 'To Be Shipped'),
        ('picked', 'Picked'),
        ('packed', 'Packed'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
        ('unpaid', 'Unpaid')
    ]
     
    order_id =  models.CharField(max_length=20, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    customer_name = models.CharField(max_length=200)    
    quantity = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_be_shipped')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.product_id and self.quantity:
            available_quantity = self.product.quantity
            if self.pk:
                original_order = Order.objects.filter(pk=self.pk).only('quantity', 'product_id').first()
                if original_order and original_order.product_id == self.product_id:
                    available_quantity += original_order.quantity

            if self.quantity > available_quantity:
                raise ValidationError({'quantity': f'Not enough quantity available for this product. Only {available_quantity} left.'})


class ShipmentLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='logs')
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)


class MaintenanceTask(models.Model):
    STATUS_CHOICES = [('upcoming','Upcoming'), ('done','Done'), ('overdue','Overdue')]
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    title = models.CharField(max_length=200) 
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')