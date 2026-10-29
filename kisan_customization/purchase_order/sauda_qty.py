# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import flt

from kisan_customization.utils.transaction_mode import MODE_FIELD, MODE_KISAN


def validate(doc, method=None):
	if doc.get("is_return"):
		return

	if doc.get(MODE_FIELD) != MODE_KISAN:
		return

	if not doc.meta.has_field("custom_sauda_qty_from"):
		return

	qty_from = flt(doc.get("custom_sauda_qty_from"))
	qty_to = flt(doc.get("custom_sauda_qty_to"))

	if qty_from <= 0:
		frappe.throw(
			_("Sauda Qty From (Qtl) must be greater than zero when Transaction Mode is Kisan Custom.")
		)

	if qty_to <= 0:
		frappe.throw(
			_("Sauda Qty To (Qtl) must be greater than zero when Transaction Mode is Kisan Custom.")
		)
