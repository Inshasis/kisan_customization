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


BOOKING_UOM = "Quintal"


class AggregatorBooking(Document):
	def validate(self):
		self._set_company_defaults()
		self._sync_items_from_header()
		self._validate_aggregator_qty()
		self._calculate_totals()
		calculate_booking_discount(self)
		apply_booking_dates(self)
		calculate_booking_broker_commission(self)

	def before_submit(self):
		self._sync_items_from_header()
		self._calculate_totals()
		self._validate_commodity_details()
		self._validate_items_for_submit()
		self._validate_aggregator_qty()
		self._validate_qty_match_on_submit()
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

	def _validate_commodity_details(self):
		if not self.commodity:
			frappe.throw(_("Commodity is required before submit"))
		if flt(self.rate) < 0:
			frappe.throw(_("Rate cannot be negative"))
		if flt(self.aggregator_qty) <= 0:
			frappe.throw(_("Aggregator Qty must be greater than zero before submit"))

	def _sync_items_from_header(self):
		if not self.commodity:
			return

		item_name = frappe.db.get_value("Item", self.commodity, "item_name")

		for row in self.items or []:
			if not _row_has_data(row) and not row.supplier:
				continue

			row.item_code = self.commodity
			row.item_name = item_name
			row.uom = BOOKING_UOM
			if self.rate is not None:
				row.rate = flt(self.rate)

	def _validate_qty_match_on_submit(self):
		aggregator_qty = flt(self.aggregator_qty)
		total_qty = flt(self.total_qty)

		if aggregator_qty != total_qty:
			frappe.throw(
				_("Aggregator Qty ({0}) must equal Total Qty ({1}) before submit").format(
					aggregator_qty, total_qty
				)
			)

	def _validate_aggregator_qty(self):
		limit = flt(self.aggregator_qty)
		if not limit:
			return

		child_qty = sum(flt(row.qty) for row in self.items or [] if _row_has_data(row))
		if child_qty > limit:
			frappe.throw(
				_("Sum of item quantities ({0}) cannot exceed Aggregator Qty ({1})").format(
					child_qty, limit
				)
			)

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
		if not flt(self.additional_discount_percentage) and not flt(self.discount_amount):
			return

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
