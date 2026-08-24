kisan_customization.delivery_payment_days.bind("Purchase Order");
kisan_customization.broker_commission.bind("Purchase Order");

const PO_SUPPLIER_GROUP = "Purchase";
const PO_ITEM_GROUP = "Products";

const HIDDEN_PO_CREATE_BUTTONS = [__("Purchase Receipt"), __("Payment Request")];

function apply_purchase_order_filters(frm) {
	frm.set_query("supplier", () => ({
		filters: {
			supplier_group: PO_SUPPLIER_GROUP,
			disabled: 0,
		},
	}));

	frm.set_query("item_code", "items", () => {
		const filters = {
			item_group: PO_ITEM_GROUP,
			is_purchase_item: 1,
			has_variants: 0,
		};
		return {
			query: "erpnext.controllers.queries.item_query",
			filters,
		};
	});
}

function hide_purchase_order_create_options(frm) {
	HIDDEN_PO_CREATE_BUTTONS.forEach((label) => {
		frm.remove_custom_button(label, __("Create"));
	});
}

function patch_purchase_order_controller() {
	const POController = erpnext.buying?.PurchaseOrderController;
	if (!POController || POController.prototype.__kisan_hide_create_patched) {
		return;
	}

	const original_refresh = POController.prototype.refresh;

	POController.prototype.refresh = function (...args) {
		const result = original_refresh.apply(this, args);
		hide_purchase_order_create_options(this.frm);
		return result;
	};

	POController.prototype.__kisan_hide_create_patched = true;
}

patch_purchase_order_controller();

frappe.ui.form.on("Purchase Order", {
	setup() {
		patch_purchase_order_controller();
	},

	onload(frm) {
		apply_purchase_order_filters(frm);
	},

	supplier(frm) {
		apply_purchase_order_filters(frm);
	},

	refresh(frm) {
		// ERPNext buying controller resets queries on load/refresh — re-apply after it runs.
		setTimeout(() => apply_purchase_order_filters(frm));
	},
});
