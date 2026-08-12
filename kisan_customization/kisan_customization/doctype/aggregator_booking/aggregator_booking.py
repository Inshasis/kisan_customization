# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from kisan_customization.aggregator_booking.purchase_orders import (
	cancel_purchase_orders_for_booking,
	create_purchase_orders_for_booking,
)


class AggregatorBooking(Document):
	def validate(self):
		self._set_company_defaults()
		self._validate_items()
		self._calculate_totals()

	def on_submit(self):
		if self.purchase_orders:
			frappe.throw(_("Purchase Orders are already linked with this booking"))

		create_purchase_orders_for_booking(self)

	def on_cancel(self):
		cancel_purchase_orders_for_booking(self)

	def _set_company_defaults(self):
		if self.company:
			return

		default_company = frappe.db.get_single_value("Kisan Master Settings", "default_company")
		if default_company:
			self.company = default_company
		else:
			self.company = frappe.defaults.get_global_default("company")

	def _validate_items(self):
		if not self.items:
			frappe.throw(_("Add at least one item row"))

		suppliers = set()
		for row in self.items:
			if not row.supplier:
				frappe.throw(_("Supplier is required in row {0}").format(row.idx))
			if not row.item_code:
				frappe.throw(_("Item is required in row {0}").format(row.idx))
			if flt(row.qty) <= 0:
				frappe.throw(_("Qty must be greater than zero in row {0}").format(row.idx))
			if flt(row.rate) < 0:
				frappe.throw(_("Rate cannot be negative in row {0}").format(row.idx))

			row.amount = flt(row.qty) * flt(row.rate)
			suppliers.add(row.supplier)

		if not suppliers:
			frappe.throw(_("At least one supplier is required"))

	def _calculate_totals(self):
		total_qty = 0
		grand_total = 0
		suppliers = set()

		for row in self.items:
			row.amount = flt(row.qty) * flt(row.rate)
			total_qty += flt(row.qty)
			grand_total += flt(row.amount)
			if row.supplier:
				suppliers.add(row.supplier)

		self.total_qty = total_qty
		self.grand_total = grand_total
		self.no_of_suppliers = len(suppliers)
