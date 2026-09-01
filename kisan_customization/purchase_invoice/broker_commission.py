# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.broker_commission.service import (
	cancel_broker_commission_on_cancel,
	clear_broker_commission_fields,
	create_broker_commission_on_submit,
)


def validate(doc, method=None):
	if doc.get("is_return"):
		clear_broker_commission_fields(doc)


def on_submit(doc, method=None):
	create_broker_commission_on_submit(doc)


def before_cancel(doc, method=None):
	cancel_broker_commission_on_cancel(doc)
