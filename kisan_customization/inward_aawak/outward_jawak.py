# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from kisan_customization.inward_aawak.delivery import get_remaining_bag_details
from kisan_customization.outward_jawak.status import STATUS_DRAFT


@frappe.whitelist()
def create_draft_outward_jawak(inward_aawak):
	inward = frappe.get_doc("Inward Aawak", inward_aawak)
	if inward.docstatus != 1:
		frappe.throw(_("Create Jawak is only available for submitted Inward Aawak records."))

	existing = frappe.db.get_value(
		"Outward Jawak",
		{"inward_aawak": inward.name, "docstatus": 0},
		"name",
		order_by="modified desc",
	)
	if existing:
		return {"name": existing, "created": False}

	if not inward.lot_number:
		frappe.throw(_("Inward Lot Number is missing on this Aawak entry."))

	remaining = get_remaining_bag_details(inward.firm, inward.lot_number)
	if not remaining.get("bag_details"):
		frappe.throw(_("No remaining bags are available for outward on this Aawak entry."))

	doc = frappe.new_doc("Outward Jawak")
	doc.firm = inward.firm
	doc.inward_lot_no = inward.lot_number
	doc.inward_aawak = inward.name
	doc.jawak_date = now_datetime()
	doc.storage_customer = inward.storage_customer
	doc.godown = inward.godown
	doc.inward_charges = inward.charges or 0
	doc.status = STATUS_DRAFT

	if inward.chamber_allocations:
		alloc = inward.chamber_allocations[0]
		doc.floor = alloc.floor
		doc.chamber = alloc.chamber

	for row in inward.commodities or []:
		if row.commodity:
			doc.append("commodities", {"commodity": row.commodity})

	for bag in remaining["bag_details"]:
		doc.append(
			"jawak_bag_details",
			{
				"line_key": bag.get("line_key"),
				"bag_configuration": bag.get("bag_configuration"),
				"bag_type": bag.get("bag_type"),
				"rate_type": bag.get("rate_type"),
				"commodity": bag.get("commodity"),
				"uom": bag.get("uom"),
				"weight_kg": bag.get("weight_kg"),
				"total_bags": bag.get("remaining_bags"),
				"release_bags": bag.get("remaining_bags"),
				"rate": bag.get("rate") or 0,
			},
		)

	doc.insert()
	return {"name": doc.name, "created": True}
