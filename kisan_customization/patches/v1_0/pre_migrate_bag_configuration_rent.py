# Copyright (c) 2026, Hidayatali and contributors

import frappe


def execute():
	if not frappe.db.has_column("Bag Configuration", "bag_weight"):
		return

	if frappe.db.has_column("Bag Configuration", "weight_kg"):
		frappe.db.sql(
			"""
			UPDATE `tabBag Configuration`
			SET weight_kg = bag_weight
			WHERE (weight_kg IS NULL OR weight_kg = 0) AND bag_weight IS NOT NULL
			"""
		)

	if frappe.db.has_column("Bag Configuration", "rate_per_bag_per_day") and frappe.db.has_column(
		"Bag Configuration", "rate"
	):
		frappe.db.sql(
			"""
			UPDATE `tabBag Configuration`
			SET rate = rate_per_bag_per_day
			WHERE (rate IS NULL OR rate = 0) AND rate_per_bag_per_day IS NOT NULL
			"""
		)
