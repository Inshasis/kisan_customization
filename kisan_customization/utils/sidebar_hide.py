# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _

CACHE_KEY = "kisan_hide_sidebar_rules"


def _rules_from_settings():
	list_doctypes = set()
	details_doctypes = set()

	if not frappe.db.table_exists("Kisan Hide Sidebar Rule"):
		return {"list": [], "details": []}

	for row in frappe.db.get_all(
		"Kisan Hide Sidebar Rule",
		filters={"parent": "Kisan Master Settings", "parenttype": "Kisan Master Settings"},
		fields=["reference_doctype", "hide_type"],
	):
		dt = (row.reference_doctype or "").strip()
		if not dt:
			continue
		if row.hide_type == "List View":
			list_doctypes.add(dt)
		elif row.hide_type == "Details View":
			details_doctypes.add(dt)

	return {
		"list": sorted(list_doctypes),
		"details": sorted(details_doctypes),
	}


def generate_sidebar_assets():
	"""Clear cache after settings change; desk reads rules from boot on reload."""
	clear_hide_sidebar_cache()
	return _rules_from_settings()


@frappe.whitelist()
def get_hide_sidebar_rules():
	cached = frappe.cache().get_value(CACHE_KEY)
	if cached:
		return cached
	rules = _rules_from_settings()
	frappe.cache().set_value(CACHE_KEY, rules)
	return rules


def clear_hide_sidebar_cache():
	frappe.cache().delete_value(CACHE_KEY)


def boot_session(bootinfo):
	bootinfo["kisan_hide_sidebar_rules"] = _rules_from_settings()


def validate_hide_sidebar_rules(rows):
	seen = set()
	for idx, row in enumerate(rows or [], start=1):
		key = (row.reference_doctype, row.hide_type)
		if key in seen:
			frappe.throw(
				_("Row {0}: Duplicate rule for {1} ({2}).").format(
					idx, frappe.bold(row.reference_doctype), row.hide_type
				)
			)
		seen.add(key)
