# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt


def sync_broker_commission(doc):
	if not doc.meta.has_field("custom_broker_commission_amount"):
		return

	commission_type = doc.get("custom_commission_type")
	commission_amount = 0

	if commission_type == "Percentage":
		net_amount = flt(doc.net_total)
		percent = flt(doc.get("custom_commission_percent"))
		commission_amount = (net_amount * percent) / 100
	elif commission_type == "Total Qty":
		total_qty = flt(doc.total_qty)
		rate = flt(doc.get("custom_commission_amount"))
		commission_amount = total_qty * rate

	doc.custom_broker_commission_amount = commission_amount


def validate(doc, method=None):
	if doc.docstatus != 0:
		return

	sync_broker_commission(doc)


def before_submit(doc, method=None):
	sync_broker_commission(doc)

	if not doc.meta.has_field("custom_broker_commission_amount"):
		return

	frappe.db.set_value(
		"Sales Order",
		doc.name,
		"custom_broker_commission_amount",
		flt(doc.custom_broker_commission_amount),
		update_modified=False,
	)
