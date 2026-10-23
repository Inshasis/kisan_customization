# Copyright (c) 2026, Hidayatali and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, cstr, flt, getdate

from kisan_customization.inward_aawak.delivery import (
	STATUS_SUBMITTED,
	update_inward_delivery_status,
)


class InwardAawak(Document):
	def validate(self):
		"""Validate the document before saving"""
		if self.is_new() and not self.firm:
			frappe.throw(_("Firm is mandatory for new Inward Aawak records"))

		if not self.naming_series:
			frappe.throw(_("Naming Series is required"))

		self._validate_lot_number()
		self._validate_bag_lorry_weights()
		self._sync_total_lorry_weight()
		self._sync_chamber_allocation_dates()

		if self.docstatus == 1:
			self._sync_delivery_totals()

	def on_submit(self):
		self.db_set(
			{
				"status": STATUS_SUBMITTED,
				"released_bags": 0,
				"remaining_bags": cint(self.total_bags or 0),
			},
			update_modified=False,
		)

	def on_cancel(self):
		self.db_set(
			{
				"released_bags": 0,
				"remaining_bags": cint(self.total_bags or 0),
			},
			update_modified=False,
		)

	def _validate_lot_number(self):
		lot = cstr(self.lot_number).strip()
		if not lot:
			frappe.throw(_("Lot Number is mandatory"), title=_("Required Field Missing"))

		filters = {
			"lot_number": lot,
			"name": ["!=", self.name or ""],
			"docstatus": ["!=", 2],
		}
		if self.firm:
			filters["firm"] = self.firm

		existing = frappe.db.get_value("Inward Aawak", filters, "name")
		if existing:
			frappe.throw(
				_("Lot Number {0} is already used in Inward Aawak {1}.").format(lot, existing),
				title=_("Duplicate Lot Number"),
			)

	def _sync_chamber_allocation_dates(self):
		if not self.chamber_allocations:
			return
		alloc_date = getdate(self.aawak_date) if self.aawak_date else None
		for row in self.chamber_allocations:
			row.allocation_date = alloc_date
			row.valid_to = add_months(alloc_date, 6) if alloc_date else None

	def _validate_bag_lorry_weights(self):
		for idx, row in enumerate(self.get("bag_details") or [], start=1):
			if row.lorry_weight_kg in (None, ""):
				continue
			if flt(row.lorry_weight_kg) < 0:
				frappe.throw(
					_("Row {0}: Lorry Weight (Kg) cannot be negative.").format(idx),
					title=_("Bag Details Error"),
				)

	def _sync_total_lorry_weight(self):
		"""Sum bag line lorry weights when present; else keep manual total_lorry_weight on the form."""
		lorry_values = [
			flt(row.lorry_weight_kg)
			for row in self.get("bag_details") or []
			if row.lorry_weight_kg not in (None, "") and flt(row.lorry_weight_kg) > 0
		]
		if lorry_values:
			self.total_lorry_weight = flt(sum(lorry_values), 2)

	def _sync_delivery_totals(self):
		update_inward_delivery_status(self.name)
		self.released_bags = cint(
			frappe.db.get_value("Inward Aawak", self.name, "released_bags") or 0
		)
		self.remaining_bags = cint(
			frappe.db.get_value("Inward Aawak", self.name, "remaining_bags") or 0
		)
		self.status = frappe.db.get_value("Inward Aawak", self.name, "status") or STATUS_SUBMITTED
