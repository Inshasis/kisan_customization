# Copyright (c) 2026, Hidayatali and contributors

from frappe.utils import flt


def get_booking_effective_discount(booking):
	total = flt(booking.get("total_amount"))
	percent = flt(booking.get("additional_discount_percentage"))

	if percent > 0:
		return total * percent / 100

	return flt(booking.get("discount_amount"))


def calculate_booking_discount(booking):
	total = flt(booking.get("total_amount"))
	percent = flt(booking.get("additional_discount_percentage"))

	if percent > 0:
		booking.discount_amount = total * percent / 100

	booking.net_amount = total - flt(booking.get("discount_amount"))
	return flt(booking.discount_amount), flt(booking.net_amount)


def apply_booking_discount_to_po(po, booking):
	"""Apply booking discount to PO — percentage globally, amount split by supplier share."""
	booking_total = flt(booking.get("total_amount"))
	percent = flt(booking.get("additional_discount_percentage"))
	booking_discount = get_booking_effective_discount(booking)

	po.apply_discount_on = "Net Total"
	po.additional_discount_percentage = 0
	po.discount_amount = 0

	if percent > 0:
		po.additional_discount_percentage = percent
	elif booking_total and booking_discount:
		po_share = flt(po.net_total) / booking_total if booking_total else 0
		po.discount_amount = booking_discount * po_share

	if hasattr(po, "calculate_taxes_and_totals"):
		po.calculate_taxes_and_totals()


def apply_booking_discount_to_pi(pi, booking):
	"""Apply booking discount to PI — percentage globally, amount split by supplier share."""
	booking_total = flt(booking.get("total_amount"))
	percent = flt(booking.get("additional_discount_percentage"))
	booking_discount = get_booking_effective_discount(booking)

	pi.apply_discount_on = "Net Total"
	pi.additional_discount_percentage = 0
	pi.discount_amount = 0

	if percent > 0:
		pi.additional_discount_percentage = percent
	elif booking_total and booking_discount:
		pi_share = flt(pi.net_total) / booking_total if booking_total else 0
		pi.discount_amount = booking_discount * pi_share

	if hasattr(pi, "calculate_taxes_and_totals"):
		pi.calculate_taxes_and_totals()
