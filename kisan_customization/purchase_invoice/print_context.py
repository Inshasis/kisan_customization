# Copyright (c) 2026, Hidayatali and contributors

import re

import frappe
from frappe.utils import flt, fmt_money, get_url, now_datetime, strip_html


def _load_pi(purchase_invoice):
	doc = frappe.get_doc("Purchase Invoice", purchase_invoice)
	if doc.get("is_return") and doc.get("return_against"):
		return frappe.get_doc("Purchase Invoice", doc.return_against)
	return doc


def _get_debit_note(pi):
	name = frappe.db.get_value(
		"Purchase Invoice",
		{"return_against": pi.name, "is_return": 1, "docstatus": ("<", 2)},
		"name",
	)
	return frappe.get_doc("Purchase Invoice", name) if name else None


def _party_location(supplier):
	if not supplier:
		return ""
	addr = frappe.db.get_value("Supplier", supplier, "supplier_primary_address")
	return _address_display(addr)


def _address_display(address_name):
	if not address_name:
		return ""
	from frappe.contacts.doctype.address.address import get_address_display

	return get_address_display(address_name) or ""


def _company_address(company_name):
	from erpnext.setup.doctype.company.company import get_default_company_address

	addr_name = get_default_company_address(company_name)
	return _address_display(addr_name)


def _address_one_line(address_html):
	text = strip_html(address_html or "").replace("\n", ", ")
	return re.sub(r"\s+", " ", text).strip(" ,")


def _company_logo_url(company_doc):
	logo = company_doc.get("company_logo")
	if not logo:
		return ""
	if logo.startswith("http"):
		return logo
	return get_url(logo)


def _broker_label(broker):
	if not broker:
		return ""
	return frappe.db.get_value("Supplier", broker, "supplier_name") or broker


def _purchase_orders(pi):
	pos = []
	for row in pi.get("items") or []:
		if row.purchase_order and row.purchase_order not in pos:
			pos.append(row.purchase_order)
	return ", ".join(pos)


def _gst_rate_label(row):
	rate = flt(row.cgst_rate) + flt(row.sgst_rate) + flt(row.igst_rate)
	if not rate:
		return ""
	return f"{rate:g}%"


def _tax_breakup(doc):
	if not doc:
		doc = frappe._dict(taxes=[])
	cgst = sgst = igst = tds = round_off = 0.0
	cgst_rate = sgst_rate = igst_rate = 0.0
	for row in doc.get("taxes") or []:
		amt = flt(row.tax_amount)
		head = (row.account_head or "").lower()
		desc = (row.description or "").lower()
		if "round" in desc or "round" in head:
			round_off += amt
		elif "tds" in desc or "tds" in head or "withholding" in desc:
			tds += amt
		elif "igst" in head:
			igst += amt
			igst_rate = igst_rate or flt(row.rate)
		elif "sgst" in head:
			sgst += amt
			sgst_rate = sgst_rate or flt(row.rate)
		elif "cgst" in head:
			cgst += amt
			cgst_rate = cgst_rate or flt(row.rate)
	return {
		"cgst": cgst,
		"sgst": sgst,
		"igst": igst,
		"tds": tds,
		"round_off": round_off,
		"gst_total": cgst + sgst + igst,
		"cgst_rate": cgst_rate,
		"sgst_rate": sgst_rate,
		"igst_rate": igst_rate,
	}


def _tax_sidebar(doc, currency):
	"""Right-hand tax block (Sub Total, CGST/SGST/IGST lines) like settlement PDF."""
	if not doc:
		taxes = _tax_breakup(None)
		sub_total = 0.0
	else:
		taxes = _tax_breakup(doc)
		sub_total = flt(doc.net_total) or flt(doc.total)

	def _line(label, amount):
		return {"label": label, "amount": fmt_money(amount, currency=currency)}

	lines = [_line("Sub Total", sub_total)]
	if taxes["cgst"] or taxes["cgst_rate"]:
		pct = f" @ {taxes['cgst_rate']:g}%" if taxes["cgst_rate"] else ""
		lines.append(_line(f"CGST +{pct}", taxes["cgst"]))
	if taxes["sgst"] or taxes["sgst_rate"]:
		pct = f" @ {taxes['sgst_rate']:g}%" if taxes["sgst_rate"] else ""
		lines.append(_line(f"SGST +{pct}", taxes["sgst"]))
	pct = f" @ {taxes['igst_rate']:g}%" if taxes["igst_rate"] else " @ 0%"
	lines.append(_line(f"IGST +{pct}", taxes["igst"]))
	if taxes["round_off"]:
		lines.append(_line("Round Off", taxes["round_off"]))
	lines.append(
		{
			"label": "Total",
			"amount": fmt_money(doc.grand_total if doc else 0, currency=currency),
			"bold": True,
		}
	)
	return lines


def _pi_lines(pi):
	tds_total = _tax_breakup(pi)["tds"]
	lines = []
	for row in pi.get("items") or []:
		gst_amt = flt(row.cgst_amount) + flt(row.sgst_amount) + flt(row.igst_amount)
		payable = flt(row.amount) + gst_amt
		vendor_wt = f"{flt(row.qty):g} {row.uom or ''}".strip()
		gst_label = _gst_rate_label(row)
		gst_cell = fmt_money(gst_amt, currency=pi.currency)
		if gst_label:
			gst_cell = f"{gst_cell} / {gst_label}"
		uom = (row.uom or "Quintal").strip()
		rate_suffix = "/QT" if uom.lower().startswith("quint") else f"/{uom[:3].upper()}"
		lines.append(
			{
				"sr": row.idx,
				"item": row.item_name or row.item_code,
				"hsn": row.gst_hsn_code or row.get("custom_hsn_code") or "",
				"vendor_dis_wt": vendor_wt,
				"rate": fmt_money(row.rate, currency=pi.currency),
				"rate_suffix": rate_suffix,
				"basic": fmt_money(row.amount, currency=pi.currency),
				"gst": gst_cell,
				"tds": "",
				"payable": fmt_money(payable, currency=pi.currency),
			}
		)
	if lines and tds_total:
		lines[0]["tds"] = fmt_money(tds_total, currency=pi.currency)
	if len(lines) == 1:
		lines[0]["payable"] = fmt_money(flt(pi.grand_total), currency=pi.currency)
	return lines


def _bargain_rows(pi):
	arrival = flt(pi.get("custom_total_arrival_weight"))
	gross = flt(pi.get("custom_total_gross_weight"))
	bags = flt(pi.get("custom_total_bags"))
	rows = []
	for idx, item in enumerate(pi.get("items") or [], start=1):
		sauda_rate = item.rate
		if item.purchase_order:
			po_rate = frappe.db.get_value(
				"Purchase Order Item",
				{"parent": item.purchase_order, "item_code": item.item_code},
				"rate",
			)
			if po_rate is not None:
				sauda_rate = po_rate
		lot = item.purchase_order or pi.get("custom_aggregator_booking") or ""
		line_arrival = flt(item.qty) * 100 if (item.uom or "").lower() == "quintal" else flt(item.qty)
		if len(pi.items) == 1 and arrival:
			line_arrival = arrival
		amount = flt(item.amount)
		rows.append(
			{
				"lot_no": lot,
				"item": item.item_name or item.item_code,
				"bags": bags if idx == 1 else "",
				"bags_wt": gross if idx == 1 else "",
				"sauda_rate": fmt_money(sauda_rate, currency=pi.currency),
				"arrival_weight": line_arrival,
				"oil_pct": "",
				"oil_rate": "",
				"net_wt": line_arrival,
				"amount": fmt_money(amount, currency=pi.currency),
			}
		)
	bargain_total = sum(flt(item.amount) for item in pi.get("items") or [])
	return rows, fmt_money(bargain_total, currency=pi.currency)


def _quality_rows(pi):
	rows = []
	total = 0.0
	for row in pi.get("custom_deductions") or []:
		if row.get("is_weight_deduction") or row.get("is_bag_deduction"):
			continue
		amt = flt(row.amount)
		total += amt
		rows.append(
			{
				"sr": row.idx,
				"particulars": row.deduction_type_name or row.deduction_type,
				"required": row.required_value if row.required_value is not None else "",
				"actual": row.actual if row.actual is not None else "",
				"diff": row.difference if row.difference is not None else "",
				"value": fmt_money(amt, currency=pi.currency),
			}
		)
	return rows, total


def _debit_lines(debit):
	if not debit:
		return []
	lines = []
	sr = 0
	if flt(debit.get("custom_weight_deduction")):
		sr += 1
		lines.append(
			{
				"sr": sr,
				"particulars": "Weight Shortage",
				"hsn": "",
				"qty": f"{flt(debit.custom_weight_deduction):g} kg",
				"rate": "",
				"amount": fmt_money(debit.get("custom_weight_deduction_amount") or 0, currency=debit.currency),
			}
		)
	if flt(debit.get("custom_bag_deduction")):
		sr += 1
		lines.append(
			{
				"sr": sr,
				"particulars": "Bags Weight",
				"hsn": "",
				"qty": f"{flt(debit.custom_bag_deduction):g} kg",
				"rate": "",
				"amount": fmt_money(debit.get("custom_bag_deduction_amount") or 0, currency=debit.currency),
			}
		)
	deduction_item = None
	for row in debit.get("items") or []:
		label = (row.item_name or row.item_code or "").lower()
		if "quality" in label:
			deduction_item = row
			break
	if deduction_item:
		sr += 1
		rate_suffix = "/QT"
		uom = (deduction_item.uom or "Quintal").strip()
		if not uom.lower().startswith("quint"):
			rate_suffix = f"/{uom[:3].upper()}"
		rate_txt = fmt_money(deduction_item.rate, currency=debit.currency)
		lines.append(
			{
				"sr": sr,
				"particulars": "Quality and other deductions",
				"hsn": deduction_item.gst_hsn_code or "",
				"qty": f"{abs(flt(deduction_item.qty)):g} {deduction_item.uom or ''}".strip(),
				"rate": f"{rate_txt} {rate_suffix}".strip(),
				"amount": fmt_money(deduction_item.amount, currency=debit.currency),
			}
		)
	for row in debit.get("items") or []:
		if deduction_item and row.name == deduction_item.name:
			continue
		sr += 1
		lines.append(
			{
				"sr": sr,
				"particulars": row.item_name or row.item_code,
				"hsn": row.gst_hsn_code or "",
				"qty": f"{abs(flt(row.qty)):g} {row.uom or ''}".strip(),
				"rate": fmt_money(row.rate, currency=debit.currency),
				"amount": fmt_money(row.amount, currency=debit.currency),
			}
		)
	return lines


def _summary_row(label, doc, currency):
	if not doc:
		return {
			"document": label,
			"basic_net_tds": fmt_money(0, currency=currency),
			"gst": fmt_money(0, currency=currency),
			"net_payable": fmt_money(0, currency=currency),
		}
	taxes = _tax_breakup(doc)
	basic = flt(doc.net_total) or flt(doc.total)
	basic_net = basic - taxes["tds"]
	return {
		"document": label,
		"basic_net_tds": fmt_money(basic_net, currency=currency),
		"gst": fmt_money(taxes["gst_total"], currency=currency),
		"net_payable": fmt_money(doc.grand_total, currency=currency),
	}


@frappe.whitelist()
def get_settlement_print_data(purchase_invoice):
	pi = _load_pi(purchase_invoice)
	debit = _get_debit_note(pi)
	company = frappe.get_doc("Company", pi.company)
	supplier = pi.supplier
	party_loc = _party_location(supplier)
	company_address = _company_address(pi.company)
	our_loc = company_address
	quality_rows, quality_total = _quality_rows(pi)
	debit_tax = _tax_breakup(debit) if debit else _tax_breakup(None)
	bargain_rows, bargain_total = _bargain_rows(pi)
	net_payable = flt(pi.grand_total) + flt(debit.grand_total if debit else 0)
	arrival = flt(pi.get("custom_total_arrival_weight"))
	final_rate = 0.0
	if arrival > 0:
		final_rate = net_payable / (arrival / 100.0)

	return {
		"pi_name": pi.name,
		"currency": pi.currency,
		"company_name": company.company_name,
		"company_abbr": company.abbr or "",
		"company_logo": _company_logo_url(company),
		"company_address": company_address,
		"company_address_line": _address_one_line(company_address),
		"company_gstin": company.gstin or "",
		"party": pi.supplier_name or pi.supplier,
		"party_location": party_loc,
		"party_gstin": frappe.db.get_value("Supplier", supplier, "gstin") if supplier else "",
		"broker": _broker_label(pi.get("custom_broker")),
		"our_invoice_no": pi.name,
		"invoice_date": frappe.format(pi.posting_date, {"fieldtype": "Date"}),
		"our_location": our_loc,
		"our_gstin": company.gstin or "",
		"po_no": _purchase_orders(pi),
		"arrival_date": frappe.format(pi.bill_date or pi.posting_date, {"fieldtype": "Date"}),
		"debit_note_no": debit.name if debit else "",
		"debit_note_date": frappe.format(debit.posting_date, {"fieldtype": "Date"}) if debit else "",
		"vendor_doc_no": pi.bill_no or "",
		"vendor_doc_date": frappe.format(pi.bill_date, {"fieldtype": "Date"}) if pi.bill_date else "",
		"vendor_bill_amount": fmt_money(
			pi.get("custom_supplier_invoice_amount") or pi.grand_total, currency=pi.currency
		),
		"lorry_no": pi.get("lr_no") or pi.get("custom_lorry_no") or "",
		"pi_lines": _pi_lines(pi),
		"pi_total_payable": fmt_money(pi.grand_total, currency=pi.currency),
		"bargain_rows": bargain_rows,
		"bargain_total": bargain_total,
		"quality_rows": quality_rows,
		"quality_total": fmt_money(quality_total, currency=pi.currency),
		"debit_lines": _debit_lines(debit),
		"debit_tax": debit_tax,
		"debit_tax_sidebar": _tax_sidebar(debit, pi.currency) if debit else [],
		"debit_grand_total": fmt_money(debit.grand_total, currency=pi.currency) if debit else fmt_money(0, currency=pi.currency),
		"summary_pi": _summary_row("Purchase Invoice", pi, pi.currency),
		"summary_debit": _summary_row("Debit Note", debit, pi.currency),
		"net_payable": fmt_money(net_payable, currency=pi.currency),
		"final_rate": fmt_money(final_rate, currency=pi.currency) if final_rate else "",
		"printed_by": frappe.session.user,
		"printed_on": now_datetime().strftime("%d-%m-%Y %H:%M"),
	}
