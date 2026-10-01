# Copyright (c) 2026, Hidayatali and contributors

import frappe


def preserve_submitted_payment_schedule(doc, method=None):
	"""Stop client onload from adding payment_schedule rows on Update After Submit."""
	if doc.docstatus != 1:
		return

	previous = frappe.get_doc("Purchase Invoice", doc.name)
	doc.set("payment_schedule", [])
	for row in previous.get("payment_schedule") or []:
		doc.append("payment_schedule", row.as_dict())

	if doc.get("is_return"):
		for fieldname in ("custom_payment_days", "custom_delivery_days"):
			if doc.meta.has_field(fieldname):
				doc.set(fieldname, previous.get(fieldname))

	if doc.meta.has_field("due_date"):
		doc.due_date = previous.due_date
