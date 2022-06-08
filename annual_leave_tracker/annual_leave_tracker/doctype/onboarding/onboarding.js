// Copyright (c) 2022, SWIFTA SERVICES LIMITED and contributors
// For license information, please see license.txt

frappe.ui.form.on('Onboarding', {
  employee_onboarding_template: function(frm) {
		frm.doc.task = [];
		erpnext.utils.map_current_doc({
			method: "erp_generic.erp_generic.doctype.onboarding.onboarding.onboarding_template",
			source_name: frm.doc.employee_onboarding_template,
			frm: frm
		});
	},
  refresh: function(frm) {
    frm.toggle_display(['total','completed'], !frm.is_new());
  }
});
