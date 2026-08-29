# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.payment_terms import (
	apply_payment_days_to_invoice,
	sync_payment_terms_from_linked_so,
)


def validate(doc, method=None):
	sync_payment_terms_from_linked_so(doc)
	apply_payment_days_to_invoice(doc)
