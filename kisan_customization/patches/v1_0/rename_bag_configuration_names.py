# Copyright (c) 2026, Hidayatali and contributors

import frappe

from kisan_customization.kisan_customization.doctype.bag_configuration.naming import (
	build_bag_configuration_name,
	ensure_unique_bag_configuration_name,
)


def execute():
	for row in frappe.get_all(
		"Bag Configuration",
		fields=["name", "rate_type", "uom", "weight_kg", "commodity"],
	):
		expected = ensure_unique_bag_configuration_name(
			build_bag_configuration_name(
				row.rate_type,
				row.uom,
				row.weight_kg,
				row.commodity,
			),
			row.name,
		)
		if row.name == expected:
			continue

		if frappe.db.exists("Bag Configuration", expected):
			continue

		frappe.rename_doc("Bag Configuration", row.name, expected, force=True, merge=False)

	frappe.clear_cache(doctype="Bag Configuration")
