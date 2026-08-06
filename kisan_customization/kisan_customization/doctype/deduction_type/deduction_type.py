# Copyright (c) 2026, Hidayatali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from kisan_customization.utils.account_utils import create_deduction_account


class DeductionType(Document):
	def before_insert(self):
		if not self.related_account:
			self.related_account = create_deduction_account(
				self.deduction_type_name, self.company
			)

	def validate(self):
		if not self.related_account:
			self.related_account = create_deduction_account(
				self.deduction_type_name, self.company
			)
		elif not frappe.db.exists(
			"Account", {"name": self.related_account, "company": self.company}
		):
			self.related_account = create_deduction_account(
				self.deduction_type_name, self.company
			)
