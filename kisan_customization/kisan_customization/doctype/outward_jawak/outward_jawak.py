# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from kisan_customization.inward_aawak.delivery import (
	get_available_inward_lots,
	get_remaining_bag_details,
	update_inward_delivery_status,
	validate_outward_release_bags,
)
from kisan_customization.outward_jawak.sales_invoice import (
	cancel_sales_invoice_for_jawak,
	create_sales_invoice_for_jawak,
)
from kisan_customization.outward_jawak.status import (
	STATUS_CANCELLED,
	STATUS_DRAFT,
	update_outward_jawak_status,
)
from kisan_customization.utils.rent_calculation import amounts_match, get_line_key, recompute_outward_jawak_amounts


class OutwardJawak(Document):
	def validate(self):
		if not self.naming_series:
			frappe.throw(_("Naming Series is required"))

		self._validate_commodities()
		self._ensure_jawak_line_keys()
		validate_outward_release_bags(self)
		self._sync_rent_amounts()

		if self.docstatus == 0:
			self.status = STATUS_DRAFT

	def _ensure_jawak_line_keys(self):
		for row in self.get("jawak_bag_details") or []:
			if row.line_key:
				continue

			row.line_key = get_line_key(
				bag_configuration=row.bag_configuration,
				commodity=row.commodity,
				uom=row.uom,
				weight_kg=row.weight_kg,
				bag_weight=row.bag_type,
			)

	def _sync_rent_amounts(self):
		if not self.jawak_bag_details or not self.jawak_date or not self.inward_aawak:
			return

		expected = recompute_outward_jawak_amounts(self)
		if not expected.get("aawak_date"):
			return

		if not amounts_match(self.total_amount, expected["total_amount"]):
			self.total_amount = expected["total_amount"]

		if not amounts_match(self.net_amount, expected["net_amount"]):
			self.net_amount = expected["net_amount"]

	def _validate_commodities(self):
		if not self.commodities:
			frappe.throw(_("Add at least one commodity"))

		for row in self.commodities:
			if not row.commodity:
				frappe.throw(_("Commodity is required in row {0}").format(row.idx))

			if not frappe.db.exists("Item", row.commodity):
				frappe.throw(
					_("Commodity {0} in row {1} is not a valid Item").format(row.commodity, row.idx)
				)

	def before_submit(self):
		if flt(self.net_amount) <= 0:
			frappe.throw(_("Net Amount must be greater than zero before submit"))

		validate_outward_release_bags(self)
		expected = recompute_outward_jawak_amounts(self)

		if not amounts_match(self.total_amount, expected["total_amount"]):
			frappe.throw(
				_("Total Amount mismatch. Please refresh rent calculation and save again.")
			)

		if not amounts_match(self.net_amount, expected["net_amount"]):
			frappe.throw(
				_("Net Amount mismatch. Please refresh rent calculation and save again.")
			)

	def on_submit(self):
		if self.sales_invoice:
			if frappe.db.exists("Sales Invoice", self.sales_invoice):
				si_docstatus = frappe.db.get_value("Sales Invoice", self.sales_invoice, "docstatus")
				if cint(si_docstatus) != 2:
					frappe.throw(_("Sales Invoice is already linked with this Outward Jawak"))
			self.db_set("sales_invoice", None, update_modified=False)

		create_sales_invoice_for_jawak(self)
		update_outward_jawak_status(self.name)

		if self.inward_aawak:
			update_inward_delivery_status(self.inward_aawak)

	def on_cancel(self):
		cancel_sales_invoice_for_jawak(self)

		frappe.db.set_value(
			"Outward Jawak", self.name, "status", STATUS_CANCELLED, update_modified=False
		)

		if self.inward_aawak:
			update_inward_delivery_status(self.inward_aawak)


@frappe.whitelist()
def get_available_lots(firm):
	return get_available_inward_lots(firm)


@frappe.whitelist()
def get_remaining_bags(firm, inward_lot_no, exclude_jawak=None):
	return get_remaining_bag_details(firm, inward_lot_no, exclude_jawak)


@frappe.whitelist()
def sync_status(name):
	return update_outward_jawak_status(name)
