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

		self._validate_reference_invoice()
		self._validate_unique_reference()

	def on_submit(self):
		if not self.journal_entry:
			je_name = create_broker_commission_journal_entry(self)
			self.db_set("journal_entry", je_name, update_modified=False)

	def on_cancel(self):
		if self.journal_entry:
			_cancel_linked_journal_entry(self.journal_entry)

	def _validate_reference_invoice(self):
		if bool(self.purchase_invoice) == bool(self.sales_invoice):
			frappe.throw(
				_("Set either Purchase Invoice or Sales Invoice, but not both.")
			)

	def _validate_unique_reference(self):
		if self.purchase_invoice:
			self._validate_unique_link("purchase_invoice", self.purchase_invoice, _("Purchase Invoice"))
		if self.sales_invoice:
			self._validate_unique_link("sales_invoice", self.sales_invoice, _("Sales Invoice"))

	def _validate_unique_link(self, fieldname, value, label):
		filters = {
			fieldname: value,
			"docstatus": ("<", 2),
			"name": ("!=", self.name),
		}
		if frappe.db.exists("Broker Commission", filters):
			frappe.throw(_("Broker Commission already exists for {0} {1}").format(label, value))


def create_broker_commission_journal_entry(doc):
	expense_account = _get_broker_commission_expense_account(doc.company)
	payable_account = get_party_account("Supplier", doc.broker, doc.company)
	amount = flt(doc.broker_commission_amount)
	cost_center = _get_cost_center(doc)
	invoice_doctype, invoice_name = _get_reference_invoice(doc)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = getdate(doc.posting_date)
	je.company = doc.company
	je.user_remark = _("Broker Commission against {0} {1}").format(invoice_doctype, invoice_name)

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


def _get_reference_invoice(doc):
	if doc.purchase_invoice:
		return "Purchase Invoice", doc.purchase_invoice
	return "Sales Invoice", doc.sales_invoice


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
	invoice_doctype, invoice_name = _get_reference_invoice(doc)
	cost_center = frappe.db.get_value(invoice_doctype, invoice_name, "cost_center")
	if cost_center:
		return cost_center

	item_doctype = f"{invoice_doctype} Item"
	item_cost_center = frappe.db.get_value(
		item_doctype,
		{"parent": invoice_name, "parenttype": invoice_doctype},
		"cost_center",
	)
	if item_cost_center:
		return item_cost_center

	return frappe.get_cached_value("Company", doc.company, "cost_center")


def _cancel_linked_journal_entry(je_name):
	if not je_name or not frappe.db.exists("Journal Entry", je_name):
		return

	je = frappe.get_doc("Journal Entry", je_name)
	if je.docstatus != 1:
		return

	je.flags.ignore_permissions = True
	je.cancel()
