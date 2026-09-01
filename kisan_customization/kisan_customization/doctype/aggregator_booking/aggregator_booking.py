# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from kisan_customization.aggregator_booking.discount import (
	calculate_booking_discount,
	get_booking_effective_discount,
)
from kisan_customization.aggregator_booking.purchase_invoices import (
	cancel_legacy_purchase_orders_for_booking,
	cancel_purchase_invoices_for_booking,
	create_purchase_invoices_for_booking,
)
from kisan_customization.aggregator_booking.terms import (
	apply_booking_dates,
	calculate_booking_broker_commission,
)


BOOKING_UOM = "Quintal"


class AggregatorBooking(Document):
	def validate(self):
		self._set_company_defaults()
		self._sync_items_from_commodities()
		self._calculate_commodity_allocations()
		self._validate_commodity_allocation_limits()
		self._calculate_totals()
		calculate_booking_discount(self)
		apply_booking_dates(self)
		calculate_booking_broker_commission(self)

	def before_submit(self):
		self._sync_items_from_commodities()
		self._calculate_commodity_allocations()
		self._calculate_totals()
		self._validate_commodity_details()
		self._validate_items_for_submit()
		self._validate_commodity_allocation_limits()
		self._validate_qty_match_on_submit()
		self._validate_discount()
		calculate_booking_discount(self)

	def on_submit(self):
		if self.purchase_invoices:
			frappe.throw(_("Purchase Invoices are already linked with this booking"))

		create_purchase_invoices_for_booking(self)

	def on_cancel(self):
		cancel_purchase_invoices_for_booking(self)
		cancel_legacy_purchase_orders_for_booking(self)

	def _set_company_defaults(self):
		if self.company:
			return

		default_company = frappe.db.get_single_value("Kisan Master Settings", "default_company")
		if default_company:
			self.company = default_company
		else:
			self.company = frappe.defaults.get_global_default("company")

	def _get_commodity_map(self):
		commodity_map = {}
		for row in self.commodities or []:
			if row.item_code:
				commodity_map[row.item_code] = row
		return commodity_map

	def _validate_commodity_details(self):
		valid_commodities = [row for row in self.commodities or [] if row.item_code]
		if not valid_commodities:
			frappe.throw(_("Add at least one commodity before submit"))

		seen_items = set()
		for row in valid_commodities:
			if row.item_code in seen_items:
				frappe.throw(_("Duplicate commodity {0} is not allowed").format(row.item_code))
			seen_items.add(row.item_code)

			if flt(row.rate) < 0:
				frappe.throw(_("Rate cannot be negative for {0}").format(row.item_code))
			if flt(row.aggregator_qty) <= 0:
				frappe.throw(_("Aggregator Qty must be greater than zero for {0}").format(row.item_code))

	def _sync_items_from_commodities(self):
		commodity_map = self._get_commodity_map()
		if not commodity_map:
			return

		for row in self.items or []:
			if not _row_has_data(row) and not row.supplier:
				continue

			if not row.item_code or row.item_code not in commodity_map:
				continue

			commodity = commodity_map[row.item_code]
			row.item_name = commodity.item_name or frappe.db.get_value(
				"Item", row.item_code, "item_name"
			)
			row.uom = BOOKING_UOM
			row.rate = flt(commodity.rate)

	def _calculate_commodity_allocations(self):
		allocated_by_item = {}
		for row in self.items or []:
			if not row.item_code or not _row_has_data(row):
				continue
			allocated_by_item[row.item_code] = allocated_by_item.get(row.item_code, 0) + flt(row.qty)

		for commodity in self.commodities or []:
			if not commodity.item_code:
				continue

			commodity.allocated_qty = flt(allocated_by_item.get(commodity.item_code, 0))
			commodity.amount = flt(commodity.aggregator_qty) * flt(commodity.rate)

	def _validate_qty_match_on_submit(self):
		for commodity in self.commodities or []:
			if not commodity.item_code:
				continue

			aggregator_qty = flt(commodity.aggregator_qty)
			allocated_qty = flt(commodity.allocated_qty)

			if aggregator_qty != allocated_qty:
				frappe.throw(
					_("Aggregator Qty ({0}) must equal Allocated Qty ({1}) for {2} before submit").format(
						aggregator_qty, allocated_qty, commodity.item_code
					)
				)

	def _validate_commodity_allocation_limits(self):
		allocated_by_item = {}
		for row in self.items or []:
			if not row.item_code or not _row_has_data(row):
				continue
			allocated_by_item[row.item_code] = allocated_by_item.get(row.item_code, 0) + flt(row.qty)

		for commodity in self.commodities or []:
			if not commodity.item_code:
				continue

			limit = flt(commodity.aggregator_qty)
			allocated = flt(allocated_by_item.get(commodity.item_code, 0))
			if allocated > limit:
				frappe.throw(
					_("Allocated quantity ({0}) cannot exceed Aggregator Qty ({1}) for {2}").format(
						allocated, limit, commodity.item_code
					)
				)

	def _validate_items_for_submit(self):
		valid_rows = [row for row in self.items or [] if _row_has_data(row)]
		if not valid_rows:
			frappe.throw(_("Add at least one supplier item row before submit"))

		commodity_map = self._get_commodity_map()
		suppliers = set()

		for row in valid_rows:
			if not row.supplier:
				frappe.throw(_("Supplier is required in row {0}").format(row.idx))
			if not row.item_code:
				frappe.throw(_("Item is required in row {0}").format(row.idx))
			if row.item_code not in commodity_map:
				frappe.throw(_("Item {0} in row {1} is not in Commodity Details").format(row.item_code, row.idx))
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
