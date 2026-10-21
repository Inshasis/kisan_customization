# Copyright (c) 2026, Hidayatali and contributors

import re

import frappe
from frappe.utils import flt, fmt_money, now_datetime, strip_html

from kisan_customization.purchase_invoice.deductions import (
	_calculate_bag_deduction_amount,
	_calculate_weight_deduction_amount,
)


def _fmt_print_amount(amount, currency):
	"""Settlement print: whole currency units (no paise/decimals on print)."""
	val = int(round(flt(amount or 0)))
	return fmt_money(val, currency=currency, precision=0)


def _fmt_print_debit_deduction(amount, currency):
	"""Debit note line deductions display as negative amounts on print."""
	val = -int(round(abs(flt(amount or 0))))
	if not val:
		return ""
	return fmt_money(val, currency=currency, precision=0)


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


def _is_gstin_address_line(line):
	return bool(re.search(r"\bgstin\b", line or "", re.I))


def _address_plain_lines(address_html, skip_gstin=False):
	if not address_html:
		return []
	text = re.sub(r"<br\s*/?>", "\n", address_html, flags=re.I)
	text = strip_html(text)
	lines = []
	seen = set()
	for raw in text.split("\n"):
		ln = _normalize_address_line(re.sub(r"\s+", " ", raw).strip())
		if not ln or (skip_gstin and _is_gstin_address_line(ln)):
			continue
		key = ln.lower()
		if key in seen:
			continue
		seen.add(key)
		lines.append(ln)
	return lines


def _normalize_address_line(line):
	if not line:
		return ""
	line = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", line)
	line = re.sub(r"(?<=\d)(PIN Code)", r", \1", line, flags=re.I)
	line = re.sub(r"PIN Code:\s*", "PIN Code: ", line, flags=re.I)
	line = re.sub(r"(?<=\d)(India)\b", r", \1", line, flags=re.I)
	line = re.sub(r"State Code:\s*(\d+)", r"State Code: \1", line, flags=re.I)
	line = re.sub(r"(\d{6})([A-Za-z])", r"\1, \2", line)
	return re.sub(r"\s+", " ", line).strip(" ,")


def _address_one_line(address_html):
	return ", ".join(_address_plain_lines(address_html))


def _address_for_print(address_html, skip_gstin=False):
	lines = _address_plain_lines(address_html, skip_gstin=skip_gstin)
	return "<br>".join(lines) if lines else ""


def _address_compact_meta(address_html):
	"""Single-line address for meta block (saves vertical space on A4)."""
	lines = _address_plain_lines(address_html, skip_gstin=True)
	if not lines:
		return ""
	text = ", ".join(lines)
	text = re.sub(r",\s*,+", ", ", text).strip(" ,")
	return text


def _address_header_two_lines(address_html):
	"""Letterhead address: at most two lines (GSTIN shown separately)."""
	lines = _address_plain_lines(address_html, skip_gstin=True)
	if not lines:
		return ""
	if len(lines) == 1:
		return lines[0]
	if len(lines) == 2:
		return "<br>".join(lines)
	mid = max(1, (len(lines) + 1) // 2)
	line1 = ", ".join(lines[:mid])
	line2 = ", ".join(lines[mid:])
	return f"{line1}<br>{line2}"


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
		return {"label": label, "amount": _fmt_print_amount(amount, currency)}

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
			"amount": _fmt_print_amount(doc.grand_total if doc else 0, currency),
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
		gst_cell = _fmt_print_amount(gst_amt, pi.currency)
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
				"rate": _fmt_print_amount(row.rate, pi.currency),
				"rate_suffix": rate_suffix,
				"basic": _fmt_print_amount(row.amount, pi.currency),
				"gst": gst_cell,
				"tds": "",
				"payable": _fmt_print_amount(payable, pi.currency),
			}
		)
	if lines and tds_total:
		lines[0]["tds"] = _fmt_print_amount(tds_total, pi.currency)
	if len(lines) == 1:
		lines[0]["payable"] = _fmt_print_amount(pi.grand_total, pi.currency)
	return lines


def _accepted_qty_kg(item):
	uom = (item.uom or "Quintal").lower()
	qty = flt(item.qty)
	if uom == "quintal":
		return abs(qty) * 100
	return abs(qty)


def _debit_return_kg_by_pi_item(debit):
	if not debit:
		return {}

	out = {}
	for row in debit.get("items") or []:
		pi_item_name = row.get("purchase_invoice_item")
		if not pi_item_name:
			continue
		out[pi_item_name] = flt(out.get(pi_item_name)) + _accepted_qty_kg(row)
	return out


def _po_line_for_pi_item(pi_row):
	if not pi_row.get("purchase_order"):
		return None
	if pi_row.get("po_detail"):
		return frappe.db.get_value(
			"Purchase Order Item",
			pi_row.po_detail,
			["name", "parent", "item_code", "item_name", "rate"],
			as_dict=True,
		)
	return frappe.db.get_value(
		"Purchase Order Item",
		{"parent": pi_row.purchase_order, "item_code": pi_row.item_code},
		["name", "parent", "item_code", "item_name", "rate"],
		as_dict=True,
	)


def _display_kg(kg):
	value = flt(kg)
	if not value:
		return ""
	if value == int(value):
		return f"{int(value):,}"
	return f"{value:,.2f}"


def _bargain_row_dict(
	po_name,
	item_label,
	sauda_rate,
	gross_kg,
	arr_kg,
	bags_cell,
	currency,
):
	amount = flt(sauda_rate * (flt(arr_kg) / 100), 2)
	return {
		"lot_no": po_name,
		"item": item_label,
		"bags": bags_cell,
		"gross_weight": _display_kg(gross_kg),
		"bags_wt": _display_kg(gross_kg),
		"sauda_rate": _fmt_print_amount(sauda_rate, currency),
		"arrival_weight": flt(arr_kg),
		"oil_pct": "",
		"oil_rate": "",
		"amount": _fmt_print_amount(amount, currency),
		"_amount_raw": amount,
	}


def _pi_commodity_item_rates(pi):
	from kisan_customization.purchase_invoice.item_gross_weight import get_commodity_items

	return [flt(row.rate) for row in get_commodity_items(pi) if flt(row.rate)]


def _pi_item_table_avg_rate(pi):
	from kisan_customization.purchase_invoice.bags import get_pi_avg_rate
	from kisan_customization.purchase_invoice.item_gross_weight import get_pi_weighted_item_rate

	rate = flt(get_pi_weighted_item_rate(pi))
	if rate:
		return rate
	rates = _pi_commodity_item_rates(pi)
	if not rates:
		rates = [flt(row.rate) for row in pi.get("items") or [] if flt(row.rate)]
	if rates:
		return flt(sum(rates) / len(rates))
	return flt(get_pi_avg_rate(pi))


def _resolve_deduction_line_rate(calc_rate, kg, amt, fallback_rate):
	rate = flt(calc_rate) or flt(fallback_rate)
	if not rate and kg and amt:
		rate = flt(amt * 100 / kg, 2)
	return rate


def _deduction_rate_display(rate, currency):
	rate = flt(rate)
	if not rate:
		return ""
	formatted = _fmt_print_amount(rate, currency) or f"{round(flt(rate)):,}"
	return f"{formatted} /QT"


def _bargain_rows(pi, debit=None):
	"""One print row per PI item line; gross weight from that line only (not summed)."""
	from kisan_customization.purchase_invoice.item_gross_weight import (
		get_commodity_items,
		get_item_line_gross_weight_kg,
	)

	debit_by_pi_item = _debit_return_kg_by_pi_item(debit)
	bags_total = flt(pi.get("custom_total_bags"))
	rows = []
	bargain_total = 0.0

	for idx, pi_row in enumerate(get_commodity_items(pi), start=1):
		po_line = _po_line_for_pi_item(pi_row)
		if po_line:
			lot_no = po_line.parent
			item_label = po_line.item_name or po_line.item_code
			sauda_rate = flt(po_line.rate)
		else:
			lot_no = pi_row.purchase_order or pi.get("custom_aggregator_booking") or ""
			item_label = pi_row.item_name or pi_row.item_code
			sauda_rate = flt(pi_row.rate)

		gross_kg = get_item_line_gross_weight_kg(pi_row)
		pi_kg = _accepted_qty_kg(pi_row)
		arr_kg = max(0, pi_kg - flt(debit_by_pi_item.get(pi_row.name, 0)))

		row = _bargain_row_dict(
			lot_no,
			item_label,
			sauda_rate,
			gross_kg,
			arr_kg,
			bags_total if idx == 1 else "",
			pi.currency,
		)
		bargain_total += row.pop("_amount_raw")
		rows.append(row)

	return rows, _fmt_print_amount(bargain_total, pi.currency)


MAX_QUALITY_PRINT_ROWS = 15


def _quality_rows(pi):
	rows = []
	total = 0.0
	for row in pi.get("custom_deductions") or []:
		if row.get("is_weight_deduction") or row.get("is_bag_deduction"):
			continue
		amt = flt(row.amount)
		total += amt
		if len(rows) >= MAX_QUALITY_PRINT_ROWS:
			continue
		rows.append(
			{
				"sr": row.idx,
				"particulars": row.deduction_type_name or row.deduction_type,
				"required": row.required_value if row.required_value is not None else "",
				"actual": row.actual if row.actual is not None else "",
				"diff": row.difference if row.difference is not None else "",
				"value": _fmt_print_amount(amt, pi.currency),
			}
		)
	return rows, total


def _debit_deduction_item_row(debit):
	from kisan_customization.purchase_invoice.deductions import get_deduction_item_code

	item_code = get_deduction_item_code()
	if not item_code:
		return None
	for row in debit.get("items") or []:
		if row.item_code == item_code:
			return row
	return None


def _debit_lines(debit, pi):
	if not debit:
		return []
	currency = pi.currency
	calc_weight_kg, calc_weight_rate, calc_weight_amt = _calculate_weight_deduction_amount(pi)
	calc_bag_kg, calc_bag_rate, calc_bag_amt = _calculate_bag_deduction_amount(pi)
	weight_kg = flt(pi.get("custom_weight_deduction")) or calc_weight_kg
	bag_kg = flt(pi.get("custom_bag_deduction")) or calc_bag_kg
	weight_amt = flt(pi.get("custom_weight_deduction_amount")) or calc_weight_amt
	bag_amt = flt(pi.get("custom_bag_deduction_amount")) or calc_bag_amt
	item_table_rate = _pi_item_table_avg_rate(pi)
	weight_rate = _resolve_deduction_line_rate(calc_weight_rate, weight_kg, weight_amt, item_table_rate)
	bag_rate = _resolve_deduction_line_rate(calc_bag_rate, bag_kg, bag_amt, item_table_rate)
	lines = []
	sr = 0
	if weight_kg or weight_amt:
		sr += 1
		lines.append(
			{
				"sr": sr,
				"particulars": "Weight Deduction",
				"hsn": "",
				"dn_qty": f"{weight_kg:g} kg",
				"dn_rate": _deduction_rate_display(weight_rate, currency),
				"amount": _fmt_print_debit_deduction(weight_amt, currency),
				"is_quality_row": 0,
			}
		)
	if bag_kg or bag_amt:
		sr += 1
		lines.append(
			{
				"sr": sr,
				"particulars": "Bag Deduction",
				"hsn": "",
				"dn_qty": f"{bag_kg:g} kg",
				"dn_rate": _deduction_rate_display(bag_rate, currency),
				"amount": _fmt_print_debit_deduction(bag_amt, currency),
				"is_quality_row": 0,
			}
		)
	deduction_item = _debit_deduction_item_row(debit)
	quality_amt = 0.0
	hsn = ""
	if deduction_item:
		quality_amt = flt(deduction_item.amount)
		hsn = deduction_item.gst_hsn_code or ""
	else:
		_, quality_total = _quality_rows(pi)
		quality_amt = flt(quality_total)
	if quality_amt or deduction_item:
		sr += 1
		lines.append(
			{
				"sr": sr,
				"particulars": "Quality Deduction",
				"hsn": hsn or "—",
				"dn_qty": "",
				"dn_rate": "",
				"amount": _fmt_print_amount(quality_amt, currency),
				"is_quality_row": 1,
			}
		)
	return lines


def _summary_row(label, doc, currency):
	if not doc:
		return {
			"document": label,
			"basic_net_tds": _fmt_settlement_amount(0, currency),
			"gst": _fmt_settlement_amount(0, currency),
			"net_payable": _fmt_settlement_amount(0, currency),
		}
	taxes = _tax_breakup(doc)
	basic = flt(doc.net_total) or flt(doc.total)
	basic_net = basic - taxes["tds"]
	return {
		"document": label,
		"basic_net_tds": _fmt_settlement_amount(basic_net, currency),
		"gst": _fmt_settlement_amount(taxes["gst_total"], currency),
		"net_payable": _fmt_settlement_amount(doc.grand_total, currency),
	}


def _fmt_settlement_amount(amount, currency):
	return _fmt_print_amount(amount, currency)


def _fmt_rounded_net_payable(amount, currency):
	return _fmt_print_amount(amount, currency)


def _summary_footer(pi, debit, currency):
	basic_net = 0.0
	gst = 0.0
	net_payable = 0.0
	for doc in (pi, debit):
		if not doc:
			continue
		taxes = _tax_breakup(doc)
		basic = flt(doc.net_total) or flt(doc.total)
		basic_net += basic - taxes["tds"]
		gst += taxes["gst_total"]
		net_payable += flt(doc.grand_total)
	return {
		"document": "Net Payable",
		"basic_net_tds": _fmt_settlement_amount(basic_net, currency),
		"gst": _fmt_settlement_amount(gst, currency),
		"net_payable": _fmt_settlement_amount(net_payable, currency),
	}


def _lorry_no_from_pi(pi):
	"""Print Lorry No. from PI Vehicle No (GST India field) and fallbacks."""
	if not pi or not pi.name:
		return ""
	candidate_fields = ("vehicle_no", "custom_lorry_no", "lr_no")
	for fieldname in candidate_fields:
		value = pi.get(fieldname)
		if value and str(value).strip():
			return str(value).strip()

	db_fields = [f for f in candidate_fields if frappe.db.has_column("Purchase Invoice", f)]
	if db_fields:
		row = frappe.db.get_value("Purchase Invoice", pi.name, db_fields, as_dict=True)
		if row:
			for fieldname in candidate_fields:
				value = row.get(fieldname)
				if value and str(value).strip():
					return str(value).strip()
	return ""


def get_kisan_settlement_print_data(purchase_invoice):
	"""Registered as Jinja method for Kisan Purchase Settlement Advice print format."""
	data = get_settlement_print_data(purchase_invoice)
	if not isinstance(data, dict):
		data = dict(data)
	if not data.get("summary_footer"):
		pi = _load_pi(purchase_invoice)
		debit = _get_debit_note(pi)
		data["summary_footer"] = _summary_footer(pi, debit, pi.currency)
	return data


@frappe.whitelist()
def get_settlement_print_data(purchase_invoice):
	pi = _load_pi(purchase_invoice)
	if frappe.session.user != "Guest":
		pi.check_permission("print")
	debit = _get_debit_note(pi)
	company = frappe.get_doc("Company", pi.company)
	supplier = pi.supplier
	party_loc = _party_location(supplier)
	company_address = _company_address(pi.company)
	our_loc = company_address
	quality_rows, quality_total = _quality_rows(pi)
	debit_tax = _tax_breakup(debit) if debit else _tax_breakup(None)
	bargain_rows, bargain_total = _bargain_rows(pi, debit)
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
		"company_address": company_address,
		"company_address_line": _address_one_line(company_address),
		"company_address_print": _address_header_two_lines(company_address),
		"company_gstin": company.gstin or "",
		"party": pi.supplier_name or pi.supplier,
		"party_location": party_loc,
		"party_location_print": _address_for_print(party_loc, skip_gstin=True),
		"party_location_compact": _address_compact_meta(party_loc),
		"party_gstin": frappe.db.get_value("Supplier", supplier, "gstin") if supplier else "",
		"broker": _broker_label(pi.get("custom_broker")),
		"our_invoice_no": pi.name,
		"invoice_date": frappe.format(pi.posting_date, {"fieldtype": "Date"}),
		"our_location": our_loc,
		"our_location_print": _address_for_print(our_loc, skip_gstin=True),
		"our_location_compact": _address_compact_meta(our_loc),
		"our_gstin": company.gstin or "",
		"po_no": _purchase_orders(pi),
		"arrival_date": frappe.format(pi.bill_date or pi.posting_date, {"fieldtype": "Date"}),
		"debit_note_no": debit.name if debit else "",
		"debit_note_date": frappe.format(debit.posting_date, {"fieldtype": "Date"}) if debit else "",
		"vendor_doc_no": pi.bill_no or "",
		"vendor_doc_date": frappe.format(pi.bill_date, {"fieldtype": "Date"}) if pi.bill_date else "",
		"vendor_bill_amount": _fmt_print_amount(
			pi.get("custom_supplier_invoice_amount") or pi.grand_total, pi.currency
		),
		"lorry_no": _lorry_no_from_pi(pi),
		"pi_lines": _pi_lines(pi),
		"pi_total_payable": _fmt_print_amount(pi.grand_total, pi.currency),
		"bargain_rows": bargain_rows,
		"bargain_total": bargain_total,
		"quality_rows": quality_rows,
		"quality_total": _fmt_print_amount(quality_total, pi.currency),
		"debit_lines": _debit_lines(debit, pi),
		"debit_tax": debit_tax,
		"debit_tax_sidebar": _tax_sidebar(debit, pi.currency) if debit else [],
		"debit_grand_total": _fmt_print_amount(debit.grand_total, pi.currency)
		if debit
		else _fmt_print_amount(0, pi.currency),
		"summary_pi": _summary_row("Purchase Invoice", pi, pi.currency),
		"summary_debit": _summary_row("Debit Note", debit, pi.currency),
		"summary_footer": _summary_footer(pi, debit, pi.currency),
		"net_payable": _fmt_rounded_net_payable(net_payable, pi.currency),
		"final_rate": _fmt_print_amount(final_rate, pi.currency) if final_rate else "",
		"printed_by": frappe.session.user,
		"printed_on": now_datetime().strftime("%d-%m-%Y %H:%M"),
	}
