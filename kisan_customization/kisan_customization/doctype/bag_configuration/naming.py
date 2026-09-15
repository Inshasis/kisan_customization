# Copyright (c) 2026, Hidayatali and contributors

import re

import frappe

NAME_SEP = "-"


def get_commodity_suffix(commodity):
	if not commodity:
		return ""

	item_name = frappe.db.get_value("Item", commodity, "item_name") or commodity
	letters = re.sub(r"[^A-Za-z]", "", item_name or "")[:3].upper()
	if letters:
		return letters

	return re.sub(r"[^A-Za-z0-9]", "", str(commodity))[:3].upper() or "ITM"


def _format_weight(weight_kg):
	if weight_kg in (None, "", 0, "0"):
		return ""
	try:
		return f"{int(float(weight_kg))}KG"
	except (TypeError, ValueError):
		return ""


def _omit_uom_in_name(uom_key, weight_part):
	"""Bag and Kg rates use weight-only segment (e.g. G-50KG, not G-KG-50KG)."""
	return uom_key in ("BAG", "KG") and bool(weight_part)


def build_bag_configuration_name(rate_type, uom, weight_kg=None, commodity=None):
	"""Human-readable ID without '/' (slashes break Frappe list/form routes)."""
	uom_key = (uom or "Bag").strip().upper().replace(" ", "")
	weight_part = _format_weight(weight_kg)
	is_general = (rate_type or "General").strip() == "General"
	prefix = "G" if is_general else "SP"

	if is_general:
		if _omit_uom_in_name(uom_key, weight_part):
			base = f"{prefix}{NAME_SEP}{weight_part}"
		elif weight_part:
			base = f"{prefix}{NAME_SEP}{uom_key}{NAME_SEP}{weight_part}"
		else:
			base = f"{prefix}{NAME_SEP}{uom_key}"
		return base

	commodity_part = get_commodity_suffix(commodity)
	if _omit_uom_in_name(uom_key, weight_part):
		base = f"{prefix}{NAME_SEP}{weight_part}{NAME_SEP}{commodity_part}"
	elif weight_part:
		base = f"{prefix}{NAME_SEP}{uom_key}{NAME_SEP}{weight_part}{NAME_SEP}{commodity_part}"
	else:
		base = f"{prefix}{NAME_SEP}{uom_key}{NAME_SEP}{commodity_part}"

	return base


def assign_bag_configuration_name(doc):
	base = build_bag_configuration_name(
		doc.rate_type,
		doc.uom,
		doc.weight_kg,
		doc.commodity,
	)
	doc.name = ensure_unique_bag_configuration_name(base, doc.name if doc.name else None)


def ensure_unique_bag_configuration_name(base, exclude_name=None):
	name = base
	counter = 2
	while frappe.db.exists("Bag Configuration", name) and name != exclude_name:
		name = f"{base}{NAME_SEP}{counter}"
		counter += 1
	return name
