# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.payment_terms import (
	apply_payment_days_to_invoice,
	sync_payment_terms_from_linked_so,
)
from kisan_customization.utils.transaction_mode import is_kisan_custom


def validate(doc, method=None):
	if not is_kisan_custom(doc):
		return

	sync_payment_terms_from_linked_so(doc)
	apply_payment_days_to_invoice(doc)
