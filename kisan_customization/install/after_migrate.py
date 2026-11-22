# Copyright (c) 2026, Hidayatali and contributors

from kisan_customization.install.deduction_types import ensure_default_deduction_types
from kisan_customization.install.kisan_logo import ensure_kisan_settlement_logo
from kisan_customization.install.master_settings import ensure_master_settings_defaults
from kisan_customization.print_formats.gst_sales_print import apply_print_format as apply_gst_sales_print
from kisan_customization.print_formats.settlement_advice_print import (
	apply_print_format as apply_settlement_print,
)
from kisan_customization.utils.sidebar_hide import generate_sidebar_assets


def after_migrate():
	"""Re-create missing master data after app updates without resetting site configuration."""
	ensure_master_settings_defaults()
	ensure_default_deduction_types()
	ensure_kisan_settlement_logo()
	apply_settlement_print()
	apply_gst_sales_print()
	generate_sidebar_assets()
