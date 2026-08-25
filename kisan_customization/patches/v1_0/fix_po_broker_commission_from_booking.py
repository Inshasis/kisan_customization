# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt

from kisan_customization.purchase_order.broker_commission import sync_broker_commission


def execute():
	if not frappe.db.has_column("Purchase Order", "custom_aggregator_booking"):
		return

	pos = frappe.get_all(
		"Purchase Order",
		filters={
			"custom_aggregator_booking": ["is", "set"],
			"docstatus": ["<", 2],
		},
		fields=["name"],
	)

	for row in pos:
		po = frappe.get_doc("Purchase Order", row.name)
		if not po.get("custom_commission_type"):
			continue

		sync_broker_commission(po)
		if not flt(po.custom_broker_commission_amount):
			continue

		frappe.db.set_value(
			"Purchase Order",
			po.name,
			"custom_broker_commission_amount",
			flt(po.custom_broker_commission_amount),
			update_modified=False,
		)

	frappe.clear_cache(doctype="Purchase Order")
