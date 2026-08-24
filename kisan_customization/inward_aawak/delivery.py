# Copyright (c) 2026, Hidayatali and contributors

import frappe
from frappe import _
from frappe.utils import cint

STATUS_SUBMITTED = "Submitted"
STATUS_PARTIALLY_DELIVERED = "Partially Delivered"
STATUS_FULLY_DELIVERED = "Fully Delivered"

DELIVERY_STATUSES = (
	STATUS_SUBMITTED,
	STATUS_PARTIALLY_DELIVERED,
	STATUS_FULLY_DELIVERED,
)


def normalize_bag_type(value):
	if value in (None, ""):
		return ""

	try:
		return str(int(float(value)))
	except (TypeError, ValueError):
		return str(value).strip()


def get_inward_aawak(firm, lot_number, docstatus=1):
	records = frappe.get_all(
		"Inward Aawak",
		filters={"firm": firm, "lot_number": lot_number, "docstatus": docstatus},
		fields=["name", "status", "total_bags", "firm", "lot_number"],
		limit=2,
	)

	if not records:
		frappe.throw(
			_("No submitted Inward Aawak found for Firm {0} and Lot {1}").format(firm, lot_number)
		)

	if len(records) > 1:
		frappe.throw(
			_("Multiple Inward Aawak records found for Firm {0} and Lot {1}").format(
				firm, lot_number
			)
		)

	return records[0]


def get_inward_bag_map(inward_name):
	bag_map = {}

	for row in frappe.get_all(
		"Bag Details",
		filters={"parent": inward_name, "parenttype": "Inward Aawak"},
		fields=["bag_weight", "number_of_bags"],
	):
		key = normalize_bag_type(row.bag_weight)
		if not key:
			continue

		bag_map[key] = bag_map.get(key, 0) + cint(row.number_of_bags)

	return bag_map


def get_submitted_jawak_names(firm, lot_number, exclude_jawak=None):
	names = frappe.get_all(
		"Outward Jawak",
		filters={
			"firm": firm,
			"inward_lot_no": lot_number,
			"docstatus": 1,
		},
		pluck="name",
	)

	if exclude_jawak:
		names = [name for name in names if name != exclude_jawak]

	return names


def get_released_bag_map(firm, lot_number, exclude_jawak=None):
	bag_map = {}

	for jawak_name in get_submitted_jawak_names(firm, lot_number, exclude_jawak):
		for row in frappe.get_all(
			"Jawak Bag Detail",
			filters={"parent": jawak_name, "parenttype": "Outward Jawak"},
			fields=["bag_type", "release_bags"],
		):
			key = normalize_bag_type(row.bag_type)
			if not key:
				continue

			bag_map[key] = bag_map.get(key, 0) + cint(row.release_bags)

	return bag_map


def get_remaining_bag_map(firm, lot_number, exclude_jawak=None):
	inward = get_inward_aawak(firm, lot_number)
	inward_map = get_inward_bag_map(inward.name)
	released_map = get_released_bag_map(firm, lot_number, exclude_jawak)

	remaining_map = {}
	for bag_type, inward_qty in inward_map.items():
		remaining_map[bag_type] = max(0, inward_qty - released_map.get(bag_type, 0))

	return remaining_map, inward


def compute_delivery_status(inward_name, firm, lot_number, exclude_jawak=None):
	inward_map = get_inward_bag_map(inward_name)
	released_map = get_released_bag_map(firm, lot_number, exclude_jawak)

	total_inward = sum(inward_map.values())
	total_released = sum(released_map.values())

	if total_released <= 0:
		return STATUS_SUBMITTED

	if total_released >= total_inward:
		for bag_type, inward_qty in inward_map.items():
			if released_map.get(bag_type, 0) < inward_qty:
				return STATUS_PARTIALLY_DELIVERED
		return STATUS_FULLY_DELIVERED

	return STATUS_PARTIALLY_DELIVERED


def update_inward_delivery_status(inward_name, exclude_jawak=None):
	if frappe.db.get_value("Inward Aawak", inward_name, "docstatus") != 1:
		return

	firm, lot_number, total_inward = frappe.db.get_value(
		"Inward Aawak", inward_name, ["firm", "lot_number", "total_bags"]
	)

	released_map = get_released_bag_map(firm, lot_number, exclude_jawak)
	total_released = sum(released_map.values())
	total_inward = cint(total_inward or 0)
	remaining_bags = max(0, total_inward - total_released)
	status = compute_delivery_status(inward_name, firm, lot_number, exclude_jawak)

	frappe.db.set_value(
		"Inward Aawak",
		inward_name,
		{
			"status": status,
			"released_bags": total_released,
			"remaining_bags": remaining_bags,
		},
		update_modified=False,
	)


def get_available_inward_lots(firm):
	records = frappe.get_all(
		"Inward Aawak",
		filters={"firm": firm, "docstatus": 1},
		fields=["name", "lot_number", "status", "remaining_bags", "total_bags", "released_bags"],
		order_by="lot_number asc",
		limit_page_length=500,
	)

	lots = []
	seen = set()

	for record in records:
		if not record.lot_number or record.lot_number in seen:
			continue

		update_inward_delivery_status(record.name)
		record = frappe.db.get_value(
			"Inward Aawak",
			record.name,
			["lot_number", "status", "remaining_bags", "total_bags", "released_bags"],
			as_dict=True,
		)

		remaining = cint(record.remaining_bags)
		if remaining <= 0:
			total_inward = cint(record.total_bags)
			released = cint(record.released_bags)
			if total_inward > released:
				remaining = total_inward - released

		if record.status == STATUS_FULLY_DELIVERED or remaining <= 0:
			continue

		seen.add(record.lot_number)
		lots.append(record.lot_number)

	return lots


def get_remaining_bag_details(firm, lot_number, exclude_jawak=None):
	remaining_map, inward = get_remaining_bag_map(firm, lot_number, exclude_jawak)
	inward_doc = frappe.get_doc("Inward Aawak", inward.name)

	bag_details = []
	for row in inward_doc.bag_details:
		bag_type = normalize_bag_type(row.bag_weight)
		remaining = remaining_map.get(bag_type, 0)
		if remaining <= 0:
			continue

		bag_details.append(
			{
				"bag_type": bag_type,
				"bag_weight": row.bag_weight,
				"remaining_bags": remaining,
				"rate": row.rate,
			}
		)

	return {
		"inward_aawak": inward.name,
		"status": inward.status,
		"remaining_bags": sum(remaining_map.values()),
		"bag_details": bag_details,
	}


def validate_outward_release_bags(doc):
	if not doc.firm or not doc.inward_lot_no:
		frappe.throw(_("Firm and Inward Lot No are required"))

	inward = get_inward_aawak(doc.firm, doc.inward_lot_no)
	if inward.status == STATUS_FULLY_DELIVERED and doc.docstatus == 0:
		frappe.throw(
			_("Inward Aawak {0} is fully delivered. No bags are available for outward.").format(
				inward.name
			)
		)

	remaining_map, inward = get_remaining_bag_map(
		doc.firm, doc.inward_lot_no, exclude_jawak=doc.name if doc.name else None
	)

	if not remaining_map and doc.docstatus == 0 and not doc.get("__islocal"):
		frappe.throw(_("No remaining bags available for this Inward Lot."))

	if not doc.jawak_bag_details:
		frappe.throw(_("Add at least one bag detail row"))

	for row in doc.jawak_bag_details:
		bag_type = normalize_bag_type(row.bag_type)
		remaining = remaining_map.get(bag_type, 0)

		if cint(row.release_bags) <= 0:
			frappe.throw(_("Release bags must be greater than zero in row {0}").format(row.idx))

		if cint(row.release_bags) > remaining:
			frappe.throw(
				_(
					"Release bags ({0}) exceed remaining bags ({1}) for bag type {2} kg in row {3}"
				).format(row.release_bags, remaining, bag_type, row.idx)
			)

		if cint(row.total_bags) > remaining:
			frappe.throw(
				_("Available bags ({0}) exceed remaining bags ({1}) for bag type {2} kg in row {3}").format(
					row.total_bags, remaining, bag_type, row.idx
				)
			)

	doc.inward_aawak = inward.name
