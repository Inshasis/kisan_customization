kisan_customization.delivery_payment_days.bind("Sales Order");
kisan_customization.broker_commission.bind("Sales Order");

const SO_CUSTOMER_GROUP = "Sales";
const SO_ITEM_GROUP = "Products";

const HIDDEN_SO_CREATE_BUTTONS = [
	__("Pick List"),
	__("Delivery Note"),
	__("Work Order"),
	__("Material Request"),
	__("Request for Raw Materials"),
	__("Purchase Order"),
	__("Maintenance Visit"),
	__("Maintenance Schedule"),
	__("Project"),
	__("Internal Purchase Order"),
	__("Inter Company Purchase Order"),
	__("Payment Request"),
];

function apply_sales_order_filters(frm) {
	frm.set_query("customer", () => ({
		filters: {
			customer_group: SO_CUSTOMER_GROUP,
			disabled: 0,
		},
	}));

	frm.set_query("item_code", "items", () => {
		const filters = {
			item_group: SO_ITEM_GROUP,
			is_sales_item: 1,
			has_variants: 0,
		};
		return {
			query: "erpnext.controllers.queries.item_query",
			filters,
		};
	});
}

function hide_sales_order_create_options(frm) {
	HIDDEN_SO_CREATE_BUTTONS.forEach((label) => {
		frm.remove_custom_button(label, __("Create"));
	});
}

function patch_sales_order_controller() {
	const SOController = erpnext.selling?.SalesOrderController;
	if (!SOController || SOController.prototype.__kisan_hide_create_patched) {
		return;
	}

	const original_refresh = SOController.prototype.refresh;

	SOController.prototype.refresh = function (...args) {
		const result = original_refresh.apply(this, args);
		hide_sales_order_create_options(this.frm);
		return result;
	};

	SOController.prototype.__kisan_hide_create_patched = true;
}

patch_sales_order_controller();

frappe.ui.form.on("Sales Order", {
	setup() {
		patch_sales_order_controller();
	},

	onload(frm) {
		apply_sales_order_filters(frm);
	},

	customer(frm) {
		apply_sales_order_filters(frm);
	},

	refresh(frm) {
		// ERPNext selling controller resets queries on load/refresh — re-apply after it runs.
		setTimeout(() => {
			apply_sales_order_filters(frm);
			hide_sales_order_create_options(frm);
		});
	},
});
