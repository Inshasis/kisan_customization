# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document

from kisan_customization.kisan_customization.doctype.bag_configuration.naming import (
	assign_bag_configuration_name,
	build_bag_configuration_name,
	ensure_unique_bag_configuration_name,
)


class BagConfiguration(Document):
	def autoname(self):
		assign_bag_configuration_name(self)

	def before_insert(self):
		if not self.name or self.name.startswith("new-"):
			assign_bag_configuration_name(self)

	def before_save(self):
		expected = ensure_unique_bag_configuration_name(
			build_bag_configuration_name(
				self.rate_type,
				self.uom,
				self.weight_kg,
				self.commodity,
			),
			self.name,
		)

		if self.is_new():
			self.name = expected
			return

		if self.name != expected:
			self.flags.expected_bag_configuration_name = expected

	def on_update(self):
		expected = self.flags.get("expected_bag_configuration_name")
		if expected and expected != self.name:
			frappe.rename_doc("Bag Configuration", self.name, expected, force=True, merge=False)

	def validate(self):
		if self.rate_type == "Specific" and not self.commodity:
			frappe.throw(_("Commodity / Item is required when Rate Type is Specific"))

		if self.rate_type == "General":
			self.commodity = None

		if self.weight_kg in (0, "0"):
			self.weight_kg = None

		self._validate_unique_combination()

	def _validate_unique_combination(self):
		filters = {"uom": self.uom}

		if self.name:
			filters["name"] = ("!=", self.name)

		if self.rate_type == "Specific":
			filters["rate_type"] = "Specific"
			filters["commodity"] = self.commodity
		else:
			filters["rate_type"] = "General"

		candidates = frappe.get_all(
			"Bag Configuration",
			filters=filters,
			fields=["name", "weight_kg", "commodity"],
		)

		for row in candidates:
			if self.rate_type == "General" and row.commodity:
				continue

			existing_weight = row.weight_kg
			if (self.weight_kg in (None, 0, "") and existing_weight in (None, 0, "")) or cint_equal(
				self.weight_kg, existing_weight
			):
				frappe.throw(
					_(
						"A Bag Configuration already exists for this Rate Type, UOM, Weight, and Commodity combination ({0})"
					).format(row.name)
				)


def cint_equal(a, b):
	try:
		return int(a or 0) == int(b or 0)
	except (TypeError, ValueError):
		return (a or "") == (b or "")
