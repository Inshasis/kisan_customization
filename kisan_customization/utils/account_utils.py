# Copyright (c) 2026, Hidayatali and contributors

import frappe


def get_all_deduction_accounts(company):
	accounts = frappe.get_all(
		"Deduction Type",
		filters={"is_active": 1, "company": company},
		pluck="related_account",
	)
	return [account for account in accounts if account]
