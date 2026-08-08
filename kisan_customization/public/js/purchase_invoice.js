kisan_customization.broker_commission.bind("Purchase Invoice");

frappe.ui.form.on("Purchase Invoice", {
	onload(frm) {
		load_bag_type_options(frm);
		if (frm.is_new() && !frm.doc.custom_bag_details?.length) {
			load_default_bag_rows(frm);
		}
	},

	refresh(frm) {
		load_bag_type_options(frm);

		if (!frm.is_new()) {
			add_broker_commission_button(frm);
		}

		if (frm.is_new()) return;
		if (!can_show_deduction_button(frm)) return;

		const total = get_existing_deduction_total(frm);
		const currency = frm.doc.currency || frappe.defaults.get_global_default("currency");
		const label =
			total > 0 ? __("Deductions") + ` (${format_currency(total, currency)})` : __("Deductions");

		frm.add_custom_button(label, () => open_deductions_dialog(frm));
	},

	custom_total_bags(frm) {
		recalculate_all_bag_rows(frm);
	},

	custom_total_gross_weight(frm) {
		recalculate_all_bag_rows(frm);
	},

	items_add(frm) {
		recalculate_all_bag_rows(frm);
	},

	items_remove(frm) {
		recalculate_all_bag_rows(frm);
	},

	validate(frm) {
		const total_bags = flt(frm.doc.custom_total_bags);
		const child_sum = get_child_bag_sum(frm);

		if (!total_bags || !child_sum) return;

		if (child_sum !== total_bags) {
			frappe.throw(
				__("Sum of No. of Bags ({0}) must equal Total Bags ({1}).", [child_sum, total_bags])
			);
		}
	},
});

frappe.ui.form.on("Purchase Invoice Item", {
	rate(frm) {
		recalculate_all_bag_rows(frm);
	},
});

frappe.ui.form.on("Purchase Invoice Bag Detail", {
	bag_type(frm, cdt, cdn) {
		set_bag_charges_from_master(frm, cdt, cdn);
	},

	no_of_bags(frm, cdt, cdn) {
		if (!flt(frm.doc.custom_total_bags)) {
			frappe.msgprint({
				title: __("Total Bags Required"),
				message: __("Please enter Total Bags first, then enter No. of Bags in Bag Details."),
				indicator: "orange",
			});
			frappe.model.set_value(cdt, cdn, "no_of_bags", 0);
			return;
		}

		if (!validate_bag_count(frm, cdt, cdn)) return;

		calculate_bag_row(frm, cdt, cdn);
	},

	custom_bag_details_remove(frm) {
		recalculate_all_bag_rows(frm);
	},
});

function add_broker_commission_button(frm) {
	if (frm.doc.docstatus !== 1 || !frm.doc.custom_broker) return;

	frappe.db.get_value(
		"Broker Commission",
		{ purchase_invoice: frm.doc.name, docstatus: 1 },
		"name",
		(r) => {
			if (!r?.name) return;
			frm.add_custom_button(__("Broker Commission"), () => {
				frappe.set_route("Form", "Broker Commission", r.name);
			});
		}
	);
}

function can_show_deduction_button(frm) {
	const total_bags = flt(frm.doc.custom_total_bags);
	const child_sum = get_child_bag_sum(frm);
	return (
		total_bags > 0 &&
		flt(frm.doc.custom_total_gross_weight) > 0 &&
		child_sum === total_bags
	);
}

function get_child_bag_sum(frm) {
	return (frm.doc.custom_bag_details || []).reduce((sum, row) => sum + flt(row.no_of_bags), 0);
}

function validate_bag_count(frm, cdt, cdn) {
	const total_bags = flt(frm.doc.custom_total_bags);
	if (!total_bags) return true;

	let child_sum = get_child_bag_sum(frm);

	if (cdt && cdn) {
		const current = flt(locals[cdt][cdn].no_of_bags);
		const saved = flt((frm.doc.custom_bag_details || []).find((r) => r.name === cdn)?.no_of_bags);
		child_sum = child_sum - saved + current;
	}

	if (child_sum > total_bags) {
		frappe.msgprint({
			title: __("Bag Count Exceeded"),
			message: __("Sum of No. of Bags ({0}) cannot be greater than Total Bags ({1}).", [
				child_sum,
				total_bags,
			]),
			indicator: "red",
		});
		if (cdt && cdn) frappe.model.set_value(cdt, cdn, "no_of_bags", 0);
		return false;
	}

	if (child_sum < total_bags && cdt && cdn) {
		frappe.show_alert({
			message: __("Remaining bags to assign: {0}", [total_bags - child_sum]),
			indicator: "orange",
		});
	}

	return true;
}

function calculate_bag_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const total_bags = flt(frm.doc.custom_total_bags);
	const total_gross = flt(frm.doc.custom_total_gross_weight);
	const average_weight = total_bags ? total_gross / total_bags : 0;

	const bags = flt(row.no_of_bags);
	const deduct = bags * flt(row.charges);
	const gross = bags * average_weight;
	const arrival = Math.max(0, gross - deduct);

	frappe.model.set_value(cdt, cdn, "deduct_weight_kg", deduct);
	frappe.model.set_value(cdt, cdn, "gross_weight_kg", gross);
	frappe.model.set_value(cdt, cdn, "arrival_qty_kg", arrival).then(() => {
		update_arrival_total(frm);
	});
}

function recalculate_all_bag_rows(frm) {
	(frm.doc.custom_bag_details || []).forEach((row) => {
		calculate_bag_row(frm, row.doctype, row.name);
	});
	update_arrival_total(frm);
}

function update_arrival_total(frm) {
	const total_arrival = (frm.doc.custom_bag_details || []).reduce(
		(sum, row) => sum + flt(row.arrival_qty_kg),
		0
	);
	frm.set_value("custom_total_arrival_weight", total_arrival);
}

function load_bag_type_options(frm) {
	frappe.call({
		method: "kisan_customization.purchase_invoice.bags.get_bag_type_options",
		callback(r) {
			if (!r.message?.length) return;

			const options = r.message.map((row) => row.bag_type).join("\n");
			if (frm.fields_dict.custom_bag_details?.grid) {
				frm.fields_dict.custom_bag_details.grid.update_docfield_property(
					"bag_type",
					"options",
					options
				);
			}
		},
	});
}

function load_default_bag_rows(frm) {
	frappe.call({
		method: "kisan_customization.purchase_invoice.bags.get_bag_type_options",
		callback(r) {
			if (!r.message?.length) return;

			r.message.forEach((bag) => {
				const row = frm.add_child("custom_bag_details");
				row.bag_type = bag.bag_type;
				row.charges = bag.charges;
			});
			frm.refresh_field("custom_bag_details");
		},
	});
}

function set_bag_charges_from_master(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.bag_type) return;

	frappe.call({
		method: "kisan_customization.purchase_invoice.bags.get_bag_charges",
		args: { bag_type: row.bag_type },
		callback(r) {
			frappe.model.set_value(cdt, cdn, "charges", flt(r.message));
			calculate_bag_row(frm, cdt, cdn);
		},
	});
}


const AUTO_CALC_MODES = new Set(["formula", "direct"]);

function get_existing_deduction_total(frm) {
	return (frm.doc.taxes || [])
		.filter((t) => t.add_deduct_tax === "Deduct" && flt(t.tax_amount) > 0)
		.reduce((sum, t) => sum + flt(t.tax_amount), 0);
}

function open_deductions_dialog(frm) {
	if (!can_show_deduction_button(frm)) {
		const total_bags = flt(frm.doc.custom_total_bags);
		const child_sum = get_child_bag_sum(frm);
		let message = __("Please enter Total Bags and Total Gross Weight, and distribute all bags in Bag Details.");

		if (total_bags && child_sum !== total_bags) {
			message = __("Sum of No. of Bags ({0}) must equal Total Bags ({1}).", [child_sum, total_bags]);
		}

		frappe.msgprint({
			title: __("Bag & Weight Required"),
			message,
			indicator: "orange",
		});
		return;
	}

	frappe.call({
		method: "kisan_customization.purchase_invoice.deductions.get_deduction_data",
		args: { purchase_invoice: frm.doc.name },
		freeze: true,
		callback(r) {
			if (!r.message?.length) {
				frappe.msgprint(__("No active Deduction Types found for this company."));
				return;
			}
			show_deductions_dialog(frm, r.message);
		},
	});
}

function show_deductions_dialog(frm, deductions) {
	const currency = frm.doc.currency || frappe.defaults.get_default("currency");

	const dialog = new frappe.ui.Dialog({
		title: __("Purchase Deductions"),
		size: "extra-large",
		fields: [],
		primary_action_label: __("Apply Deductions"),
		primary_action() {
			apply_deductions(dialog, frm);
		},
	});

	dialog.$wrapper.addClass("kisan-deduction-dialog");
	dialog.$body.addClass("kisan-deduction-body").html(build_deductions_html(deductions, frm, currency));

	dialog.$wrapper.on("shown.bs.modal", () => {
		dialog._frm = frm;
		bind_deduction_events(dialog, frm, currency);
		update_deduction_summary(dialog, currency);
	});

	dialog.show();
}

function build_deductions_html(deductions, frm, currency) {
	const netAmount = flt(deductions[0]?.net_amount);
	const totalBags = flt(frm.doc.custom_total_bags || deductions[0]?.total_bags);
	const totalGrossWeight = flt(frm.doc.custom_total_gross_weight || deductions[0]?.total_gross_weight);

	return `
		<style>${get_deduction_styles()}</style>
		<div class="kd-wrap">
			<div class="kd-header">
				<div class="kd-header-row">
					<div>
						<p class="kd-title">${__("Deduction Entry")}</p>
						<p class="kd-sub">${frappe.utils.escape_html(frm.doc.name)} &bull; ${frappe.utils.escape_html(frm.doc.supplier_name || frm.doc.supplier || "")}</p>
					</div>
					<div class="kd-total-box">
						<div class="kd-total-lbl">${__("Total Deduction")}</div>
						<div class="kd-total-amt" id="kd-total">${format_currency(0, currency)}</div>
					</div>
				</div>
				<div class="kd-stats">
					<div class="kd-stat"><b id="kd-active">0</b>${__("Active")}</div>
					<div class="kd-stat"><b>${deductions.length}</b>${__("Types")}</div>
					<div class="kd-stat"><b>${format_currency(netAmount, currency)}</b>${__("Net Amount")}</div>
					<div class="kd-stat"><b>${totalBags || 0}</b>${__("Total Bags")}</div>
					<div class="kd-stat"><b>${totalGrossWeight || 0}</b>${__("Gross Weight")}</div>
				</div>
			</div>
			<div class="kd-toolbar">
				<div class="kd-search-wrap"><i class="fa fa-search"></i>
					<input class="kd-search" id="kd-search" type="text" placeholder="${__("Search deduction type...")}">
				</div>
				<button type="button" class="kd-clear" id="kd-clear">${__("Clear Manual")}</button>
			</div>
			<div class="kd-list">${build_deduction_rows(deductions, currency)}</div>
			<div class="kd-footer">
				<strong>${__("Damage")}:</strong> ${__("difference × charges × total_gross_weight / 100")} &nbsp;|&nbsp;
				<strong>${__("S/S / Moise")}:</strong> ${__("difference × total_amount / 100")}
			</div>
		</div>`;
}

function build_deduction_rows(deductions, currency) {
	const symbol = typeof get_currency_symbol === "function" ? get_currency_symbol(currency) : currency;

	return deductions
		.map((row, idx) => {
			const abbr = get_deduction_abbr(row.deduction_type_name);
			const active = flt(row.amount) > 0 ? "active" : "";
			const search_key = frappe.utils.escape_html((row.deduction_type_name || "").toLowerCase());
			const data = frappe.utils.escape_html(
				JSON.stringify({
					deduction_type: row.deduction_type,
					qty_deducation: row.qty_deducation ? 1 : 0,
					calculation_mode: row.calculation_mode,
					bag_type: row.bag_type || "",
				})
			);

			if (row.qty_deducation) {
				return build_qty_deducation_row(row, idx, abbr, active, search_key, data, currency);
			}

			if (AUTO_CALC_MODES.has(row.calculation_mode)) {
				return build_auto_calc_row(row, idx, abbr, active, search_key, data, currency);
			}

			return build_manual_row(row, idx, abbr, active, search_key, data, symbol, currency);
		})
		.join("");
}

function build_qty_deducation_row(row, idx, abbr, active, search_key, data, currency) {
	const formula = row.formula
		? `<p class="kd-formula">${frappe.utils.escape_html(row.formula)}</p>`
		: "";

	return `
		<div class="kd-row ${active} kd-row-qty" data-search="${search_key}" data-row='${data}'>
			<div class="kd-badge b${idx % 9}">${frappe.utils.escape_html(abbr)}</div>
			<div class="kd-info">
				<p class="kd-name">${frappe.utils.escape_html(row.deduction_type_name)}</p>
				<p class="kd-acct">${frappe.utils.escape_html(row.related_account || "")}</p>
				${formula}
			</div>
			<div class="kd-qty-fields">
				<div class="kd-field">
					<label>${__("Actual")}</label>
					<input type="number" class="kd-input deduction-actual" value="${flt(row.actual) || ""}" min="0" step="0.01" placeholder="0">
				</div>
				<div class="kd-field kd-readonly">
					<label>${__("Required Value")}</label>
					<input type="text" class="kd-input deduction-required" value="${flt(row.required_value)}" readonly>
				</div>
				<div class="kd-field kd-readonly">
					<label>${__("Difference")}</label>
					<input type="text" class="kd-input deduction-diff" value="${flt(row.difference)}" readonly>
				</div>
				<div class="kd-field kd-readonly kd-amount-field">
					<label>${__("Amount")}</label>
					<input type="text" class="kd-input deduction-amount" value="${format_currency(flt(row.amount), currency)}" readonly>
				</div>
			</div>
		</div>`;
}

function build_auto_calc_row(row, idx, abbr, active, search_key, data, currency) {
	return `
		<div class="kd-row ${active} kd-row-auto" data-search="${search_key}" data-row='${data}' data-amount="${flt(row.amount)}">
			<div class="kd-badge b${idx % 9}">${frappe.utils.escape_html(abbr)}</div>
			<div class="kd-info">
				<p class="kd-name">${frappe.utils.escape_html(row.deduction_type_name)}</p>
				<p class="kd-acct">${frappe.utils.escape_html(row.related_account || "")}</p>
				<p class="kd-formula">${frappe.utils.escape_html(row.formula || "")}</p>
			</div>
			<div class="kd-auto-amount">
				<label>${__("Amount")}</label>
				<div class="kd-auto-value">${format_currency(flt(row.amount), currency)}</div>
			</div>
		</div>`;
}

function build_manual_row(row, idx, abbr, active, search_key, data, symbol, currency) {
	return `
		<div class="kd-row ${active} kd-row-manual" data-search="${search_key}" data-row='${data}'>
			<div class="kd-badge b${idx % 9}">${frappe.utils.escape_html(abbr)}</div>
			<div class="kd-info">
				<p class="kd-name">${frappe.utils.escape_html(row.deduction_type_name)}</p>
				<p class="kd-acct">${frappe.utils.escape_html(row.related_account || "")}</p>
			</div>
			<div class="kd-input-wrap">
				<span class="kd-sym">${frappe.utils.escape_html(symbol)}</span>
				<input type="number" class="kd-input deduction-amount-input" value="${flt(row.amount) || ""}" min="0" step="0.01" placeholder="0.00">
			</div>
		</div>`;
}

function bind_deduction_events(dialog, frm, currency) {
	const $body = dialog.$body;

	$body.on("input", ".deduction-actual", function () {
		recalculate_qty_row($(this).closest(".kd-row"), frm, currency);
		update_deduction_summary(dialog, currency);
	});

	$body.on("input", ".deduction-amount-input", function () {
		const $row = $(this).closest(".kd-row");
		flt($(this).val()) > 0 ? $row.addClass("active") : $row.removeClass("active");
		update_deduction_summary(dialog, currency);
	});

	$body.find("#kd-search").on("input", function () {
		const q = $(this).val().toLowerCase().trim();
		$body.find(".kd-row").each(function () {
			$(this).toggleClass("hide", q && !($(this).attr("data-search") || "").includes(q));
		});
	});

	$body.find("#kd-clear").on("click", function () {
		$body.find(".deduction-actual").val("");
		$body.find(".deduction-amount-input").val("");
		$body.find(".deduction-diff").val("0");
		$body.find(".deduction-amount").val(format_currency(0, currency));
		$body.find(".kd-row-manual, .kd-row-qty").removeClass("active");
		update_deduction_summary(dialog, currency);
	});
}

function recalculate_qty_row($row, frm, currency) {
	const rowData = JSON.parse($row.attr("data-row") || "{}");
	const actual = flt($row.find(".deduction-actual").val());

	frappe.call({
		method: "kisan_customization.purchase_invoice.deductions.calculate_deduction_preview",
		args: {
			purchase_invoice: frm.doc.name,
			deduction_type: rowData.deduction_type,
			actual,
			bag_type: rowData.bag_type || null,
		},
		callback(r) {
			if (!r.message) return;
			$row.find(".deduction-required").val(r.message.required_value);
			$row.find(".deduction-diff").val(r.message.difference);
			$row.find(".deduction-amount").val(format_currency(r.message.amount, currency));
			if (r.message.formula) {
				let $formula = $row.find(".kd-formula");
				if (!$formula.length) {
					$row.find(".kd-info").append(`<p class="kd-formula">${frappe.utils.escape_html(r.message.formula)}</p>`);
				} else {
					$formula.text(r.message.formula);
				}
			}
			r.message.amount > 0 ? $row.addClass("active") : $row.removeClass("active");
		},
	});
}

function get_row_amount($row) {
	if ($row.hasClass("kd-row-auto")) {
		return flt($row.attr("data-amount"));
	}
	if ($row.hasClass("kd-row-qty")) {
		const txt = $row.find(".deduction-amount").val() || "";
		return flt(txt.replace(/[^\d.-]/g, ""));
	}
	return flt($row.find(".deduction-amount-input").val());
}

function update_deduction_summary(dialog, currency) {
	const $body = dialog.$body;
	let total = 0;
	let active = 0;

	$body.find(".kd-row:not(.hide)").each(function () {
		const amount = get_row_amount($(this));
		if (amount > 0) {
			total += amount;
			active++;
		}
	});

	$body.find("#kd-total").text(format_currency(total, currency));
	$body.find("#kd-active").text(active);
}

function apply_deductions(dialog, frm) {
	const deductions = [];

	dialog.$body.find(".kd-row").each(function () {
		const $row = $(this);
		const rowData = JSON.parse($row.attr("data-row") || "{}");

		if (rowData.qty_deducation) {
			deductions.push({
				deduction_type: rowData.deduction_type,
				qty_deducation: 1,
				actual: flt($row.find(".deduction-actual").val()),
				bag_type: rowData.bag_type || "",
			});
		} else if (AUTO_CALC_MODES.has(rowData.calculation_mode)) {
			deductions.push({
				deduction_type: rowData.deduction_type,
				calculation_mode: rowData.calculation_mode,
			});
		} else {
			deductions.push({
				deduction_type: rowData.deduction_type,
				qty_deducation: 0,
				amount: flt($row.find(".deduction-amount-input").val()),
			});
		}
	});

	frappe.call({
		method: "kisan_customization.purchase_invoice.deductions.apply_deductions",
		args: { purchase_invoice: frm.doc.name, deductions: JSON.stringify(deductions) },
		freeze: true,
		freeze_message: __("Applying deductions..."),
		callback(response) {
			if (response.exc) return;
			dialog.hide();
			frm.reload_doc().then(() => {
				frappe.show_alert({ message: __("Deductions applied successfully"), indicator: "green" });
			});
		},
	});
}

function get_deduction_abbr(name) {
	if (!name) return "?";
	const parts = name.trim().split(/[\s\/]+/);
	return parts.length >= 2 ? (parts[0][0] + parts[1][0]).toUpperCase() : name.substring(0, 2).toUpperCase();
}

function get_deduction_styles() {
	return `
		.kisan-deduction-body{padding:0!important;background:#f4f6f8}
		.kd-header{background:linear-gradient(135deg,#14532d,#166534 40%,#22c55e);color:#fff;padding:18px 20px}
		.kd-header-row{display:flex;justify-content:space-between;gap:12px}
		.kd-title{font-size:17px;font-weight:700;margin:0 0 3px}
		.kd-sub{font-size:12px;opacity:.85;margin:0}
		.kd-total-box{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:10px;padding:8px 14px;text-align:right;min-width:130px}
		.kd-total-lbl{font-size:10px;text-transform:uppercase;opacity:.8}
		.kd-total-amt{font-size:20px;font-weight:700}
		.kd-stats{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
		.kd-stat{flex:1;min-width:90px;background:rgba(255,255,255,.12);border-radius:8px;padding:7px 10px;font-size:11px}
		.kd-stat b{display:block;font-size:15px}
		.kd-toolbar{display:flex;gap:8px;padding:10px 14px;background:#fff;border-bottom:1px solid #d1d8dd}
		.kd-search{flex:1;padding:7px 12px 7px 34px;border:1px solid #d1d8dd;border-radius:8px;font-size:13px;outline:none}
		.kd-search-wrap{flex:1;position:relative}.kd-search-wrap .fa{position:absolute;left:11px;top:10px;color:#888}
		.kd-clear{padding:7px 12px;border:1px solid #d1d8dd;border-radius:8px;background:#fff;cursor:pointer;font-size:12px}
		.kd-list{max-height:420px;overflow-y:auto;padding:10px 14px}
		.kd-row{display:flex;align-items:center;gap:10px;background:#fff;border:1.5px solid #d1d8dd;border-radius:10px;padding:10px 12px;margin-bottom:8px}
		.kd-row.active{border-color:#22c55e;background:#f0fdf4}
		.kd-row.hide{display:none}
		.kd-badge{width:36px;height:36px;border-radius:9px;color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;flex-shrink:0}
		.kd-info{flex:1;min-width:0}.kd-name{font-weight:600;margin:0 0 2px}.kd-acct{font-size:11px;color:#6b7280;margin:0}
		.kd-formula{font-size:11px;color:#166534;margin:4px 0 0;font-weight:600}
		.kd-input-wrap{display:flex;border:1.5px solid #d1d8dd;border-radius:8px;overflow:hidden;width:140px;flex-shrink:0;background:#fff}
		.kd-sym{padding:0 8px;background:#f0fdf4;color:#166534;font-weight:700;display:flex;align-items:center;border-right:1px solid #d1d8dd}
		.kd-input{border:none!important;box-shadow:none!important;text-align:right;font-weight:600!important;font-size:13px!important;padding:6px 8px!important;width:100%;outline:none}
		.kd-qty-fields{display:flex;gap:8px;flex-shrink:0;align-items:flex-end}
		.kd-field{display:flex;flex-direction:column;gap:2px}
		.kd-field label{font-size:10px;color:#6b7280;text-transform:uppercase;font-weight:600}
		.kd-field .kd-input{width:80px;border:1.5px solid #d1d8dd!important;border-radius:6px!important;padding:5px 6px!important;text-align:right}
		.kd-readonly .kd-input{background:#f9fafb;color:#374151}
		.kd-amount-field .kd-input{width:100px;font-weight:700!important;color:#166534}
		.kd-auto-amount{text-align:right;flex-shrink:0}
		.kd-auto-amount label{font-size:10px;color:#6b7280;text-transform:uppercase;font-weight:600;display:block;margin-bottom:2px}
		.kd-auto-value{font-size:16px;font-weight:700;color:#166534;min-width:100px}
		.kd-footer{padding:10px 14px;background:#fff;border-top:1px solid #d1d8dd;font-size:11px;color:#6b7280;line-height:1.6}
		.b0{background:linear-gradient(135deg,#14532d,#22c55e)}.b1{background:linear-gradient(135deg,#7f1d1d,#ef4444)}
		.b2{background:linear-gradient(135deg,#1e3a8a,#3b82f6)}.b3{background:linear-gradient(135deg,#78350f,#f59e0b)}
		.b4{background:linear-gradient(135deg,#581c87,#a855f7)}.b5{background:linear-gradient(135deg,#134e4a,#14b8a6)}
		.b6{background:linear-gradient(135deg,#44403c,#78716c)}.b7{background:linear-gradient(135deg,#881337,#f43f5e)}
		.b8{background:linear-gradient(135deg,#312e81,#6366f1)}`;
}
