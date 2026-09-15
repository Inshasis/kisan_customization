# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.broker_commission.service import (
	cancel_broker_commission_on_cancel,
	create_broker_commission_on_submit,
)
from kisan_customization.utils.transaction_mode import is_kisan_custom


def on_submit(doc, method=None):
	if not is_kisan_custom(doc):
		return

	create_broker_commission_on_submit(doc)


def before_cancel(doc, method=None):
	cancel_broker_commission_on_cancel(doc)
