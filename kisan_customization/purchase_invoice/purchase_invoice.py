# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.purchase_invoice.bags import recalculate_bag_weights, validate_bag_details
from kisan_customization.purchase_invoice.deductions import recalculate_existing_deductions


def validate(doc, method=None):
	validate_bag_details(doc)
	recalculate_bag_weights(doc)
	recalculate_existing_deductions(doc)
