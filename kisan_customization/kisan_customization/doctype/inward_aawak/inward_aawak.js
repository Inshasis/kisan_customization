// Copyright (c) 2026, Hidayatali and contributors

function weightRequiredForRow(row) {
	const uom = (row.uom || 'Bag').trim();
	return ['Kg', 'Bag', 'Nos'].includes(uom);
}

frappe.provide("kisan_customization.master_groups");

const RENTAL_ITEM_GROUP =
	kisan_customization.master_groups.RENTAL_ITEM_GROUP || "Rental Commodity";
const RENTAL_CUSTOMER_GROUP =
	kisan_customization.master_groups.RENTAL_CUSTOMER_GROUP || "Rental Customers";

frappe.ui.form.on('Inward Aawak', {
	refresh(frm) {
		frm.set_query('commodities', () => ({
			filters: {
				item_group: RENTAL_ITEM_GROUP,
				disabled: 0,
			},
		}));

		frm.set_query('storage_customer', () => ({
			filters: {
				customer_group: RENTAL_CUSTOMER_GROUP,
				disabled: 0,
			},
		}));

		if (!frm.doc.aawak_date) {
			frm.set_value('aawak_date', frappe.datetime.get_today());
		}

		if (frm.doc.docstatus === 1) {
			frm.set_df_property('status', 'read_only', 1);
			addCreateJawakButton(frm);
		}

		setupHierarchyFiltering(frm);

		syncChamberAllocationDates(frm);

		calculateGrandTotals(frm);

		if (frm.fields_dict.bag_details?.grid) {
			frm.fields_dict.bag_details.grid.update_docfield_property(
				'lorry_weight_kg',
				'read_only',
				0
			);
		}

	},

	aawak_date(frm) {
		syncChamberAllocationDates(frm);
	},

	validate(frm) {
		if (!(frm.doc.lot_number || '').trim()) {
			frappe.msgprint({
				title: __('Required Field Missing'),
				message: __('Lot Number is mandatory'),
				indicator: 'red',
			});
			frappe.validated = false;
			return;
		}

		if (!frm.doc.storage_customer) {
			frappe.msgprint({
				title: __('Required Field Missing'),
				message: __('Storage Customer is required'),
				indicator: 'red',
			});
			frappe.validated = false;
			return;
		}

		if (!frm.doc.commodities || frm.doc.commodities.length === 0) {
			frappe.msgprint({
				title: __('Required Field Missing'),
				message: __('Please select at least one Commodity'),
				indicator: 'red',
			});
			frappe.validated = false;
			return;
		}

		if (!frm.doc.godown) {
			frappe.msgprint({
				title: __('Required Field Missing'),
				message: __('Godown is required'),
				indicator: 'red',
			});
			frappe.validated = false;
			return;
		}

		if (!frm.doc.bag_details || frm.doc.bag_details.length === 0) {
			frappe.msgprint({
				title: __('Bag Details Required'),
				message: __('Please add at least one bag detail entry'),
				indicator: 'red',
			});
			frappe.validated = false;
			return;
		}

		const config_keys = {};
		let hasValidRows = false;
		frm.doc.bag_details.forEach((row, index) => {
			const weight = row.bag_weight || row.weight_kg;
			if (weightRequiredForRow(row) && !weight) {
				frappe.msgprint({
					title: __('Bag Details Error'),
					message: __('Row {0}: Weight is required for UOM {1}', [index + 1, row.uom || 'Bag']),
					indicator: 'red',
				});
				frappe.validated = false;
				return;
			}

			if (row.bag_configuration) {
				if (config_keys[row.bag_configuration]) {
					frappe.msgprint({
						title: __('Bag Details Error'),
						message: __('Row {0}: Duplicate Bag Configuration line', [index + 1]),
						indicator: 'red',
					});
					frappe.validated = false;
					return;
				}
				config_keys[row.bag_configuration] = true;
			}

			if (!row.number_of_bags || row.number_of_bags <= 0) {
				frappe.msgprint({
					title: __('Bag Details Error'),
					message: __('Row {0}: Quantity must be greater than 0', [index + 1]),
					indicator: 'red',
				});
				frappe.validated = false;
				return;
			}

			if (flt(row.lorry_weight_kg) < 0) {
				frappe.msgprint({
					title: __('Bag Details Error'),
					message: __('Row {0}: Lorry Weight (Kg) cannot be negative', [index + 1]),
					indicator: 'red',
				});
				frappe.validated = false;
				return;
			}
			hasValidRows = true;
		});

		if (!hasValidRows) {
			frappe.validated = false;
			return;
		}

		if (frm.doc.chamber_allocations && frm.doc.chamber_allocations.length > 0) {
			let total_allocated = 0;
			const chamber_codes = [];
			const duplicate_chambers = [];

			frm.doc.chamber_allocations.forEach((allocation, index) => {
				if (!allocation.bags_allocated || allocation.bags_allocated <= 0) {
					frappe.msgprint({
						title: __('Chamber Allocation Error'),
						message: __('Bags Allocated must be greater than 0 for allocation ' + (index + 1)),
						indicator: 'red',
					});
					frappe.validated = false;
					return;
				}

				if (chamber_codes.includes(allocation.chamber)) {
					duplicate_chambers.push(allocation.chamber);
				} else {
					chamber_codes.push(allocation.chamber);
				}

				total_allocated += allocation.bags_allocated;
			});

			if (duplicate_chambers.length > 0) {
				frappe.msgprint({
					title: __('Duplicate Chamber Allocation'),
					message: __('Duplicate chambers found: ' + duplicate_chambers.join(', ') + '. Each chamber can only be allocated once.'),
					indicator: 'red',
				});
				frappe.validated = false;
				return;
			}

			if (total_allocated !== frm.doc.total_bags) {
				frappe.msgprint({
					title: __('Allocation Mismatch'),
					message: __('Total allocated bags (' + total_allocated + ') must equal total bags (' + frm.doc.total_bags + ')'),
					indicator: 'red',
				});
				frappe.validated = false;
				return;
			}
		} else {
			frappe.msgprint({
				title: __('Chamber Allocation Required'),
				message: __('At least one chamber allocation is required'),
				indicator: 'red',
			});
			frappe.validated = false;
		}
	},

	firm(frm) {
		if (frm.doc.godown) {
			frm.set_value('godown', '');
			frm.clear_table('chamber_allocations');
			frm.refresh_field('chamber_allocations');
		}
	},

	godown(frm) {
		frm.clear_table('chamber_allocations');
		frm.refresh_field('chamber_allocations');
	},
});

frappe.ui.form.on('Bag Details', {
	bag_weight(frm, cdt, cdn) {
		calculateRowTotal(frm, cdt, cdn);
		calculateGrandTotals(frm);
	},

	number_of_bags(frm, cdt, cdn) {
		calculateRowTotal(frm, cdt, cdn);
		calculateGrandTotals(frm);
	},

	lorry_weight_kg(frm, cdt, cdn) {
		if (!validateLorryWeightKg(frm, cdt, cdn)) {
			return;
		}
		calculateRowTotal(frm, cdt, cdn);
		calculateGrandTotals(frm);
	},

	bag_details_remove(frm) {
		calculateGrandTotals(frm);
	},

	bag_details_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row) {
			return;
		}
		if (row.number_of_bags === undefined) {
			frappe.model.set_value(cdt, cdn, 'number_of_bags', 0);
		}
		if (row.total_weight === undefined) {
			frappe.model.set_value(cdt, cdn, 'total_weight', 0);
		}
		frappe.model.set_value(cdt, cdn, 'is_auto_populated', 0);
	},
});

frappe.ui.form.on('Chamber Allocation', {
	floor(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, 'chamber', '');
	},

	chamber(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.chamber) {
			frappe.call({
				method: 'frappe.client.get_value',
				args: {
					doctype: 'Floor Chamber',
					filters: { name: row.chamber },
					fieldname: 'max_capacity',
				},
				callback(r) {
					if (r.message && r.message.max_capacity) {
						row.max_capacity = r.message.max_capacity;
					}
				},
			});
		}
	},

	bags_allocated(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.bags_allocated && row.max_capacity && row.bags_allocated > row.max_capacity) {
			frappe.msgprint({
				title: __('Capacity Exceeded'),
				message: __('Bags allocated (' + row.bags_allocated + ') cannot exceed chamber capacity (' + row.max_capacity + ')'),
				indicator: 'red',
			});
			frappe.set_value(cdt, cdn, 'bags_allocated', '');
		}
		validateChamberAllocations(frm);
	},

	chamber_allocations_remove(frm) {
		validateChamberAllocations(frm);
	},

	chamber_allocations_add(frm) {
		const new_row = frm.doc.chamber_allocations[frm.doc.chamber_allocations.length - 1];
		if (new_row) {
			syncChamberAllocationDates(frm);
			if (frm.doc.total_bags) {
				frappe.model.set_value('Chamber Allocation', new_row.name, 'bags_allocated', frm.doc.total_bags);
			}
		}
	},
});

function aawakDateOnly(frm) {
	const value = frm.doc.aawak_date;
	if (!value) {
		return frappe.datetime.get_today();
	}
	return String(value).split(' ')[0];
}

function syncChamberAllocationDates(frm) {
	const allocDate = aawakDateOnly(frm);
	const validTo = frappe.datetime.add_months(allocDate, 6);
	(frm.doc.chamber_allocations || []).forEach((row) => {
		frappe.model.set_value('Chamber Allocation', row.name, 'allocation_date', allocDate);
		frappe.model.set_value('Chamber Allocation', row.name, 'valid_to', validTo);
	});
}

function addCreateJawakButton(frm) {
	if (cint(frm.doc.remaining_bags) <= 0) {
		return;
	}

	frm.add_custom_button(
		__('Create Jawak'),
		() => {
			frappe.call({
				method: 'kisan_customization.inward_aawak.outward_jawak.create_draft_outward_jawak',
				args: { inward_aawak: frm.doc.name },
				freeze: true,
				callback(r) {
					const result = r.message || {};
					if (!result.name) {
						return;
					}
					if (result.created) {
						frappe.show_alert({
							message: __('Draft Outward Jawak {0} created', [result.name]),
							indicator: 'green',
						});
					} else {
						frappe.show_alert({
							message: __('Opening existing draft Outward Jawak {0}', [result.name]),
							indicator: 'blue',
						});
					}
					frappe.set_route('Form', 'Outward Jawak', result.name);
				},
			});
		},
	);
}

function cint(value) {
	return parseInt(value, 10) || 0;
}

function calculateRowTotal(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const weight = parseFloat(row.bag_weight || row.weight_kg);
	const numberOfBags = parseInt(row.number_of_bags, 10);

	if (weight && numberOfBags) {
		if (!isNaN(weight) && !isNaN(numberOfBags)) {
			let totalWeight = weight * numberOfBags;
			totalWeight = Math.round(totalWeight * 100) / 100;
			frappe.model.set_value(cdt, cdn, 'total_weight', totalWeight);
		}
	} else if (flt(row.lorry_weight_kg) > 0) {
		frappe.model.set_value(cdt, cdn, 'total_weight', flt(row.lorry_weight_kg));
	} else {
		frappe.model.set_value(cdt, cdn, 'total_weight', 0);
	}
}

function isLorryWeightProvided(row) {
	return flt(row.lorry_weight_kg) > 0;
}

function validateLorryWeightKg(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (row.lorry_weight_kg === '' || row.lorry_weight_kg == null) {
		return true;
	}
	const weight = flt(row.lorry_weight_kg);
	if (weight < 0) {
		frappe.msgprint({
			title: __('Invalid Lorry Weight'),
			message: __('Lorry Weight (Kg) cannot be negative'),
			indicator: 'red',
		});
		frappe.model.set_value(cdt, cdn, 'lorry_weight_kg', null);
		return false;
	}
	if (weight === 0) {
		frappe.model.set_value(cdt, cdn, 'lorry_weight_kg', null);
	}
	return true;
}

function flt(value) {
	return parseFloat(value) || 0;
}

function calculateGrandTotals(frm) {
	let totalBags = 0;
	let totalWeight = 0;
	let totalLorryWeight = 0;
	let hasLorryInGrid = false;
	if (frm.doc.bag_details) {
		frm.doc.bag_details.forEach((row) => {
			if (row.number_of_bags) {
				totalBags += parseInt(row.number_of_bags, 10) || 0;
			}
			if (row.total_weight) {
				totalWeight += parseFloat(row.total_weight) || 0;
			}
			if (isLorryWeightProvided(row)) {
				hasLorryInGrid = true;
				totalLorryWeight += flt(row.lorry_weight_kg);
			}
		});
	}
	totalWeight = Math.round(totalWeight * 100) / 100;
	totalLorryWeight = Math.round(totalLorryWeight * 100) / 100;
	frm.set_value('total_bags', totalBags);
	frm.set_value('total_weight', totalWeight);

	if (hasLorryInGrid) {
		frm.set_value('total_lorry_weight', totalLorryWeight);
		if (frm.fields_dict.total_lorry_weight) {
			frm.set_df_property('total_lorry_weight', 'read_only', 1);
		}
	} else if (frm.fields_dict.total_lorry_weight) {
		frm.set_df_property('total_lorry_weight', 'read_only', 0);
	}

	validateChamberAllocations(frm);
}

function validateChamberAllocations(frm) {
	if (frm.doc.chamber_allocations && frm.doc.chamber_allocations.length > 0) {
		let total_allocated = 0;
		frm.doc.chamber_allocations.forEach((allocation) => {
			if (allocation.bags_allocated) {
				total_allocated += allocation.bags_allocated;
			}
		});

		if (frm.doc.total_bags && total_allocated !== frm.doc.total_bags) {
			frm.dashboard.add_comment(
				'Allocation Status',
				'Total allocated: ' + total_allocated + ' / Total bags: ' + frm.doc.total_bags,
				'orange'
			);
		} else {
			frm.dashboard.clear_comment();
		}
	}
}

function setupHierarchyFiltering(frm) {
	frm.set_query('godown', () => ({ filters: { status: 'Active', firm: frm.doc.firm } }));
	frm.set_query('floor', 'chamber_allocations', () => ({ filters: { godown: frm.doc.godown, status: 'Active' } }));
	frm.set_query('chamber', 'chamber_allocations', (doc, cdt, cdn) => {
		const row = locals[cdt][cdn];
		return { filters: { floor: row.floor, status: 'Available' } };
	});
}
