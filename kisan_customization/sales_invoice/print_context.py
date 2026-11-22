# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.utils import flt, fmt_money, money_in_words


def get_gst_sales_print_data(sales_invoice):
	"""Data for GST Sales print format (Sales Invoice)."""
	si = frappe.get_doc("Sales Invoice", sales_invoice)
	currency = si.currency or "INR"

	company = frappe.get_cached_doc("Company", si.company) if si.company else None
	company_gstin = ""
	if company and company.get("gstin"):
		company_gstin = company.gstin
	elif si.get("company_gstin"):
		company_gstin = si.company_gstin

	customer_gstin = si.get("billing_address_gstin") or ""
	if not customer_gstin and si.customer:
		customer_gstin = frappe.db.get_value("Customer", si.customer, "gstin") or ""

	items = []
	for idx, row in enumerate(si.get("items") or [], start=1):
		items.append(
			{
				"idx": idx,
				"item_name": row.item_name or row.item_code,
				"qty": flt(row.qty),
				"uom": row.uom or "",
				"rate": _money(row.rate, currency),
				"amount": _money(row.amount, currency),
				"hsn": row.get("gst_hsn_code") or "",
			}
		)

	tax_rows = []
	for tax in si.get("taxes") or []:
		desc = (tax.description or tax.account_head or "").strip()
		if not desc:
			continue
		tax_rows.append(
			{
				"description": desc,
				"rate": flt(tax.rate),
				"amount": _money(tax.tax_amount, currency),
			}
		)

	gst_breakup = _gst_breakup_rows(si, currency)

	title = "Credit Note" if si.get("is_return") else "Tax Invoice"
	rounded = si.get("rounded_total")
	if rounded is None:
		rounded = si.grand_total

	return {
		"title": title,
		"invoice_no": si.name,
		"invoice_date": frappe.format(si.posting_date, {"fieldtype": "Date"}),
		"company_name": si.company or "",
		"company_address": si.get("company_address_display") or "",
		"company_gstin": company_gstin,
		"customer_name": si.customer_name or si.customer or "",
		"customer_address": si.get("address_display") or "",
		"customer_gstin": customer_gstin,
		"place_of_supply": si.get("place_of_supply") or "",
		"items": items,
		"tax_rows": tax_rows,
		"net_total": _money(si.net_total, currency),
		"grand_total": _money(si.grand_total, currency),
		"rounded_total": _money(rounded, currency),
		"in_words": si.get("in_words")
		or money_in_words(abs(flt(rounded if rounded is not None else si.grand_total)), currency),
		"gst_breakup": gst_breakup,
		"currency": currency,
		"is_return": cint_bool(si.get("is_return")),
	}


def cint_bool(value):
	return 1 if value else 0


def _money(amount, currency):
	return fmt_money(flt(amount), currency=currency)


def _gst_breakup_rows(si, currency):
	"""Group taxable + GST by HSN from item lines."""
	groups = {}
	for row in si.get("items") or []:
		hsn = row.get("gst_hsn_code") or "—"
		bucket = groups.setdefault(
			hsn,
			{
				"hsn": hsn,
				"taxable": 0.0,
				"cgst_rate": 0.0,
				"sgst_rate": 0.0,
				"igst_rate": 0.0,
				"cgst": 0.0,
				"sgst": 0.0,
				"igst": 0.0,
			},
		)
		taxable = flt(row.get("taxable_value"))
		if not taxable:
			taxable = flt(row.net_amount if row.get("net_amount") is not None else row.amount)
		bucket["taxable"] += taxable

		cgst_rate = flt(row.get("cgst_rate"))
		sgst_rate = flt(row.get("sgst_rate"))
		igst_rate = flt(row.get("igst_rate"))
		if cgst_rate:
			bucket["cgst_rate"] = cgst_rate
			bucket["cgst"] += taxable * cgst_rate / 100.0
		if sgst_rate:
			bucket["sgst_rate"] = sgst_rate
			bucket["sgst"] += taxable * sgst_rate / 100.0
		if igst_rate:
			bucket["igst_rate"] = igst_rate
			bucket["igst"] += taxable * igst_rate / 100.0

	# Prefer document tax amounts if item rates missing
	has_rates = any(
		b["cgst_rate"] or b["sgst_rate"] or b["igst_rate"] for b in groups.values()
	)
	rows = []
	for bucket in groups.values():
		row = {
			"hsn": bucket["hsn"],
			"taxable": _money(bucket["taxable"], currency),
			"cgst": "",
			"sgst": "",
			"igst": "",
		}
		if has_rates:
			if bucket["cgst_rate"] or bucket["cgst"]:
				row["cgst"] = f"({bucket['cgst_rate']:g}%) {_money(bucket['cgst'], currency)}"
			if bucket["sgst_rate"] or bucket["sgst"]:
				row["sgst"] = f"({bucket['sgst_rate']:g}%) {_money(bucket['sgst'], currency)}"
			if bucket["igst_rate"] or bucket["igst"]:
				row["igst"] = f"({bucket['igst_rate']:g}%) {_money(bucket['igst'], currency)}"
		rows.append(row)
	return rows
