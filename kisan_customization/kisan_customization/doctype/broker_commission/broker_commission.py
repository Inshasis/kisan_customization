# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from erpnext.accounts.party import get_party_account


class BrokerCommission(Document):
	def validate(self):
		if flt(self.broker_commission_amount) <= 0:
			frappe.throw(_("Broker Commission Amount must be greater than zero"))

		self._validate_unique_purchase_invoice()

	def on_submit(self):
		if not self.journal_entry:
			je_name = create_broker_commission_journal_entry(self)
			self.db_set("journal_entry", je_name, update_modified=False)

	def on_cancel(self):
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.flags.ignore_permissions = True
				je.cancel()

	def _validate_unique_purchase_invoice(self):
		if not self.purchase_invoice:
			return

		filters = {
			"purchase_invoice": self.purchase_invoice,
			"docstatus": ("<", 2),
			"name": ("!=", self.name),
		}
		if frappe.db.exists("Broker Commission", filters):
			frappe.throw(
				_("Broker Commission already exists for Purchase Invoice {0}").format(
					self.purchase_invoice
				)
			)


def create_broker_commission_journal_entry(doc):
	expense_account = _get_broker_commission_expense_account(doc.company)

	payable_account = get_party_account("Supplier", doc.broker, doc.company)
	amount = flt(doc.broker_commission_amount)
	cost_center = _get_cost_center(doc)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = getdate(doc.posting_date)
	je.company = doc.company
	je.user_remark = _("Broker Commission against Purchase Invoice {0}").format(doc.purchase_invoice)

	je.append(
		"accounts",
		{
			"account": expense_account,
			"debit_in_account_currency": amount,
			"cost_center": cost_center,
		},
	)
	je.append(
		"accounts",
		{
			"account": payable_account,
			"credit_in_account_currency": amount,
			"party_type": "Supplier",
			"party": doc.broker,
			"cost_center": cost_center,
		},
	)

	je.insert(ignore_permissions=True)
	je.flags.ignore_permissions = True
	je.submit()

	return je.name


def _get_broker_commission_expense_account(company):
	meta = frappe.get_meta("Kisan Master Settings", cached=False)
	if not meta.has_field("broker_commission_expense_account"):
		frappe.throw(
			_(
				"Broker Commission Expense Account field is missing on {0}. "
				"Please update kisan_customization and run bench migrate."
			).format(frappe.bold(_("Kisan Master Settings")))
		)

	expense_account = frappe.db.get_single_value(
		"Kisan Master Settings", "broker_commission_expense_account"
	)
	if not expense_account:
		frappe.throw(
			_("Set Broker Commission Expense Account in {0}").format(
				frappe.bold(_("Kisan Master Settings"))
			)
		)

	if not frappe.db.exists("Account", {"name": expense_account, "company": company}):
		frappe.throw(_("Account {0} does not belong to company {1}").format(expense_account, company))

	return expense_account


def _get_cost_center(doc):
	pi_cost_center = frappe.db.get_value("Purchase Invoice", doc.purchase_invoice, "cost_center")
	if pi_cost_center:
		return pi_cost_center

	item_cost_center = frappe.db.get_value(
		"Purchase Invoice Item",
		{"parent": doc.purchase_invoice, "parenttype": "Purchase Invoice"},
		"cost_center",
	)
	if item_cost_center:
		return item_cost_center

	return frappe.get_cached_value("Company", doc.company, "cost_center")
