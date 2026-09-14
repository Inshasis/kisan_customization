# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.install.deduction_types import ensure_default_deduction_types
from kisan_customization.install.master_settings import ensure_master_settings_defaults


def after_migrate():
	"""Re-create missing master data after app updates without resetting site configuration."""
	ensure_master_settings_defaults()
	ensure_default_deduction_types()
