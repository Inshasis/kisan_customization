# Copyright (c) 2026, Hidayatali and contributors

import frappe


def get_deduction_parent_account(company):
	settings = frappe.get_single("Kisan Master Settings")
	if settings.deduction_parent_account:
		parent = frappe.db.get_value(
			"Account",
			settings.deduction_parent_account,
			["name", "is_group", "company"],
			as_dict=True,
		)
		if parent and parent.is_group and parent.company == company:
			return parent.name

	parent = frappe.db.get_value(
		"Account",
		{"account_name": "Indirect Expenses", "company": company, "is_group": 1},
	)
	if parent:
		return parent

	return create_deduction_accounts_group(company)


def create_deduction_accounts_group(company):
	group_name = "Deduction Accounts"
	existing = frappe.db.get_value(
		"Account",
		{"account_name": group_name, "company": company},
	)
	if existing:
		return existing

	parent = frappe.db.get_value(
		"Account",
		{"account_name": "Indirect Expenses", "company": company, "is_group": 1},
	)
	if not parent:
		frappe.throw(
			frappe._("Indirect Expenses account group not found for company {0}").format(company)
		)

	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": group_name,
			"parent_account": parent,
			"company": company,
			"is_group": 1,
		}
	)
	account.insert(ignore_permissions=True)
	return account.name


def create_deduction_account(deduction_type_name, company):
	parent_account = get_deduction_parent_account(company)

	existing = frappe.db.get_value(
		"Account",
		{"account_name": deduction_type_name, "company": company},
	)
	if existing:
		return existing

	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": deduction_type_name,
			"parent_account": parent_account,
			"company": company,
			"is_group": 0,
			"account_type": "Expense Account",
		}
	)
	account.insert(ignore_permissions=True)
	return account.name


def get_deduction_account_for_company(deduction_type, company):
	dt = frappe.get_doc("Deduction Type", deduction_type)
	if dt.company == company and dt.related_account:
		return dt.related_account

	return frappe.db.get_value(
		"Account",
		{"account_name": dt.deduction_type_name, "company": company},
	) or create_deduction_account(dt.deduction_type_name, company)


def get_all_deduction_accounts(company):
	accounts = frappe.get_all(
		"Deduction Type",
		filters={"is_active": 1, "company": company},
		pluck="related_account",
	)
	return [account for account in accounts if account]
