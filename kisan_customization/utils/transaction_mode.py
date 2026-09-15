# Copyright (c) 2026, Hidayatali and contributors

MODE_REGULAR = "Regular"
MODE_KISAN = "Kisan Custom"
MODE_FIELD = "custom_kisan_transaction_mode"


def is_kisan_custom(doc):
	if doc.get("is_return"):
		return True

	if not doc.meta.has_field(MODE_FIELD):
		return True

	mode = doc.get(MODE_FIELD)
	if not mode:
		return True

	return mode == MODE_KISAN


def copy_transaction_mode(source, target):
	if not source.meta.has_field(MODE_FIELD) or not target.meta.has_field(MODE_FIELD):
		return

	target.set(MODE_FIELD, source.get(MODE_FIELD))
