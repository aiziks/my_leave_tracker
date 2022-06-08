frappe.pages['employee-profile'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Employee Profile',
		single_column: true
	});
	let employee_name;
	frappe.call({
			method:"erp_generic.api.emp_details.get_user_name",
			args:{
					email: frappe.session.user
			},
			callback: function(r){
            employee_name = JSON.stringify(r.message)
            frappe.set_route("Form/Employee/"+r.message);
        }
	});
}
