# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.purchase_invoice.bags import (
	recalculate_bag_weights,
	sync_arrival_qty_to_items,
	validate_bag_details,
)
from kisan_customization.purchase_invoice.deductions import recalculate_existing_deductions
from kisan_customization.purchase_invoice.payment_terms import (
	apply_payment_days_to_invoice,
	sync_payment_terms_from_linked_po,
)


def validate(doc, method=None):
	validate_bag_details(doc)
	recalculate_bag_weights(doc)
	sync_arrival_qty_to_items(doc)
	recalculate_existing_deductions(doc)
	sync_payment_terms_from_linked_po(doc)
	apply_payment_days_to_invoice(doc)
