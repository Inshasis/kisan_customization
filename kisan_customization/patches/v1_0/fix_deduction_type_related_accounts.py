# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.patches.v1_0.restore_deduction_type_related_accounts import (
	_restore_from_deduction_child_table,
	_restore_from_tax_history,
)


def execute():
	_restore_from_deduction_child_table()
	_restore_from_tax_history()
