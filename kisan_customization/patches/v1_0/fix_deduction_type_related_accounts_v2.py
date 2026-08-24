# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	_restore_from_deduction_child_table()
	_restore_from_tax_history()
	frappe.db.commit()
	frappe.clear_cache(doctype="Deduction Type")


def _restore_from_deduction_child_table():
	if not frappe.db.table_exists("tabPurchase Invoice Deduction"):
		return

	rows = frappe.db.sql(
		"""
		select deduction_type, max(related_account) as related_account
		from `tabPurchase Invoice Deduction`
		where ifnull(related_account, '') != ''
			and ifnull(deduction_type, '') != ''
		group by deduction_type
		""",
		as_dict=True,
	)

	for row in rows:
		_set_related_account(row.deduction_type, row.related_account, force=True)


def _restore_from_tax_history():
	rows = frappe.db.sql(
		"""
		select description, account_head
		from `tabPurchase Taxes and Charges`
		where parenttype = 'Purchase Invoice'
			and add_deduct_tax = 'Deduct'
			and ifnull(account_head, '') != ''
			and ifnull(description, '') != ''
			and description not like 'Deductions:%%'
		order by modified desc
		""",
		as_dict=True,
	)

	seen_labels = {}
	for row in rows:
		label = (row.description or "").split("|")[0].strip()
		if label and label not in seen_labels:
			seen_labels[label] = row.account_head

	for label, account in seen_labels.items():
		name = frappe.db.get_value("Deduction Type", {"deduction_type_name": label}, "name")
		if name:
			_set_related_account(name, account)


def _set_related_account(deduction_type, account, force=False):
	if not account:
		return

	name = deduction_type
	if not frappe.db.exists("Deduction Type", name):
		name = frappe.db.get_value(
			"Deduction Type", {"deduction_type_name": deduction_type}, "name"
		)
	if not name:
		return

	if not frappe.db.sql(
		"select name from `tabAccount` where name=%s limit 1", (account,)
	):
		return

	if not force:
		current = frappe.db.get_value("Deduction Type", name, "related_account")
		if current:
			return

	frappe.db.set_value(
		"Deduction Type",
		name,
		"related_account",
		account,
		update_modified=False,
	)
