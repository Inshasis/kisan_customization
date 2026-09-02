# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import cint, flt

from kisan_customization.fixtures.deduction_types import get_default_deduction_types

SYNC_FIELDS = (
	"required_value",
	"charges_per_unit",
	"calculation",
	"deduction_category",
	"tiered_calculation",
	"qty_deducation",
	"is_active",
)


def sync_deduction_types(companies=None):
	companies = companies or _get_companies()
	if not companies:
		return

	defaults = get_default_deduction_types()
	for company in companies:
		for row in defaults:
			_sync_deduction_type(company, row)

	frappe.clear_cache(doctype="Deduction Type")


def _get_companies():
	companies = frappe.get_all("Company", pluck="name")
	if companies:
		return companies

	company = frappe.get_single_value("Kisan Master Settings", "default_company")
	if company:
		return [company]

	default_company = frappe.defaults.get_global_default("company")
	return [default_company] if default_company else []


def _sync_deduction_type(company, row):
	type_name = row.get("deduction_type_name")
	if not type_name:
		return

	values = {field: row.get(field) for field in SYNC_FIELDS if field in row}
	existing_name = _find_existing_deduction_type(company, type_name)

	if existing_name:
		_update_if_changed(existing_name, values)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Deduction Type",
			"company": company,
			"deduction_type_name": type_name,
			**values,
		}
	)
	_copy_related_account_from_existing(doc, type_name)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)


def _find_existing_deduction_type(company, type_name):
	name = frappe.db.get_value(
		"Deduction Type",
		{"deduction_type_name": type_name, "company": company},
		"name",
	)
	if name:
		return name

	if frappe.db.exists("Deduction Type", type_name):
		doc_company = frappe.db.get_value("Deduction Type", type_name, "company")
		if doc_company == company:
			return type_name

	return None


def _update_if_changed(name, values):
	current = frappe.db.get_value("Deduction Type", name, list(SYNC_FIELDS), as_dict=True) or {}
	updates = {}

	for field, value in values.items():
		if _field_changed(current.get(field), value):
			updates[field] = value

	if updates:
		frappe.db.set_value("Deduction Type", name, updates, update_modified=False)


def _field_changed(current, new):
	if isinstance(new, (int, float)) or isinstance(current, (int, float)):
		return flt(current) != flt(new)

	if field_is_check(new) or field_is_check(current):
		return cint(current) != cint(new)

	return (current or "") != (new or "")


def field_is_check(value):
	return value in (0, 1, True, False)


def _copy_related_account_from_existing(doc, type_name):
	if doc.get("related_account"):
		return

	related_account = frappe.db.get_value(
		"Deduction Type",
		{"deduction_type_name": type_name, "related_account": ("is", "set")},
		"related_account",
	)
	if related_account:
		doc.related_account = related_account
