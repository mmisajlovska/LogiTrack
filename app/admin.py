from django.contrib import admin

# Register your models here.

from .models import *


admin.site.register(Client)
admin.site.register(Warehouse)
admin.site.register(StorageZone)
admin.site.register(WarehouseSlot)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(ShipmentLog)
admin.site.register(MaintenanceTask)

