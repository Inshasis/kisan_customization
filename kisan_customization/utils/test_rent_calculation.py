# Copyright (c) 2026, Hidayatali and contributors

from frappe.tests.utils import FrappeTestCase

from kisan_customization.kisan_customization.doctype.bag_configuration.naming import (
	build_bag_configuration_name,
)
from kisan_customization.utils.rent_calculation import (
	compute_general_chargeable_days,
	compute_rent_line,
	compute_specific_chargeable_months,
)


class TestRentCalculation(FrappeTestCase):
	def _mock_settings(self):
		return type(
			"Settings",
			(),
			{
				"minimum_chargeable_days": 15,
				"extra_days_after_minimum": 2,
				"days_per_month": 30,
				"specific_minimum_days": 30,
				"specific_extra_days": 2,
				"specific_days_per_month": 30,
			},
		)()

	def test_general_minimum_days(self):
		settings = self._mock_settings()
		self.assertEqual(compute_general_chargeable_days(14, settings), 15)
		self.assertEqual(compute_general_chargeable_days(20, settings), 22)

	def test_general_rent_example_jaggery(self):
		settings = self._mock_settings()

		result = compute_rent_line(
			"General",
			qty=10,
			rate=2.2,
			aawak_date="2026-01-01",
			jawak_date="2026-01-15",
			settings=settings,
		)
		self.assertEqual(result["chargeable_period"], 15)
		self.assertEqual(result["total_days"], 15)

	def test_specific_month_slabs(self):
		settings = self._mock_settings()
		self.assertEqual(compute_specific_chargeable_months(32, settings), 1)
		self.assertEqual(compute_specific_chargeable_months(33, settings), 2)
		self.assertEqual(compute_specific_chargeable_months(34, settings), 2)
		self.assertEqual(compute_specific_chargeable_months(62, settings), 2)
		self.assertEqual(compute_specific_chargeable_months(63, settings), 3)

	def test_specific_rent_eggs_crate(self):
		settings = self._mock_settings()

		result = compute_rent_line(
			"Specific",
			qty=4,
			rate=50,
			aawak_date="2026-01-01",
			jawak_date="2026-02-03",
			settings=settings,
		)
		self.assertEqual(result["chargeable_period"], 2)
		self.assertEqual(result["chargeable_period_uom"], "Months")
		self.assertEqual(result["total_amount"], 400)


class TestBagConfigurationNaming(FrappeTestCase):
	def test_general_bag_weight_name(self):
		self.assertEqual(build_bag_configuration_name("General", "Bag", 50), "G-50KG")

	def test_general_kg_weight_name(self):
		self.assertEqual(build_bag_configuration_name("General", "Kg", 50), "G-50KG")

	def test_general_nos_weight_name(self):
		self.assertEqual(build_bag_configuration_name("General", "Nos", 10), "G-NOS-10KG")

	def test_specific_bag_name(self):
		name = build_bag_configuration_name("Specific", "Bag", 50, "JAG-001")
		self.assertEqual(name, "SP-50KG-JAG")

	def test_specific_kg_name(self):
		name = build_bag_configuration_name("Specific", "Kg", 50, "Goodown Rent")
		self.assertEqual(name, "SP-50KG-GOO")

	def test_specific_crate_without_weight(self):
		name = build_bag_configuration_name("Specific", "Crate", None, "EGG-001")
		self.assertTrue(name.startswith("SP-CRATE-"))
