# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from kisan_customization.utils.deduction_utils import evaluate_calculation


class DeductionType(Document):
	def validate(self):
		if self.related_account and not frappe.db.exists(
			"Account", {"name": self.related_account, "company": self.company}
		):
			frappe.throw(
				frappe._("Account {0} does not belong to company {1}").format(
					self.related_account, self.company
				)
			)

		if not (self.calculation or "").strip():
			return

		try:
			evaluate_calculation(
				self,
				net_amount=1000,
				total_qty=10,
				total_bags=10,
				total_gross_weight=500,
				actual=12,
				difference=2,
			)
		except Exception as exc:
			frappe.throw(frappe._("Invalid Calculation formula: {0}").format(str(exc)))
