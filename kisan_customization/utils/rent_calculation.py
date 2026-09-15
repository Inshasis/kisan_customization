# Copyright (c) 2026, Hidayatali and contributors

import math

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def get_master_rent_settings():
	return frappe.get_single("Kisan Master Settings")


def get_actual_storage_days(aawak_date, jawak_date):
	if not aawak_date or not jawak_date:
		return 0

	start = getdate(aawak_date)
	end = getdate(jawak_date)
	return max(0, (end - start).days)


def compute_general_chargeable_days(actual_days, settings=None):
	"""General rent: minimum days, else actual days + extra; amount is daily prorated."""
	settings = settings or get_master_rent_settings()
	min_days = cint(settings.minimum_chargeable_days) or 15
	extra_days = cint(settings.extra_days_after_minimum) or 2

	if actual_days <= min_days:
		return min_days

	return actual_days + extra_days


def compute_specific_chargeable_months(actual_days, settings=None):
	"""Bill in full months using Specific settings.

	First month covers Minimum Chargeable Days + Extra Days After Minimum
	(e.g. 30 + 2 = 32 days). Each day after that threshold starts counting
	toward the next month in blocks of Days Per Month (33–62 → 2 months).
	"""
	settings = settings or get_master_rent_settings()
	min_days = cint(settings.specific_minimum_days) or 30
	extra_days = cint(settings.specific_extra_days) or 2
	days_per_month = cint(settings.specific_days_per_month) or 30

	threshold = min_days + extra_days
	if actual_days <= threshold:
		return 1

	remaining = actual_days - threshold
	return 1 + math.ceil(remaining / days_per_month)


def compute_rent_line(
	rate_type,
	qty,
	rate,
	aawak_date,
	jawak_date,
	add_amount=0,
	settings=None,
):
	settings = settings or get_master_rent_settings()
	qty = cint(qty)
	rate = flt(rate)
	add_amount = flt(add_amount)
	actual_days = get_actual_storage_days(aawak_date, jawak_date)

	result = {
		"actual_storage_days": actual_days,
		"chargeable_period": 0,
		"chargeable_period_uom": "Days",
		"total_days": 0,
		"base_total_amount": 0.0,
		"total_amount": 0.0,
	}

	if qty <= 0 or rate <= 0:
		return result

	rate_type = (rate_type or "General").strip()

	if rate_type == "Specific":
		chargeable_months = compute_specific_chargeable_months(actual_days, settings)
		base_amount = qty * rate * chargeable_months
		result.update(
			{
				"chargeable_period": chargeable_months,
				"chargeable_period_uom": "Months",
				"total_days": 0,
			}
		)
	else:
		chargeable_days = compute_general_chargeable_days(actual_days, settings)
		days_per_month = cint(settings.days_per_month) or 30
		daily_rate = rate / days_per_month
		base_amount = qty * daily_rate * chargeable_days
		result.update(
			{
				"chargeable_period": chargeable_days,
				"chargeable_period_uom": "Days",
				"total_days": chargeable_days,
			}
		)

	base_amount = flt(base_amount, 2)
	total_amount = round(base_amount + add_amount)

	result["base_total_amount"] = base_amount
	result["total_amount"] = total_amount
	return result


def get_line_key(bag_configuration=None, commodity=None, uom=None, weight_kg=None, bag_weight=None):
	if bag_configuration:
		return str(bag_configuration)

	weight = weight_kg if weight_kg not in (None, "", 0) else bag_weight
	weight_part = normalize_weight(weight)
	commodity_part = (commodity or "").strip()
	uom_part = (uom or "Bag").strip()
	return f"{commodity_part}|{uom_part}|{weight_part}"


def normalize_weight(value):
	if value in (None, ""):
		return ""

	try:
		return str(int(float(value)))
	except (TypeError, ValueError):
		return str(value).strip()


def format_line_description(uom=None, weight_kg=None, commodity=None, bag_weight=None):
	weight = weight_kg if weight_kg not in (None, "", 0) else bag_weight
	parts = []
	if commodity:
		parts.append(str(commodity))
	if uom:
		parts.append(str(uom))
	if weight not in (None, "", 0):
		parts.append(f"{normalize_weight(weight)} kg")
	return " / ".join(parts) if parts else normalize_weight(weight) or _("Line")


def recompute_jawak_bag_detail_row(row, aawak_date, jawak_date, settings=None):
	calc = compute_rent_line(
		row.get("rate_type"),
		row.get("release_bags"),
		row.get("rate"),
		aawak_date,
		jawak_date,
		add_amount=row.get("add_amount"),
		settings=settings,
	)
	row.actual_storage_days = calc["actual_storage_days"]
	row.chargeable_period = calc["chargeable_period"]
	row.chargeable_period_uom = calc["chargeable_period_uom"]
	row.total_days = calc["total_days"]
	row.base_total_amount = calc["base_total_amount"]
	row.total_amount = calc["total_amount"]
	return calc


def recompute_outward_jawak_amounts(doc, settings=None, tolerance=0.01):
	settings = settings or get_master_rent_settings()

	if not doc.jawak_date or not doc.inward_aawak:
		return {"total_amount": 0.0, "net_amount": 0.0}

	aawak_date = frappe.db.get_value("Inward Aawak", doc.inward_aawak, "aawak_date")
	if not aawak_date:
		return {"total_amount": 0.0, "net_amount": 0.0}

	total_amount = 0.0
	for row in doc.get("jawak_bag_details") or []:
		recompute_jawak_bag_detail_row(row, aawak_date, doc.jawak_date, settings=settings)
		total_amount += flt(row.total_amount)

	total_amount = flt(total_amount, 2)
	net_amount = flt(
		total_amount
		+ flt(doc.additional_charges)
		+ flt(doc.inward_charges)
		- flt(doc.discount),
		2,
	)

	return {
		"total_amount": total_amount,
		"net_amount": net_amount,
		"aawak_date": aawak_date,
	}


def amounts_match(expected, actual, tolerance=0.01):
	return abs(flt(expected) - flt(actual)) <= tolerance


@frappe.whitelist()
def calculate_rent_line(
	rate_type,
	qty,
	rate,
	aawak_date,
	jawak_date,
	add_amount=0,
):
	return compute_rent_line(
		rate_type,
		qty,
		rate,
		aawak_date,
		jawak_date,
		add_amount=add_amount,
	)
