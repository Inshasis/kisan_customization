# Copyright (c) 2026, Hidayatali and contributors

from frappe.utils import flt

from kisan_customization.broker_commission.service import (
	cancel_broker_commission_on_cancel,
	clear_broker_commission_fields,
	create_broker_commission_on_submit,
)


def sync_broker_commission(doc):
	if not doc.meta.has_field("custom_broker_commission_amount"):
		return

	doc.custom_broker_commission_amount = calculate_broker_commission_amount(doc)


def _get_pi_commission_base(doc):
	from kisan_customization.utils.deduction_utils import get_pi_total_gross_weight

	return flt(get_pi_total_gross_weight(doc))


def calculate_broker_commission_amount(doc):
	commission_type = doc.get("custom_commission_type")
	base_qty = _get_pi_commission_base(doc)
	commission_amount = 0

	if commission_type == "Percentage":
		percent = flt(doc.get("custom_commission_percent"))
		commission_amount = (base_qty * percent) / 100
	elif commission_type == "Total Qty":
		rate = flt(doc.get("custom_commission_amount"))
		commission_amount = (base_qty * rate) / 100

	return commission_amount


def validate(doc, method=None):
	if doc.get("is_return"):
		clear_broker_commission_fields(doc)
		return

	sync_broker_commission(doc)


def before_submit(doc, method=None):
	if doc.get("is_return"):
		return

	sync_broker_commission(doc)


def on_submit(doc, method=None):
	sync_broker_commission(doc)
	create_broker_commission_on_submit(doc)


def before_cancel(doc, method=None):
	cancel_broker_commission_on_cancel(doc)
