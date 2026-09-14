# Copyright (c) 2026, Hidayatali and contributors

import json
from pathlib import Path

DEDUCTION_TYPE_NAMES = [
	"Moise",
	"Damage",
	"S/S",
	"PP",
	"Others",
	"UNLOADING",
	"Miscellaneous",
	"Weighbridge",
	"RTGS",
	"Bag Deduction",
	"Weight Deduction",
]


def get_default_deduction_types():
	fixture_path = (
		Path(__file__).resolve().parent.parent / "install" / "deduction_type_defaults.json"
	)
	with fixture_path.open(encoding="utf-8") as handle:
		records = json.load(handle)

	_validate_deduction_type_fixture(records)

	return [
		{key: value for key, value in record.items() if key not in ("doctype", "name")}
		for record in records
	]


def _validate_deduction_type_fixture(records):
	names_from_json = [record.get("deduction_type_name") for record in records]
	expected = sorted(DEDUCTION_TYPE_NAMES)
	actual = sorted(name for name in names_from_json if name)

	if actual != expected:
		missing = set(expected) - set(actual)
		extra = set(actual) - set(expected)
		raise ValueError(
			"install/deduction_type_defaults.json does not match fixtures/deduction_types.py "
			f"DEDUCTION_TYPE_NAMES. Missing: {sorted(missing)}. Extra: {sorted(extra)}."
		)

	for record in records:
		if record.get("name") and record.get("name") != record.get("deduction_type_name"):
			raise ValueError(
				f"Deduction Type fixture name must match deduction_type_name: {record.get('name')!r}"
			)
