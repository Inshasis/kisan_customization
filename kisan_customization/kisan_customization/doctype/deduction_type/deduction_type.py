# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kisan_customization.utils.deduction_utils import evaluate_calculation


class DeductionType(Document):
	def validate(self):
		if self.related_account and not frappe.db.exists(
			"Account", {"name": self.related_account, "company": self.company}
		):
			frappe.throw(
				_("Account {0} does not belong to company {1}").format(
					self.related_account, self.company
				)
			)

		if self.qty_deducation and (self.calculation or "").strip():
			frappe.throw(_("Clear Calculation when Qty Deducation is enabled."))

		if not self.qty_deducation and (self.calculation or "").strip():
			try:
				evaluate_calculation(self, net_amount=100, total_qty=10, total_bags=10)
			except Exception as exc:
				frappe.throw(_("Invalid Calculation formula: {0}").format(str(exc)))
