# Copyright (c) 2026, Hidayatali and contributors
"""Repair item GST amounts so GST Breakup matches Tax Breakup."""

import frappe
from frappe.utils import flt

from kisan_customization.purchase_invoice.deductions import refresh_item_gst_details


def execute():
	parents = frappe.db.sql(
		"""
		SELECT DISTINCT parent
		FROM `tabPurchase Invoice Item`
		WHERE IFNULL(taxable_value, 0) != 0
		  AND (
			(IFNULL(igst_rate, 0) != 0 AND IFNULL(igst_amount, 0) = 0)
			OR (IFNULL(cgst_rate, 0) != 0 AND IFNULL(cgst_amount, 0) = 0)
			OR (IFNULL(sgst_rate, 0) != 0 AND IFNULL(sgst_amount, 0) = 0)
		  )
		""",
		pluck=True,
	)
	for name in parents or []:
		doc = frappe.get_doc("Purchase Invoice", name)
		refresh_item_gst_details(doc)
		for item in doc.items:
			for tax in ("igst", "cgst", "sgst", "cess"):
				for suffix in ("rate", "amount"):
					field = f"{tax}_{suffix}"
					if item.meta.has_field(field):
						frappe.db.set_value(
							item.doctype,
							item.name,
							field,
							flt(item.get(field)),
							update_modified=False,
						)
