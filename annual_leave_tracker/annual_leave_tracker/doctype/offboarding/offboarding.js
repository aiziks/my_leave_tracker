// Copyright (c) 2022, SWIFTA SERVICES LIMITED and contributors
// For license information, please see license.txt

frappe.ui.form.on('Offboarding', {
  employee_offboarding_template: function(frm) {
		frm.doc.task = [];
		erpnext.utils.map_current_doc({
			method: "erp_generic.erp_generic.doctype.offboarding.offboarding.offboarding_template",
			source_name: frm.doc.employee_offboarding_template,
			frm: frm
		});
	},
  refresh: function(frm) {
    frm.toggle_display(['total','completed','resignation_letter_date','exit_interview_section'], !frm.is_new());
  }
});
