frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		const total = get_existing_deduction_total(frm);
		const currency = frm.doc.currency || frappe.defaults.get_global_default("currency");
		const label =
			total > 0
				? __("Deductions") + ` (${format_currency(total, currency)})`
				: __("Deductions");

		frm.add_custom_button(label, () => open_deductions_dialog(frm));
	},
});

function get_existing_deduction_total(frm) {
	return (frm.doc.taxes || [])
		.filter((t) => t.add_deduct_tax === "Deduct" && flt(t.tax_amount) > 0)
		.reduce((sum, t) => sum + flt(t.tax_amount), 0);
}

function open_deductions_dialog(frm) {
	frappe.call({
		method: "kisan_customization.purchase_invoice.deductions.get_deduction_data",
		args: { purchase_invoice: frm.doc.name },
		freeze: true,
		callback(r) {
			if (!r.message || !r.message.length) {
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
		size: "large",
		fields: [],
		primary_action_label: __("Apply Deductions"),
		primary_action() {
			apply_deductions(dialog, frm);
		},
	});

	dialog.$wrapper.addClass("kisan-deduction-dialog");
	dialog.$body.addClass("kisan-deduction-body").html(build_deductions_html(deductions, frm, currency));

	dialog.$wrapper.on("shown.bs.modal", function () {
		bind_deduction_events(dialog, currency);
		update_deduction_summary(dialog, currency);
		dialog.$body.find(".deduction-amount").first().focus();
	});

	dialog.show();
}

function build_deductions_html(deductions, frm, currency) {
	const symbol = typeof get_currency_symbol === "function" ? get_currency_symbol(currency) : currency;

	return `
		<style>
			.kisan-deduction-body { padding: 0 !important; background: #f4f6f8; }
			.kd-wrap { font-size: 13px; }
			.kd-header {
				background: linear-gradient(135deg, #14532d 0%, #166534 40%, #22c55e 100%);
				color: #fff; padding: 18px 20px;
			}
			.kd-header-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
			.kd-title { font-size: 17px; font-weight: 700; margin: 0 0 3px; }
			.kd-sub { font-size: 12px; opacity: .85; margin: 0; }
			.kd-total-box {
				background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
				border-radius: 10px; padding: 8px 14px; text-align: right; min-width: 120px;
			}
			.kd-total-lbl { font-size: 10px; text-transform: uppercase; opacity: .8; }
			.kd-total-amt { font-size: 20px; font-weight: 700; }
			.kd-stats { display: flex; gap: 8px; margin-top: 12px; }
			.kd-stat {
				flex: 1; background: rgba(255,255,255,.12); border-radius: 8px;
				padding: 7px 10px; font-size: 11px;
			}
			.kd-stat b { display: block; font-size: 15px; }
			.kd-toolbar {
				display: flex; gap: 8px; padding: 10px 14px;
				background: #fff; border-bottom: 1px solid #d1d8dd;
			}
			.kd-search {
				flex: 1; padding: 7px 12px 7px 34px; border: 1px solid #d1d8dd;
				border-radius: 8px; font-size: 13px; outline: none;
			}
			.kd-search-wrap { flex: 1; position: relative; }
			.kd-search-wrap .fa { position: absolute; left: 11px; top: 10px; color: #888; }
			.kd-clear {
				padding: 7px 12px; border: 1px solid #d1d8dd; border-radius: 8px;
				background: #fff; cursor: pointer; font-size: 12px; white-space: nowrap;
			}
			.kd-clear:hover { border-color: #e74c3c; color: #e74c3c; }
			.kd-list { max-height: 360px; overflow-y: auto; padding: 10px 14px; }
			.kd-row {
				display: flex; align-items: center; gap: 10px;
				background: #fff; border: 1.5px solid #d1d8dd; border-radius: 10px;
				padding: 10px 12px; margin-bottom: 8px; transition: all .15s;
			}
			.kd-row:hover { border-color: #86efac; box-shadow: 0 2px 8px rgba(0,0,0,.06); }
			.kd-row.active { border-color: #22c55e; background: #f0fdf4; }
			.kd-row.hide { display: none; }
			.kd-badge {
				width: 36px; height: 36px; border-radius: 9px; color: #fff;
				display: flex; align-items: center; justify-content: center;
				font-size: 11px; font-weight: 800; flex-shrink: 0;
			}
			.kd-info { flex: 1; min-width: 0; }
			.kd-name { font-weight: 600; margin: 0 0 2px; color: #1f2937; }
			.kd-acct { font-size: 11px; color: #6b7280; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.kd-input-wrap {
				display: flex; border: 1.5px solid #d1d8dd; border-radius: 8px;
				overflow: hidden; width: 140px; flex-shrink: 0; background: #fff;
			}
			.kd-row.active .kd-input-wrap { border-color: #22c55e; }
			.kd-sym {
				padding: 0 8px; background: #f0fdf4; color: #166534; font-weight: 700;
				display: flex; align-items: center; border-right: 1px solid #d1d8dd; font-size: 13px;
			}
			.kd-input {
				border: none !important; box-shadow: none !important; text-align: right;
				font-weight: 600 !important; font-size: 14px !important;
				padding: 6px 8px !important; width: 100%; outline: none;
			}
			.kd-footer {
				padding: 10px 14px; background: #fff; border-top: 1px solid #d1d8dd;
				font-size: 11px; color: #6b7280;
			}
			.kd-footer strong { color: #166534; }
			.b0{background:linear-gradient(135deg,#14532d,#22c55e)}
			.b1{background:linear-gradient(135deg,#7f1d1d,#ef4444)}
			.b2{background:linear-gradient(135deg,#1e3a8a,#3b82f6)}
			.b3{background:linear-gradient(135deg,#78350f,#f59e0b)}
			.b4{background:linear-gradient(135deg,#581c87,#a855f7)}
			.b5{background:linear-gradient(135deg,#134e4a,#14b8a6)}
			.b6{background:linear-gradient(135deg,#44403c,#78716c)}
			.b7{background:linear-gradient(135deg,#881337,#f43f5e)}
			.b8{background:linear-gradient(135deg,#312e81,#6366f1)}
		</style>

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
					<div class="kd-stat"><b id="kd-skipped">${deductions.length}</b>${__("Skipped")}</div>
				</div>
			</div>

			<div class="kd-toolbar">
				<div class="kd-search-wrap">
					<i class="fa fa-search"></i>
					<input class="kd-search" id="kd-search" type="text" placeholder="${__("Search deduction type...")}">
				</div>
				<button type="button" class="kd-clear" id="kd-clear">${__("Clear All")}</button>
			</div>

			<div class="kd-list">
				${build_deduction_rows(deductions, symbol)}
			</div>

			<div class="kd-footer">
				${__("Only")} <strong>${__("non-zero")}</strong> ${__("amounts added to Purchase Taxes & Charges as")} <strong>${__("Deduct")}</strong>
			</div>
		</div>
	`;
}

function build_deduction_rows(deductions, symbol) {
	return deductions
		.map((row, idx) => {
			const amount = flt(row.amount);
			const abbr = get_deduction_abbr(row.deduction_type_name);
			const active = amount > 0 ? "active" : "";
			const search_key = frappe.utils.escape_html(
				(row.deduction_type_name || "").toLowerCase()
			);

			return `
			<div class="kd-row ${active}" data-search="${search_key}">
				<div class="kd-badge b${idx % 9}">${frappe.utils.escape_html(abbr)}</div>
				<div class="kd-info">
					<p class="kd-name">${frappe.utils.escape_html(row.deduction_type_name)}</p>
					<p class="kd-acct">${frappe.utils.escape_html(row.related_account || "")}</p>
				</div>
				<div class="kd-input-wrap">
					<span class="kd-sym">${frappe.utils.escape_html(symbol)}</span>
					<input type="number" class="kd-input deduction-amount form-control"
						data-deduction-type="${frappe.utils.escape_html(row.deduction_type)}"
						value="${amount || ""}" min="0" step="0.01" placeholder="0.00">
				</div>
			</div>`;
		})
		.join("");
}

function get_deduction_abbr(name) {
	if (!name) return "?";
	const parts = name.trim().split(/[\s\/]+/);
	if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
	return name.substring(0, 2).toUpperCase();
}

function bind_deduction_events(dialog, currency) {
	const $body = dialog.$body;

	$body.on("input", ".deduction-amount", function () {
		const $row = $(this).closest(".kd-row");
		flt($(this).val()) > 0 ? $row.addClass("active") : $row.removeClass("active");
		update_deduction_summary(dialog, currency);
	});

	$body.on("keydown", ".deduction-amount", function (e) {
		if (e.key === "Enter") {
			e.preventDefault();
			const $inputs = $body.find(".kd-row:not(.hide) .deduction-amount");
			const idx = $inputs.index(this);
			if (idx < $inputs.length - 1) $inputs.eq(idx + 1).focus().select();
		}
	});

	$body.find("#kd-search").on("input", function () {
		const q = $(this).val().toLowerCase().trim();
		$body.find(".kd-row").each(function () {
			const key = $(this).attr("data-search") || "";
			$(this).toggleClass("hide", q && !key.includes(q));
		});
	});

	$body.find("#kd-clear").on("click", function () {
		$body.find(".deduction-amount").val("").closest(".kd-row").removeClass("active");
		update_deduction_summary(dialog, currency);
	});
}

function update_deduction_summary(dialog, currency) {
	const $body = dialog.$body;
	let total = 0;
	let active = 0;
	const count = $body.find(".kd-row").length;

	$body.find(".deduction-amount").each(function () {
		const val = flt($(this).val());
		if (val > 0) {
			total += val;
			active++;
		}
	});

	$body.find("#kd-total").text(format_currency(total, currency));
	$body.find("#kd-active").text(active);
	$body.find("#kd-skipped").text(count - active);
}

function apply_deductions(dialog, frm) {
	const deductions = [];
	dialog.$body.find(".deduction-amount").each(function () {
		deductions.push({
			deduction_type: $(this).attr("data-deduction-type"),
			amount: flt($(this).val()),
		});
	});

	frappe.call({
		method: "kisan_customization.purchase_invoice.deductions.apply_deductions",
		args: {
			purchase_invoice: frm.doc.name,
			deductions: JSON.stringify(deductions),
		},
		freeze: true,
		freeze_message: __("Applying deductions..."),
		callback(response) {
			if (response.exc) return;
			dialog.hide();
			frm.reload_doc().then(() => {
				frappe.show_alert({
					message: __("Deductions applied successfully"),
					indicator: "green",
				});
			});
		},
	});
}
