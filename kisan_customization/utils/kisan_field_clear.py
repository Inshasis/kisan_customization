# Copyright (c) 2026, Hidayatali and contributors

KISAN_PI_SCALAR_FIELDS = (
	"custom_total_bags",
	"custom_total_gross_weight",
	"custom_total_arrival_weight",
	"custom_weight_deduction",
	"custom_bag_deduction",
	"custom_bag_deduction_amount",
	"custom_weight_deduction_amount",
	"custom_supplier_invoice_amount",
	"custom_broker",
	"custom_commission_type",
	"custom_commission_percent",
	"custom_commission_amount",
	"custom_broker_commission_amount",
	"custom_payment_days",
	"custom_delivery_days",
)


def clear_kisan_purchase_invoice_fields(doc):
	if doc.meta.has_field("custom_bag_details"):
		doc.set("custom_bag_details", [])
	if doc.meta.has_field("custom_deductions"):
		doc.set("custom_deductions", [])

	for fieldname in KISAN_PI_SCALAR_FIELDS:
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, None)

	if doc.meta.has_field("payment_schedule"):
		doc.set("payment_schedule", [])
