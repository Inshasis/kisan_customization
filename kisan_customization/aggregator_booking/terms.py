# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import add_days, cint, flt, getdate


def get_booking_base_date(booking):
	return getdate(booking.booking_date or booking.get("booking_date"))


def compute_delivery_date(booking):
	base_date = get_booking_base_date(booking)
	delivery_days = cint(booking.get("delivery_days"))

	if delivery_days > 0:
		return add_days(base_date, delivery_days)

	if booking.get("delivery_date"):
		return getdate(booking.delivery_date)

	return base_date


def compute_payment_date(booking):
	base_date = get_booking_base_date(booking)
	payment_days = cint(booking.get("payment_days"))

	if payment_days > 0:
		return add_days(base_date, payment_days)

	if booking.get("payment_date"):
		return getdate(booking.payment_date)

	return None


def apply_booking_dates(booking):
	booking.delivery_date = compute_delivery_date(booking)
	booking.payment_date = compute_payment_date(booking)


def calculate_booking_broker_commission(booking):
	commission_type = booking.get("commission_type")
	commission_amount = 0

	if commission_type == "Percentage":
		base_amount = flt(booking.get("total_amount") or booking.get("grand_total"))
		percent = flt(booking.get("commission_percent"))
		commission_amount = (base_amount * percent) / 100
	elif commission_type == "Total Qty":
		total_qty = flt(booking.get("total_qty"))
		rate = flt(booking.get("commission_amount"))
		commission_amount = total_qty * rate

	booking.broker_commission_amount = commission_amount
	return commission_amount


def calculate_po_broker_commission(po, booking):
	commission_type = booking.get("commission_type")
	commission_amount = 0

	if commission_type == "Percentage":
		net_amount = flt(po.net_total)
		percent = flt(booking.get("commission_percent"))
		commission_amount = (net_amount * percent) / 100
	elif commission_type == "Total Qty":
		total_qty = flt(po.total_qty)
		rate = flt(booking.get("commission_amount"))
		commission_amount = total_qty * rate

	return commission_amount


def apply_booking_terms_to_po(po, booking):
	delivery_days = cint(booking.get("delivery_days"))
	payment_days = cint(booking.get("payment_days"))
	delivery_date = compute_delivery_date(booking)
	payment_date = compute_payment_date(booking)

	if _has_field("Purchase Order", "custom_delivery_days") and delivery_days:
		po.custom_delivery_days = delivery_days

	if _has_field("Purchase Order", "custom_payment_days") and payment_days:
		po.custom_payment_days = payment_days

	po.schedule_date = delivery_date
	for row in po.get("items") or []:
		row.schedule_date = delivery_date

	if payment_date and payment_days:
		grand_total = flt(po.rounded_total) or flt(po.grand_total)
		base_grand_total = flt(po.base_rounded_total) or flt(po.base_grand_total)

		po.set("payment_schedule", [])
		schedule_row = {
			"due_date": payment_date,
			"invoice_portion": 100,
			"payment_amount": grand_total,
			"base_payment_amount": base_grand_total,
			"outstanding": grand_total,
		}
		if _has_field("Payment Schedule", "credit_days"):
			schedule_row["credit_days"] = payment_days

		po.append("payment_schedule", schedule_row)
		po.due_date = payment_date
	elif payment_date:
		po.due_date = payment_date

	apply_booking_broker_to_po(po, booking)


def apply_booking_broker_to_po(po, booking):
	if not booking.get("aggregator"):
		return

	if _has_field("Purchase Order", "custom_broker"):
		po.custom_broker = booking.aggregator

	if _has_field("Purchase Order", "custom_commission_type"):
		po.custom_commission_type = booking.get("commission_type")

	if _has_field("Purchase Order", "custom_commission_percent"):
		po.custom_commission_percent = flt(booking.get("commission_percent"))

	if _has_field("Purchase Order", "custom_commission_amount"):
		po.custom_commission_amount = flt(booking.get("commission_amount"))

	if _has_field("Purchase Order", "custom_broker_commission_amount"):
		po.custom_broker_commission_amount = calculate_po_broker_commission(po, booking)


def persist_po_booking_terms(po_name, booking):
	"""Write booking terms directly to DB so submit validation sees persisted values."""
	po = frappe.get_doc("Purchase Order", po_name)
	apply_booking_broker_to_po(po, booking)

	values = {}
	field_map = {
		"custom_broker": booking.get("aggregator"),
		"custom_commission_type": booking.get("commission_type"),
		"custom_commission_percent": flt(booking.get("commission_percent")),
		"custom_commission_amount": flt(booking.get("commission_amount")),
		"custom_broker_commission_amount": flt(po.custom_broker_commission_amount),
		"custom_delivery_days": cint(booking.get("delivery_days")) or None,
		"custom_payment_days": cint(booking.get("payment_days")) or None,
	}

	for fieldname, value in field_map.items():
		if _has_field("Purchase Order", fieldname) and value not in (None, ""):
			values[fieldname] = value

	if values:
		frappe.db.set_value("Purchase Order", po_name, values, update_modified=False)


def _has_field(doctype, fieldname):
	return frappe.get_meta(doctype).has_field(fieldname)
