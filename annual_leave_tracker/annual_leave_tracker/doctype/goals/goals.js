// Copyright (c) 2021, SWIFTA SERVICES LIMITED and contributors
// For license information, please see license.txt

frappe.ui.form.on('Goals', {
	end_date: function(frm){
		console.log("End date")
    	if(frm.doc.start_date >= frm.doc.end_date){
			console.log(frm.doc.start_date);
			console.log(frm.doc.end_date);
			frm.set_value('start_date','');
			frm.set_value('end_date','');
			frappe.throw('End date must be greater than start date');
    	}
	},

	percentage_completed: function(frm){
		console.log("Percentage")
    	if(frm.doc.percentage_completed > 100){
			console.log(frm.doc.percentage_completed);
			frm.set_value('percentage_completed','');
			frappe.throw('Percentage completed must be between 0 and 100');
    	}
	},
	before_save: function(frm){
		if (frm.is_new()){
			frm.set_value('status', "Pending Approval")
		}
		if (frm.doc.stage == "Completed"){
			frm.set_value('percentage_completed', 100)
		}
	},

	onload: function(frm){
		if (frm.doc.stage == "Completed" && frappe.user.has_role("Manager")){
			frm.set_df_property('status', 'read_only', 0)
			frm.set_df_property('status', 'options', ['Approved', 'Decline'])
			console.log('Helloooo')
		}
	}
});
