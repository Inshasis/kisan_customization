# Copyright (c) 2026, Hidayatali and contributors

"""Company-scoped master data that must survive Delete Company Transactions."""

COMPANY_MASTER_DOCTYPES = (
	"Deduction Type",
)


def get_company_master_doctypes():
	return list(COMPANY_MASTER_DOCTYPES)
