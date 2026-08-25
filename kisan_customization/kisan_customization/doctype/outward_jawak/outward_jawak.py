# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
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


class OutwardJawak(Document):
	def autoname(self):
		"""
		Custom naming to support firm-wise sequences, matching Inward Aawak pattern.
		
		Each firm gets its own independent sequence.
		Format: JAWAK-{firm_sequence}-YYYY-####
		
		Where:
		- firm_sequence is the firm's auto-generated number (e.g., FIRM-0001 -> 0001)
		- YYYY is the year
		- #### is the sequence number for that firm
		
		Example: JAWAK-0001-2025-0001 (Firm FIRM-0001, first jawak of 2025)
		         JAWAK-0002-2025-0001 (Firm FIRM-0002, first jawak of 2025)
		"""
		if self.firm:
			# Get the firm's sequence number from its name
			# Firm name format is FIRM-0001, FIRM-0002, etc.
			firm_parts = self.firm.split('-')
			if len(firm_parts) >= 2:
				firm_seq = firm_parts[-1]  # Extract the numeric part (e.g., "0001")
			else:
				# Fallback if firm name doesn't follow expected format
				firm_seq = self.firm.replace('FIRM-', '').replace('FIRM', '')[:4].zfill(4)
			
			# Create firm-specific series key
			# This ensures each firm has its own sequence counter
			series_key = f"JAWAK-.{self.firm}-.YYYY.-.####"
			
			# Get next number from firm-specific series
			full_name = make_autoname(series_key)
			
			# Extract year and sequence number from the generated name
			# Format will be: JAWAK-FIRM-0001-2025-0001
			parts = full_name.split('-')
			
			if len(parts) >= 2:
				year = parts[-2]
				sequence = parts[-1]
				# Create final name with firm sequence included
				self.name = f"JAWAK-{firm_seq}-{year}-{sequence}"
				# Set lot number (sequence only) for printing/receipts
				self.lot_number = sequence
			else:
				# Fallback in case of unexpected format
				self.name = full_name
		else:
			# Fallback for legacy records or if firm is not set
			# This maintains backward compatibility
			self.name = make_autoname("JAWAK-.YYYY.-.####")
			self.lot_number = self.name.split('-')[-1] if '-' in self.name else ""
	
	def validate(self):
		self._validate_commodities()
		validate_outward_release_bags(self)

		if self.docstatus == 0:
			self.status = STATUS_DRAFT

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
