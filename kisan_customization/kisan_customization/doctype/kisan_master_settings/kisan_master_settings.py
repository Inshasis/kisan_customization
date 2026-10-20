# Copyright (c) 2026, Hidayatali and contributors

from frappe.model.document import Document

from kisan_customization.utils.sidebar_hide import generate_sidebar_assets, validate_hide_sidebar_rules


class KisanMasterSettings(Document):
	def validate(self):
		validate_hide_sidebar_rules(self.get("hide_sidebar_rules"))

	def on_update(self):
		generate_sidebar_assets()
