kisan_customization.delivery_payment_days.bind("Purchase Order");

frappe.ui.form.on('Purchase Order', {
    
    setup: function(frm) {
        frm.set_query('custom_broker', function() {
            return {
                filters: {
                    'supplier_group': 'Broker'
                }
            };
        });
    },

    custom_commission_type: function(frm) {
        // Clear both input fields when type changes
        frm.set_value('custom_commission_percent', 0);
        frm.set_value('custom_commission_amount', 0);
        
        // Recalculate (will become 0)
        calculate_broker_commission(frm);
    },

    custom_commission_percent: function(frm) {
        calculate_broker_commission(frm);
    },

    custom_commission_amount: function(frm) {
        calculate_broker_commission(frm);
    },

    net_total: function(frm) {
        calculate_broker_commission(frm);
    },

    total_qty: function(frm) {
        calculate_broker_commission(frm);
    },

    refresh: function(frm) {
        calculate_broker_commission(frm);
    }
});

function calculate_broker_commission(frm) {
    let commission_type = frm.doc.custom_commission_type;
    let commission_amount = 0;

    if (commission_type === "Percentage") {
        let net_amount = flt(frm.doc.net_total) || 0;
        let percent = flt(frm.doc.custom_commission_percent) || 0;
        commission_amount = (net_amount * percent) / 100;
    }
    else if (commission_type === "Total Qty") {
        let total_qty = flt(frm.doc.total_qty) || 0;
        let rate = flt(frm.doc.custom_commission_amount) || 0;
        commission_amount = total_qty * rate;
    }

    frm.set_value('custom_broker_commission_amount', commission_amount);
}