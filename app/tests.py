from django.test import TestCase

from .models import StorageZone, Warehouse, WarehouseSlot


class ModelStringTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.warehouse = Warehouse.objects.create(
			name='Main Warehouse',
			location='Skopje',
			total_capacity=100,
		)
		cls.zone = StorageZone.objects.create(
			name='Zone A',
			zone_code='ZA1',
			warehouse=cls.warehouse,
			category='electronics',
			total_slots=10,
		)
		cls.slot = WarehouseSlot.objects.create(
			zone=cls.zone,
			slot_number='S-1',
			capacity=50,
		)

	def test_warehouse_str(self):
		self.assertEqual(str(self.warehouse), 'Main Warehouse')

	def test_storage_zone_str(self):
		self.assertEqual(str(self.zone), 'Zone A')

	def test_warehouse_slot_str(self):
		self.assertEqual(str(self.slot), 'S-1 (Zone A - electronics)')
