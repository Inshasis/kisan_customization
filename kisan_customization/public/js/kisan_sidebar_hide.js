frappe.provide("kisan_customization.sidebar_hide");

(function () {
	function rules() {
		const boot = (frappe.boot && frappe.boot.kisan_hide_sidebar_rules) || {};
		return {
			list: boot.list || [],
			details: boot.details || [],
		};
	}

	function hideList(listview) {
		const r = rules();
		if (!listview || r.list.indexOf(listview.doctype) === -1) {
			return;
		}
		const $p = listview.$page || $(listview.parent);
		$p.find(".layout-side-section, .list-sidebar").each(function () {
			this.style.setProperty("display", "none", "important");
		});
		$p.find(".layout-main-section-wrapper").css({ flex: "1 1 auto", "max-width": "100%" });
		$(document.body).addClass("no-list-sidebar");
	}

	function hideForm(frm) {
		const r = rules();
		if (!frm || r.details.indexOf(frm.doctype) === -1) {
			return;
		}
		const $w = frm.page && frm.page.wrapper ? $(frm.page.wrapper) : $(frm.wrapper);
		$w.find(".layout-side-section, .form-sidebar").each(function () {
			this.style.setProperty("display", "none", "important");
		});
	}

	function registerListSettings() {
		rules().list.forEach((doctype) => {
			frappe.listview_settings[doctype] = frappe.listview_settings[doctype] || {};
			const s = frappe.listview_settings[doctype];
			if (s.__kisan_sidebar_hide) {
				return;
			}
			s.__kisan_sidebar_hide = true;
			const prev = s.onload;
			s.onload = function (listview) {
				if (prev) {
					prev.call(this, listview);
				}
				hideList(listview);
			};
		});
	}

	function registerFormHandlers() {
		rules().details.forEach((doctype) => {
			frappe.ui.form.on(doctype, {
				onload(frm) {
					hideForm(frm);
				},
				refresh(frm) {
					hideForm(frm);
				},
			});
		});
	}

	function patchList() {
		if (!frappe.views || !frappe.views.Factory) {
			return;
		}
		if (!frappe.views.Factory.prototype.__kisan_sidebar_hide) {
			frappe.views.Factory.prototype.__kisan_sidebar_hide = true;
			const orig = frappe.views.Factory.prototype.make_page;
			frappe.views.Factory.prototype.make_page = function (dc, name, toggle) {
				const route = this.route || frappe.get_route() || [];
				if (route[0] === "List" && rules().list.indexOf(route[1]) !== -1) {
					return orig.call(this, false, name, true);
				}
				return orig.call(this, dc, name, toggle);
			};
		}
		if (frappe.views.BaseList && !frappe.views.BaseList.prototype.__kisan_sidebar_hide) {
			frappe.views.BaseList.prototype.__kisan_sidebar_hide = true;
			const origBar = frappe.views.BaseList.prototype.setup_side_bar;
			frappe.views.BaseList.prototype.setup_side_bar = function () {
				if (rules().list.indexOf(this.doctype) !== -1) {
					return;
				}
				return origBar.apply(this, arguments);
			};
			const origShow = frappe.views.BaseList.prototype.show;
			frappe.views.BaseList.prototype.show = function () {
				const out = origShow.apply(this, arguments);
				return Promise.resolve(out).then(() => hideList(this));
			};
		}
		if (frappe.views.ListSidebar && !frappe.views.ListSidebar.prototype.__kisan_sidebar_hide) {
			frappe.views.ListSidebar.prototype.__kisan_sidebar_hide = true;
			const origMake = frappe.views.ListSidebar.prototype.make;
			frappe.views.ListSidebar.prototype.make = function () {
				if (rules().list.indexOf(this.doctype) !== -1) {
					return;
				}
				return origMake.apply(this, arguments);
			};
		}
	}

	function patchForm() {
		if (!frappe.ui.form.Form || frappe.ui.form.Form.prototype.__kisan_sidebar_hide) {
			return;
		}
		frappe.ui.form.Form.prototype.__kisan_sidebar_hide = true;
		const orig = frappe.ui.form.Form.prototype.render_form;
		frappe.ui.form.Form.prototype.render_form = function (switched) {
			const hide = rules().details.indexOf(this.doctype) !== -1;
			let prev;
			if (hide) {
				prev = frappe.boot.desk_settings.form_sidebar;
				frappe.boot.desk_settings.form_sidebar = false;
			}
			try {
				return orig.call(this, switched);
			} finally {
				if (hide) {
					frappe.boot.desk_settings.form_sidebar = prev;
				}
				hideForm(this);
			}
		};
	}

	function apply() {
		registerListSettings();
		registerFormHandlers();
		patchList();
		patchForm();
		if (window.cur_list) {
			hideList(cur_list);
		}
		if (window.cur_frm) {
			hideForm(cur_frm);
		}
	}

	function boot() {
		if (!window.frappe || !frappe.views) {
			setTimeout(boot, 25);
			return;
		}
		apply();
	}

	boot();

	frappe.ready(function () {
		apply();
		$(document).on("page-change form-load form-refresh", apply);
	});

	kisan_customization.sidebar_hide.apply = apply;
})();
