// Copyright (c) 2026, Hidayatali and contributors
// For license information, please see license.txt

console.log('Outward Jawak client script loaded');

let currentAawak = null;
let aawakFetchToken = 0;
let recalcToken = 0;

function getAawakLoadKey(frm) {
	if (!frm.doc.firm || !frm.doc.inward_lot_no) {
		return '';
	}
	return `${frm.doc.firm}::${frm.doc.inward_lot_no}`;
}

function shouldFetchAawak(frm) {
	if (frm.doc.docstatus !== 0) {
		return false;
	}

	if (frm.doc.inward_aawak) {
		return false;
	}

	const loadKey = getAawakLoadKey(frm);
	if (!loadKey) {
		return false;
	}

	// Avoid duplicate fetch on every refresh when data is already loaded.
	return frm._aawak_loaded_key !== loadKey;
}

frappe.ui.form.on('Outward Jawak', {
	onload: function (frm) {
		console.log('Outward Jawak onload event called');

		// Ensure proper field display on form load
		if (frm.doc.storage_customer || (frm.doc.commodities && frm.doc.commodities.length > 0) || frm.doc.godown || frm.doc.floor || frm.doc.chamber) {
			// Refresh fields to show actual names instead of naming series
			frm.refresh_field('storage_customer');
			frm.refresh_field('commodities');
			frm.refresh_field('godown');
			frm.refresh_field('floor');
			frm.refresh_field('chamber');
		}

		// If form has data but amounts are not calculated, trigger calculation
		if (frm.doc.jawak_bag_details && frm.doc.jawak_bag_details.length > 0 &&
			(!frm.doc.total_amount || frm.doc.total_amount === 0)) {
			console.log('Triggering calculation on form load');
			recalculateAllAmounts(frm);
		}

		// Apply bold styling to specific field labels
		applyBoldLabels(frm);

		initializeDraftForm(frm);
	},
	
	refresh: function (frm) {
		console.log('Outward Jawak refresh event called');

		initializeDraftForm(frm);

		// Ensure all fields are visible and refreshed with actual names
		console.log('Refreshing all fields');
		frm.refresh_field('storage_customer');
		frm.refresh_field('commodities');
		frm.refresh_field('godown');
		frm.refresh_field('floor');
		frm.refresh_field('chamber');
		frm.refresh_field('jawak_bag_details');
		frm.refresh_field('total_bags');
		frm.refresh_field('released_bags');
		frm.refresh_field('total_weight');
		frm.refresh_field('released_bag_weight');
		frm.refresh_field('total_amount');
		frm.refresh_field('additional_charges');
		frm.refresh_field('discount');
		frm.refresh_field('net_amount');
		frm.refresh_field('payment_method');
		frm.refresh_field('payment_reference');
		frm.refresh_field('notes');
		frm.refresh_field('sales_invoice');

		if (frm.doc.docstatus === 1 && frm.doc.sales_invoice) {
			frm.add_custom_button(__('View Sales Invoice'), () => {
				frappe.set_route('Form', 'Sales Invoice', frm.doc.sales_invoice);
			});
		}

		if (frm.doc.docstatus === 1) {
			syncOutwardJawakStatus(frm);
		}

		// If form has data but amounts are not calculated, trigger calculation
		if (frm.doc.jawak_bag_details && frm.doc.jawak_bag_details.length > 0 &&
			(!frm.doc.total_amount || frm.doc.total_amount === 0)) {
			console.log('Triggering calculation for existing data');
			recalculateAllAmounts(frm);
		}

		// Apply bold styling to specific field labels
		applyBoldLabels(frm);

		console.log('All fields refreshed');
	},

	firm: function (frm) {
		console.log('firm field changed to:', frm.doc.firm);
		onFirmChange(frm);
	},

	inward_lot_no: function (frm) {
		console.log('inward_lot_no field changed to:', frm.doc.inward_lot_no);
		onLotChange(frm);
	},

	jawak_date: function (frm) {
		console.log('jawak_date changed to:', frm.doc.jawak_date);

		// Validate Jawak date against Aawak date
		validateJawakDate(frm);

		// Recalculate all days and amounts when jawak date changes
		// Use setTimeout to ensure the form value is fully updated
		setTimeout(() => {
			recalculateAllAmounts(frm);
		}, 100);
	},

	additional_charges: function (frm) {
		console.log('additional_charges changed to:', frm.doc.additional_charges);
		calculateNetAmount(frm);
	},

	discount: function (frm) {
		console.log('discount changed to:', frm.doc.discount);
		calculateNetAmount(frm);
	},

	inward_charges: function (frm) {
		console.log('inward_charges changed to:', frm.doc.inward_charges);
		calculateNetAmount(frm);
	},

	payment_method: function (frm) {
		console.log('payment_method changed to:', frm.doc.payment_method);
		// Clear payment reference when payment method changes
		if (frm.doc.payment_method === 'Cash') {
			frm.set_value('payment_reference', '');
		}
	}
});

// Jawak Bag Detail child table events
frappe.ui.form.on('Jawak Bag Detail', {
	release_bags: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		console.log('release_bags changed to:', row.release_bags, 'for row:', row.name);

		// Validate release bags cannot exceed available bags
		if (row.release_bags > row.total_bags) {
			frappe.msgprint({
				title: __('Invalid Release Quantity'),
				message: __('Release bags cannot exceed available bags'),
				indicator: 'red'
			});
			frappe.model.set_value(cdt, cdn, 'release_bags', row.total_bags);
			return;
		}

		// Calculate total amount for this row and then update parent
		// Passing true to indicate we want to update parent totals after this row update
		calculateRowAmount(frm, cdt, cdn, true);
	},

	add_amount: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		console.log('add_amount changed to:', row.add_amount, 'for row:', row.name);

		// Recalculate total_amount when add_amount changes
		// Use base_total_amount + add_amount, rounded to nearest whole number
		let baseAmount = row.base_total_amount || 0;
		let addAmount = row.add_amount || 0;
		let totalAmount = Math.round(baseAmount + addAmount);

		frappe.model.set_value(cdt, cdn, 'total_amount', totalAmount);

		// Update parent totals
		calculateParentTotals(frm);
	},

	jawak_bag_details_remove: function (frm) {
		console.log('Bag detail row removed');
		calculateParentTotals(frm);
	},

	jawak_bag_details_add: function (frm) {
		console.log('Bag detail row added');
		// Set default release_bags = total_bags for new rows
		let new_row = frm.doc.jawak_bag_details[frm.doc.jawak_bag_details.length - 1];
		if (new_row.total_bags && !new_row.release_bags) {
			frappe.model.set_value('Jawak Bag Detail', new_row.name, 'release_bags', new_row.total_bags);
		}
	}
});

// Helper Functions

function syncOutwardJawakStatus(frm) {
	if (!frm.doc.name || frm.doc.__islocal) {
		return;
	}

	frappe.call({
		method: 'kisan_customization.kisan_customization.doctype.outward_jawak.outward_jawak.sync_status',
		args: { name: frm.doc.name },
		async: true,
		callback(r) {
			if (r.message && r.message !== frm.doc.status) {
				frm.set_value('status', r.message);
				frm.refresh_field('status');
			}
		},
	});
}

function initializeDraftForm(frm) {
	if (frm.doc.docstatus !== 0) {
		return;
	}

	if (frm.doc.firm) {
		loadLotOptions(frm, { preserveValue: true });
	}

	if (frm.doc.inward_aawak) {
		loadAawakContext(frm, frm.doc.inward_aawak);
		return;
	}

	if (shouldFetchAawak(frm)) {
		console.log('Auto-populating from Firm and Inward Lot No');
		fetchAawakByFirmAndLot(frm);
	}
}

function loadLotOptions(frm, opts = {}) {
	const preserveValue = opts.preserveValue !== false;
	const currentLot = opts.ensureLot || frm.doc.inward_lot_no;

	if (!frm.doc.firm) {
		frm.set_df_property('inward_lot_no', 'options', currentLot ? [currentLot] : []);
		if (!preserveValue) {
			frm.set_value('inward_lot_no', '');
		}
		frm.refresh_field('inward_lot_no');
		return;
	}

	const firm = String(frm.doc.firm);

	frappe.call({
		method: 'kisan_customization.kisan_customization.doctype.outward_jawak.outward_jawak.get_available_lots',
		args: { firm },
		callback: function (r) {
			const lots = [...(r.message || [])];

			// Keep the saved lot visible in Select options (amend / reload).
			if (currentLot && !lots.includes(currentLot)) {
				lots.unshift(currentLot);
			}

			frm.set_df_property('inward_lot_no', 'options', lots);
			frm.refresh_field('inward_lot_no');

			if (!preserveValue && currentLot && !lots.includes(currentLot)) {
				frm.set_value('inward_lot_no', '');
			}

			if (!lots.length) {
				frappe.msgprint({
					title: __('No Lots Found'),
					message: __('No submitted Inward Aawak with remaining bags found for Firm {0}.', [firm]),
					indicator: 'orange'
				});
			}
		}
	});
}

function onFirmChange(frm) {
	currentAawak = null;
	frm._aawak_loaded_key = '';

	frm.set_value('inward_charges', 0);
	frm.set_value('inward_lot_no', '');
	clearForm(frm);
	loadLotOptions(frm, { preserveValue: false });
}

function onLotChange(frm) {
	currentAawak = null;
	frm._aawak_loaded_key = '';

	frm.set_value('inward_charges', 0);
	clearForm(frm);

	if (frm.doc.firm && frm.doc.inward_lot_no) {
		console.log('Attempting fetch using Firm and Inward Lot No');
		fetchAawakByFirmAndLot(frm);
	}
}

function loadAawakContext(frm, aawakName) {
	if (!aawakName) {
		return;
	}

	if (currentAawak && currentAawak.name === aawakName) {
		return;
	}

	const fetchToken = ++aawakFetchToken;

	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Inward Aawak',
			name: aawakName
		},
		callback: function (r) {
			if (fetchToken !== aawakFetchToken) {
				return;
			}

			if (!r.message) {
				return;
			}

			currentAawak = r.message;
			frm._aawak_loaded_key = getAawakLoadKey(frm);

			if (!frm.doc.inward_lot_no && r.message.lot_number) {
				frm.set_value('inward_lot_no', r.message.lot_number);
			}

			loadLotOptions(frm, {
				preserveValue: true,
				ensureLot: r.message.lot_number || frm.doc.inward_lot_no,
			});

			if (!frm.doc.jawak_bag_details || !frm.doc.jawak_bag_details.length) {
				populateFromAawakData(frm, r.message);
				return;
			}

			validateJawakDate(frm);
		}
	});
}

function fetchAawakByFirmAndLot(frm) {
	const firm = frm.doc.firm;
	const lotNo = frm.doc.inward_lot_no;

	if (!firm || !lotNo) {
		console.log('Firm or Inward Lot No missing; skipping fetch');
		currentAawak = null;
		return;
	}

	const firmFilter = String(firm);
	const lotFilter = String(lotNo);
	const fetchToken = ++aawakFetchToken;

	console.log('Fetching Inward Aawak using Firm and Inward Lot No:', firmFilter, lotFilter);

	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Inward Aawak',
			filters: {
				firm: firmFilter,
				lot_number: lotFilter,
				docstatus: 1
			},
			fields: ['name'],
			limit_page_length: 2
		},
		callback: function (r) {
			if (fetchToken !== aawakFetchToken) {
				return;
			}

			if (r.message && r.message.length === 1) {
				console.log('Unique Inward Aawak match found:', r.message[0].name);
				fetchAawakRecord(frm, r.message[0].name, fetchToken);
			} else if (r.message && r.message.length === 0) {
				clearForm(frm);
				frappe.msgprint({
					title: __('Inward Aawak Not Found'),
					message: __('No Inward Aawak found for Firm {0} and Inward Lot No {1}.', [firm, lotNo]),
					indicator: 'red'
				});
			} else {
				clearForm(frm);
				frappe.msgprint({
					title: __('Multiple Matches Found'),
					message: __('Multiple Inward Aawak records found for Firm {0} and Inward Lot No {1}. Please resolve duplicates.', [firm, lotNo]),
					indicator: 'red'
				});
			}
		}
	});
}

function fetchAawakRecord(frm, aawakName, fetchToken = aawakFetchToken) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Inward Aawak',
			name: aawakName
		},
		callback: function (r) {
			if (fetchToken !== aawakFetchToken) {
				return;
			}

			console.log('Inward Aawak data received:', r.message);

			if (r.message) {
				populateFromAawakData(frm, r.message);

				// Validate Jawak date against Aawak date after populating
				validateJawakDate(frm);
			} else {
				clearForm(frm);
				frappe.msgprint({
					title: __('Error'),
					message: __('Could not fetch Inward Aawak details'),
					indicator: 'red'
				});
			}
		}
	});
}

function populateFromAawakData(frm, aawak) {
	if (!aawak) {
		return;
	}

	console.log('Populating Outward Jawak from Inward Aawak:', aawak.name);

	// Reset existing auto-populated data without invalidating this populate run
	clearAutoPopulatedFields(frm, false);

	// Keep reference to current Inward Aawak for downstream calculations
	currentAawak = aawak;
	frm._aawak_loaded_key = getAawakLoadKey(frm);

	// Populate basic fields
	frm.set_value('storage_customer', aawak.storage_customer);
	frm.set_value('godown', aawak.godown);

	// Get floor and chamber from chamber allocations
	if (aawak.chamber_allocations && aawak.chamber_allocations.length > 0) {
		let allocation = aawak.chamber_allocations[0];
		frm.set_value('floor', allocation.floor);
		frm.set_value('chamber', allocation.chamber);
	}

	// Populate commodities with names (async)
	populateCommodities(frm, aawak.commodities);

	// Populate bag details
	populateBagDetails(frm, aawak);

	// Auto-fetch inward charges
	if (aawak.charges) {
		frm.set_value('inward_charges', aawak.charges);
	}

	// Refresh all fields to ensure visibility and proper display of names
	frm.refresh_field('storage_customer');
	frm.refresh_field('godown');
	frm.refresh_field('floor');
	frm.refresh_field('chamber');
	frm.refresh_field('jawak_bag_details');
	frm.refresh_field('inward_charges');
}

function populateCommodities(frm, inward_commodities) {
	frm.clear_table('commodities');

	if (!inward_commodities || !inward_commodities.length) {
		frm.refresh_field('commodities');
		return;
	}

	const item_codes = [
		...new Set(
			inward_commodities.map((row) => row.commodity).filter(Boolean)
		),
	];

	if (!item_codes.length) {
		frm.refresh_field('commodities');
		return;
	}

	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Item',
			filters: [['name', 'in', item_codes]],
			fields: ['name', 'item_name'],
		},
		callback: function (r) {
			const valid_items = new Set((r.message || []).map((item) => item.name));

			(r.message || []).forEach((item) => {
				if (frappe.utils.add_link_title) {
					frappe.utils.add_link_title('Item', item.name, item.item_name || item.name);
				}
			});

			item_codes.forEach((item_code) => {
				if (!valid_items.has(item_code)) {
					return;
				}

				const row = frm.add_child('commodities');
				frappe.model.set_value(row.doctype, row.name, 'commodity', item_code);
			});

			frm.refresh_field('commodities');
			console.log('Commodities populated:', item_codes.filter((item) => valid_items.has(item)));
		},
	});
}

function populateBagDetails(frm, aawak) {
	frm.clear_table('jawak_bag_details');

	if (!frm.doc.firm || !frm.doc.inward_lot_no) {
		return;
	}

	frappe.call({
		method: 'kisan_customization.kisan_customization.doctype.outward_jawak.outward_jawak.get_remaining_bags',
		args: {
			firm: frm.doc.firm,
			inward_lot_no: frm.doc.inward_lot_no,
			exclude_jawak: frm.doc.name && !frm.doc.__islocal ? frm.doc.name : null,
		},
		callback: function (r) {
			const data = r.message || {};

			if (data.inward_aawak) {
				frm.set_value('inward_aawak', data.inward_aawak);
			} else if (aawak?.name) {
				frm.set_value('inward_aawak', aawak.name);
			}

			if (!data.bag_details || !data.bag_details.length) {
				frappe.msgprint({
					title: __('No Bags Available'),
					message: __('All bags for this Inward Lot have already been delivered.'),
					indicator: 'orange'
				});
				frm.refresh_field('jawak_bag_details');
				return;
			}

			data.bag_details.forEach((bagDetail) => {
				const new_row = frm.add_child('jawak_bag_details');
				frappe.model.set_value('Jawak Bag Detail', new_row.name, 'bag_type', bagDetail.bag_type);
				frappe.model.set_value('Jawak Bag Detail', new_row.name, 'total_bags', bagDetail.remaining_bags);
				frappe.model.set_value('Jawak Bag Detail', new_row.name, 'release_bags', bagDetail.remaining_bags);
				frappe.model.set_value('Jawak Bag Detail', new_row.name, 'rate', bagDetail.rate || 0);
			});

			frm.refresh_field('jawak_bag_details');
			recalculateAllAmounts(frm);
		},
	});
}

function recalculateAllAmounts(frm) {
	if (!frm.doc.jawak_date || !currentAawak || !currentAawak.aawak_date) {
		console.log('Cannot recalculate: missing jawak_date or Inward Aawak context');
		return;
	}

	console.log('Recalculating all amounts for jawak_date:', frm.doc.jawak_date);

	const calcToken = ++recalcToken;

	// Fetch settings ONCE to avoid N+1 queries and race conditions
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Kisan Master Settings',
			name: 'Kisan Master Settings'
		},
		callback: function (r) {
			if (calcToken !== recalcToken) {
				return;
			}

			if (r.message) {
				let settings = r.message;

				if (frm.doc.jawak_bag_details) {
					frm.doc.jawak_bag_details.forEach(row => {
						if (!locals['Jawak Bag Detail']?.[row.name]) {
							return;
						}
						performRowCalculation(frm, 'Jawak Bag Detail', row.name, settings);
					});
				}

				frm.refresh_field('jawak_bag_details');
				calculateParentTotals(frm);
			}
		}
	});
}

function calculateRowAmount(frm, cdt, cdn, updateParent = false) {
	const calcToken = ++recalcToken;

	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Kisan Master Settings',
			name: 'Kisan Master Settings'
		},
		callback: function (r) {
			if (calcToken !== recalcToken) {
				return;
			}

			if (r.message) {
				performRowCalculation(frm, cdt, cdn, r.message);
				if (updateParent) {
					calculateParentTotals(frm);
				}
			}
		}
	});
}

function performRowCalculation(frm, cdt, cdn, settings) {
	let row = locals[cdt]?.[cdn];
	if (!row) {
		return;
	}

	if (!frm.doc.jawak_date || !currentAawak || !currentAawak.aawak_date) {
		return;
	}

	let aawakDate = new Date(currentAawak.aawak_date);
	let jawakDate = new Date(frm.doc.jawak_date);

	let aawakDay = new Date(aawakDate.getFullYear(), aawakDate.getMonth(), aawakDate.getDate());
	let jawakDay = new Date(jawakDate.getFullYear(), jawakDate.getMonth(), jawakDate.getDate());
	let actualDays = Math.round((jawakDay - aawakDay) / (1000 * 60 * 60 * 24));

	let minDays = parseInt(settings.minimum_chargeable_days) || 15;
	let extraDays = parseInt(settings.extra_days_after_minimum) || 2;
	let daysPerMonth = parseInt(settings.days_per_month) || 30;

	// Calculate chargeable days
	let chargeableDays;
	if (actualDays <= minDays) {
		chargeableDays = minDays;
	} else {
		chargeableDays = actualDays + extraDays;
	}

	// Update total days
	frappe.model.set_value(cdt, cdn, 'total_days', chargeableDays);

	// Calculate base amount (before add_amount)
	if (row.release_bags && row.rate) {
		let dailyRate = row.rate / daysPerMonth;
		let baseAmount = row.release_bags * dailyRate * chargeableDays;
		baseAmount = Math.round(baseAmount * 100) / 100; // Keep 2 decimal precision for base

		// Store base amount for use when add_amount changes
		frappe.model.set_value(cdt, cdn, 'base_total_amount', baseAmount);

		// Calculate total_amount = base_total_amount + add_amount, rounded to nearest whole number
		let addAmount = row.add_amount || 0;
		let totalAmount = Math.round(baseAmount + addAmount);

		frappe.model.set_value(cdt, cdn, 'total_amount', totalAmount);
	}
}

function calculateParentTotals(frm) {
	console.log('Calculating parent totals');

	let totalBags = 0;
	let releasedBags = 0;
	let totalWeight = 0;
	let releasedWeight = 0;
	let totalAmount = 0;

	if (frm.doc.jawak_bag_details) {
		frm.doc.jawak_bag_details.forEach(row => {
			totalBags += row.total_bags || 0;
			releasedBags += row.release_bags || 0;

			// bag_type contains the bag weight (e.g., "5" for 5kg bags)
			let bagWeight = parseFloat(row.bag_type) || 0;
			totalWeight += (row.total_bags || 0) * bagWeight;
			releasedWeight += (row.release_bags || 0) * bagWeight;
			totalAmount += row.total_amount || 0;

			console.log('Row totals:', {
				totalBags: row.total_bags,
				releasedBags: row.release_bags,
				bagWeight: bagWeight,
				totalAmount: row.total_amount
			});
		});
	}

	// Round weights to 2 decimal places
	totalWeight = Math.round(totalWeight * 100) / 100;
	releasedWeight = Math.round(releasedWeight * 100) / 100;
	totalAmount = Math.round(totalAmount * 100) / 100;

	console.log('Parent totals calculated:', {
		totalBags,
		releasedBags,
		totalWeight,
		releasedWeight,
		totalAmount
	});

	frm.set_value('total_bags', totalBags);
	frm.set_value('released_bags', releasedBags);
	frm.set_value('total_weight', totalWeight);
	frm.set_value('released_bag_weight', releasedWeight);
	frm.set_value('total_amount', totalAmount);

	calculateNetAmount(frm);
}

function calculateNetAmount(frm) {
	let totalAmount = frm.doc.total_amount || 0;
	let additionalCharges = frm.doc.additional_charges || 0;
	let inwardCharges = frm.doc.inward_charges || 0;
	let discount = frm.doc.discount || 0;

	let netAmount = totalAmount + additionalCharges + inwardCharges - discount;
	netAmount = Math.round(netAmount * 100) / 100; // Round to 2 decimal places

	console.log('Net amount calculated:', netAmount, 'from total:', totalAmount, 'plus additional charges:', additionalCharges, 'plus inward charges:', inwardCharges, 'minus discount:', discount);

	frm.set_value('net_amount', netAmount);
}

function clearForm(frm) {
	clearAutoPopulatedFields(frm, true);
}

function clearAutoPopulatedFields(frm, resetAawakContext = true) {
	console.log('Clearing form');

	if (resetAawakContext) {
		currentAawak = null;
		frm._aawak_loaded_key = '';
		aawakFetchToken += 1;
		recalcToken += 1;
	}

	// Clear all auto-populated fields
	frm.set_value('storage_customer', '');
	frm.clear_table('commodities');
	frm.set_value('godown', '');
	frm.set_value('floor', '');
	frm.set_value('chamber', '');

	// Clear bag details
	frm.clear_table('jawak_bag_details');

	// Reset totals
	frm.set_value('total_bags', 0);
	frm.set_value('released_bags', 0);
	frm.set_value('total_weight', 0);
	frm.set_value('released_bag_weight', 0);
	frm.set_value('total_amount', 0);
	frm.set_value('net_amount', 0);
}

function validateJawakDate(frm) {
	// Only validate if both dates are present
	if (!frm.doc.jawak_date || !currentAawak || !currentAawak.aawak_date) {
		return;
	}

	console.log('Validating Jawak date against Aawak date');

	let aawakDate = new Date(currentAawak.aawak_date);
	let jawakDate = new Date(frm.doc.jawak_date);

	console.log('Comparing dates - Aawak:', aawakDate, 'Jawak:', jawakDate);

	// Check if Jawak date is after Aawak date
	if (jawakDate <= aawakDate) {
		// Clear the invalid Jawak date
		frm.set_value('jawak_date', '');

		// Show error message
		frappe.msgprint({
			title: __('Invalid Jawak Date'),
			message: __('Jawak Date must be after Aawak Date. Aawak Date is: ' + frappe.datetime.str_to_user(aawakDate) + '. Please enter a later date.'),
			indicator: 'red'
		});

		console.log('Date validation failed - Jawak date cleared');
	} else {
		console.log('Date validation passed');
	}
}

function applyBoldLabels(frm) {
	// Apply bold styling to specific field labels
	const fieldsToBold = ['godown', 'floor', 'chamber'];

	fieldsToBold.forEach(function (fieldname) {
		// Use setTimeout to ensure DOM is ready
		setTimeout(function () {
			// Find the label element for the field
			let fieldWrapper = frm.fields_dict[fieldname].$wrapper;
			if (fieldWrapper && fieldWrapper.length) {
				let labelElement = fieldWrapper.find('label');
				if (labelElement && labelElement.length) {
					labelElement.css('font-weight', 'bold');
					console.log('Applied bold styling to', fieldname, 'label');
				}
			}
		}, 100);
	});
}