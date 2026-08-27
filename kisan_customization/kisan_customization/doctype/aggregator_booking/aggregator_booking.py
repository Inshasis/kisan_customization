# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kisan_customization.aggregator_booking.discount import (
	calculate_booking_discount,
	get_booking_effective_discount,
)
from kisan_customization.aggregator_booking.purchase_orders import (
	cancel_purchase_orders_for_booking,
	create_purchase_orders_for_booking,
)
from kisan_customization.aggregator_booking.terms import (
	apply_booking_dates,
	calculate_booking_broker_commission,
)


class AggregatorBooking(Document):
	def validate(self):
		self._set_company_defaults()
		self._calculate_totals()
		calculate_booking_discount(self)
		apply_booking_dates(self)
		calculate_booking_broker_commission(self)

	def before_submit(self):
		self._validate_items_for_submit()
		self._validate_discount()
		calculate_booking_discount(self)

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

	def _validate_items_for_submit(self):
		valid_rows = [row for row in self.items or [] if _row_has_data(row)]
		if not valid_rows:
			frappe.throw(_("Add at least one item row before submit"))

		suppliers = set()
		for row in valid_rows:
			if not row.supplier:
				frappe.throw(_("Supplier is required in row {0}").format(row.idx))
			if not row.item_code:
				frappe.throw(_("Item is required in row {0}").format(row.idx))
			if not row.uom:
				frappe.throw(_("UOM is required in row {0}").format(row.idx))
			if flt(row.qty) <= 0:
				frappe.throw(_("Qty must be greater than zero in row {0}").format(row.idx))
			if flt(row.rate) < 0:
				frappe.throw(_("Rate cannot be negative in row {0}").format(row.idx))

			row.amount = flt(row.qty) * flt(row.rate)
			suppliers.add(row.supplier)

		if not suppliers:
			frappe.throw(_("At least one supplier is required"))

	def _validate_discount(self):
		has_percent = flt(self.additional_discount_percentage) > 0
		has_amount = flt(self.discount_amount) > 0

		if not has_percent and not has_amount:
			frappe.throw(
				_("Please enter Discount Percent (%) or Discount Amount"),
				title=_("Discount Required"),
			)

		if flt(self.total_amount) and get_booking_effective_discount(self) > flt(self.total_amount):
			frappe.throw(_("Discount Amount cannot be greater than Total Amount"))

	def _calculate_totals(self):
		total_qty = 0
		total_amount = 0
		suppliers = set()

		for row in self.items or []:
			if not _row_has_data(row):
				continue

			row.amount = flt(row.qty) * flt(row.rate)
			total_qty += flt(row.qty)
			total_amount += flt(row.amount)
			if row.supplier:
				suppliers.add(row.supplier)

		self.total_qty = total_qty
		self.total_amount = total_amount
		self.no_of_suppliers = len(suppliers)


def _row_has_data(row):
	return row.supplier or row.item_code or flt(row.qty) or flt(row.rate)
