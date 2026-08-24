(function () {
	const settings = frappe.listview_settings["Purchase Order"] || {};
	const _onload = settings.onload;

	settings.onload = function (listview) {
		if (_onload) {
			_onload(listview);
		}

		const label = encodeURIComponent(__("Purchase Receipt"));
		listview.page.actions.find(`a.dropdown-item[data-label="${label}"]`).remove();
	};

	frappe.listview_settings["Purchase Order"] = settings;
})();
