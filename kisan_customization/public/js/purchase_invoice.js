frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		if (frm.is_new()) return;

		const total = get_existing_deduction_total(frm);
		const currency = frm.doc.currency || frappe.defaults.get_global_default("currency");
		const label =
			total > 0 ? __("Deductions") + ` (${format_currency(total, currency)})` : __("Deductions");

		frm.add_custom_button(label, () => open_deductions_dialog(frm));
	},

	custom_total_bags(frm) {
		if (!frm.is_new() && frm.doc.custom_total_bags) {
			frappe.show_alert({
				message: __("Total Bags updated. Open Deductions to refresh calculated amounts."),
				indicator: "blue",
			});
		}
	},
});

const AUTO_CALC_MODES = new Set(["formula", "direct"]);

function get_existing_deduction_total(frm) {
	return (frm.doc.taxes || [])
		.filter((t) => t.add_deduct_tax === "Deduct" && flt(t.tax_amount) > 0)
		.reduce((sum, t) => sum + flt(t.tax_amount), 0);
}

function open_deductions_dialog(frm) {
	if (!flt(frm.doc.custom_total_bags) && frm.doc.items?.length) {
		frappe.msgprint({
			title: __("Total Bags"),
			message: __("Please enter Total Bags on Purchase Invoice before opening deductions."),
			indicator: "orange",
		});
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
				<strong>${__("Qty Deducation")}:</strong> ${__("Actual − Required → calculated amount")} &nbsp;|&nbsp;
				<strong>${__("Calculation")}:</strong> ${__("Formula from Deduction Type (e.g. total_bags * charges_per_unit)")} &nbsp;|&nbsp;
				<strong>${__("Direct")}:</strong> ${__("Charges per Unit when no formula")} &nbsp;|&nbsp;
				<strong>${__("Manual")}:</strong> ${__("Enter amount when no formula and no charges")}
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
	return `
		<div class="kd-row ${active} kd-row-qty" data-search="${search_key}" data-row='${data}'>
			<div class="kd-badge b${idx % 9}">${frappe.utils.escape_html(abbr)}</div>
			<div class="kd-info">
				<p class="kd-name">${frappe.utils.escape_html(row.deduction_type_name)}</p>
				<p class="kd-acct">${frappe.utils.escape_html(row.related_account || "")}</p>
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
		},
		callback(r) {
			if (!r.message) return;
			$row.find(".deduction-required").val(r.message.required_value);
			$row.find(".deduction-diff").val(r.message.difference);
			$row.find(".deduction-amount").val(format_currency(r.message.amount, currency));
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
