# Copyright (c) 2026, Hidayatali and contributors

import shutil
from pathlib import Path

import frappe

KISAN_LOGO_FILE_URL = "/files/kisan_logo.jpeg"
KISAN_LOGO_FILENAME = "kisan_logo.jpeg"


def ensure_kisan_settlement_logo():
	"""Copy bundled logo to site public/files so /files/kisan_logo.jpeg works on every site."""
	public_file = Path(frappe.get_site_path("public", "files", KISAN_LOGO_FILENAME))
	if public_file.is_file():
		return

	source = Path(frappe.get_app_path("kisan_customization", "public", "images", KISAN_LOGO_FILENAME))
	if not source.is_file():
		return

	public_file.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(source, public_file)

	if frappe.db.exists("File", {"file_url": KISAN_LOGO_FILE_URL, "is_folder": 0}):
		return

	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": KISAN_LOGO_FILENAME,
			"file_url": KISAN_LOGO_FILE_URL,
			"is_private": 0,
		}
	).insert(ignore_permissions=True)
