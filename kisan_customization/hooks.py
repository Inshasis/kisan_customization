app_name = "kisan_customization"
app_title = "Kisan Customization"
app_publisher = "Hidayatali"
app_description = "Kisan Customization - Trading Idustry"
app_email = "sales@wirerr.com"
app_license = "mit"

required_apps = ["erpnext"]

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Purchase Invoice-custom_bag_details_section",
					"Purchase Invoice-custom_bag_details",
					"Purchase Invoice-custom_weight_info_section",
					"Purchase Invoice-custom_total_bags",
					"Purchase Invoice-custom_total_gross_weight",
					"Purchase Invoice-custom_total_arrival_weight",
					"Purchase Invoice-custom_weight_deduction",
					"Purchase Invoice-custom_bag_deduction",
					"Purchase Invoice-custom_bag_deduction_amount",
					"Purchase Invoice-custom_weight_deduction_amount",
					"Purchase Invoice-custom_deductions_section",
					"Purchase Invoice-custom_deductions",
					"Purchase Invoice-custom_section_break_lqipi",
					"Purchase Invoice-custom_broker",
					"Purchase Invoice-custom_column_break_1ked0",
					"Purchase Invoice-custom_commission_type",
					"Purchase Invoice-custom_commission_percent",
					"Purchase Invoice-custom_commission_amount",
					"Purchase Invoice-custom_broker_commission_amount",
					"Purchase Invoice-custom_payment_days",
					"Purchase Invoice-custom_supplier_invoice_amount",
					"Purchase Order-custom_section_break_lqipi",
					"Purchase Order-custom_broker",
					"Purchase Order-custom_column_break_1ked0",
					"Purchase Order-custom_commission_type",
					"Purchase Order-custom_column_break_y5zpm",
					"Purchase Order-custom_commission_percent",
					"Purchase Order-custom_commission_amount",
					"Purchase Order-custom_broker_commission_amount",
					"Purchase Order-custom_delivery_days",
					"Purchase Order-custom_payment_days",
					"Sales Order-custom_section_break_lqipi",
					"Sales Order-custom_broker",
					"Sales Order-custom_column_break_1ked0",
					"Sales Order-custom_commission_type",
					"Sales Order-custom_column_break_y5zpm",
					"Sales Order-custom_commission_percent",
					"Sales Order-custom_commission_amount",
					"Sales Order-custom_broker_commission_amount",
					"Sales Order-custom_delivery_days",
					"Sales Order-custom_payment_days",
					"Sales Invoice-custom_delivery_days",
					"Sales Invoice-custom_payment_days",
					"Sales Invoice-custom_delivery_date",
					"Sales Invoice-custom_section_break_lqipi",
					"Sales Invoice-custom_broker",
					"Sales Invoice-custom_column_break_1ked0",
					"Sales Invoice-custom_commission_type",
					"Sales Invoice-custom_column_break_y5zpm",
					"Sales Invoice-custom_commission_percent",
					"Sales Invoice-custom_commission_amount",
					"Sales Invoice-custom_broker_commission_amount",
				],
			]
		],
	},
    {"dt": "Item Group", "filters": [
		[
			"name",
		"in",
		{
			"Cold Storage Item"
		}]
	]},
	{"dt": "Customer Group", "filters": [
		[
			"name",
		"in",
		{
			"Cold Storage Customer"
		}]
	]},
    {"dt": "Supplier Group", "filters": [
		[
			"name",
		"in",
		{
			"Aggregator",
            "Broker"
		}]
	]},
]

# bench --site kisan_custom export-fixtures --app kisan_customization

# Apps
# ------------------

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "kisan_customization",
# 		"logo": "/assets/kisan_customization/logo.png",
# 		"title": "Kisan Customization",
# 		"route": "/kisan_customization",
# 		"has_permission": "kisan_customization.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kisan_customization/css/kisan_customization.css"
# app_include_js = "/assets/kisan_customization/js/kisan_customization.js"

# include js, css files in header of web template
# web_include_css = "/assets/kisan_customization/css/kisan_customization.css"
# web_include_js = "/assets/kisan_customization/js/kisan_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kisan_customization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Purchase Invoice": [
		"public/js/broker_commission.js",
		"public/js/delivery_payment_days.js",
		"public/js/purchase_invoice.js",
	],
	"Purchase Order": [
		"public/js/delivery_payment_days.js",
		"public/js/broker_commission.js",
		"public/js/purchase_order.js",
	],
	"Sales Order": [
		"public/js/delivery_payment_days.js",
		"public/js/broker_commission.js",
		"public/js/sales_order.js",
	],
	"Sales Invoice": [
		"public/js/broker_commission.js",
		"public/js/delivery_payment_days.js",
		"public/js/sales_invoice.js",
	],
}
doctype_list_js = {
	"Purchase Order": "public/js/purchase_order_list.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "kisan_customization/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "kisan_customization.utils.jinja_methods",
# 	"filters": "kisan_customization.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "kisan_customization.install.before_install"
after_install = "kisan_customization.install.after_install.after_install"

# Uninstallation
# ------------

# before_uninstall = "kisan_customization.uninstall.before_uninstall"
# after_uninstall = "kisan_customization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "kisan_customization.utils.before_app_install"
# after_app_install = "kisan_customization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "kisan_customization.utils.before_app_uninstall"
# after_app_uninstall = "kisan_customization.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kisan_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Invoice": {
		"validate": [
			"kisan_customization.purchase_invoice.purchase_invoice.validate",
			"kisan_customization.purchase_invoice.broker_commission.validate",
		],
		"before_submit": "kisan_customization.purchase_invoice.broker_commission.before_submit",
		"before_cancel": "kisan_customization.purchase_invoice.broker_commission.before_cancel",
		"on_submit": "kisan_customization.purchase_invoice.broker_commission.on_submit",
		"on_trash": "kisan_customization.purchase_invoice.aggregator_booking.on_trash",
	},
	"Purchase Order": {
		"validate": "kisan_customization.purchase_order.broker_commission.validate",
		"before_submit": "kisan_customization.purchase_order.broker_commission.before_submit",
	},
	"Sales Order": {
		"validate": "kisan_customization.sales_order.broker_commission.validate",
		"before_submit": "kisan_customization.sales_order.broker_commission.before_submit",
	},
	"Sales Invoice": {
		"validate": "kisan_customization.sales_invoice.sales_invoice.validate",
		"before_cancel": "kisan_customization.sales_invoice.broker_commission.before_cancel",
		"on_submit": [
			"kisan_customization.sales_invoice.broker_commission.on_submit",
			"kisan_customization.outward_jawak.status.on_sales_invoice_update",
		],
		"on_cancel": "kisan_customization.outward_jawak.status.on_sales_invoice_update",
		"on_update_after_submit": "kisan_customization.outward_jawak.status.on_sales_invoice_update",
	},
	"Payment Entry": {
		"on_submit": "kisan_customization.outward_jawak.status.update_jawak_from_payment_entry",
		"on_cancel": "kisan_customization.outward_jawak.status.update_jawak_from_payment_entry",
	},
}

# Broker Commission is cancelled programmatically on invoice cancel (before_cancel hook).
auto_cancel_exempted_doctypes = ["Broker Commission"]

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"kisan_customization.tasks.all"
# 	],
# 	"daily": [
# 		"kisan_customization.tasks.daily"
# 	],
# 	"hourly": [
# 		"kisan_customization.tasks.hourly"
# 	],
# 	"weekly": [
# 		"kisan_customization.tasks.weekly"
# 	],
# 	"monthly": [
# 		"kisan_customization.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "kisan_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice": (
		"kisan_customization.purchase_order.purchase_order.make_purchase_invoice"
	),
	"erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice": (
		"kisan_customization.sales_invoice.sales_order.make_sales_invoice"
	),
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "kisan_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = ["Aggregator Booking"]

# Request Events
# ----------------
# before_request = ["kisan_customization.utils.before_request"]
# after_request = ["kisan_customization.utils.after_request"]

# Job Events
# ----------
# before_job = ["kisan_customization.utils.before_job"]
# after_job = ["kisan_customization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"kisan_customization.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

