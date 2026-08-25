# Copyright (c) 2026, Hidayatali and contributors

import json
from pathlib import Path

DEDUCTION_TYPE_NAMES = [
	"Moise",
	"Damage",
	"S/S",
	"PP",
	"UNLOADING",
	"Others",
	"Weighbridge",
	"RTGS",
	"Miscellaneous",
	"Weight Deduction",
]


def get_default_deduction_types():
	fixture_path = Path(__file__).resolve().parent / "deduction_type_defaults.json"
	with fixture_path.open(encoding="utf-8") as handle:
		records = json.load(handle)

	return [
		{key: value for key, value in record.items() if key not in ("doctype", "name")}
		for record in records
	]
