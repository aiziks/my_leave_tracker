from __future__ import unicode_literals
import frappe, json
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cstr, cint, get_fullname, get_url


@frappe.whitelist()
def get_template_form(user_id):
    employee = frappe.db.get_value('Employee', {"user_id": user_id}, ['category','name', 'employee_number','department', 'reporting_manager'],as_dict=1)
    # approvers = frappe.db.get_values('Department Appraisal Approver', {"parent": employee.department}, 'lm1',as_dict=1)

    reporting_mn_email = frappe.db.get_value('Employee', {"name" : employee.reporting_manager}, 'user_id');

    template_form = frappe.db.get_value('Appraisal Form Template',{"specify_employee_category": employee.category}, 'name');

    frappe.errprint('employee record is:' +json.dumps(employee));

    thisdict = {
      "employee_name": employee.name,
      "employee_full_name": get_fullname(user_id),
      "employee_category": employee.category,
      "template_form": template_form,
      "employee_number": employee.employee_number,
      "employee_reporting_mn_email": reporting_mn_email
      # "first_lm":approvers[0].lm1,
      # "second_lm":approvers[1].lm1
    }

    return thisdict;


@frappe.whitelist()
def fetch_appraisal_template(source_name, target_doc=None):
    target_doc = get_mapped_doc("Appraisal Form Template", source_name, {
         "Appraisal Form Template": {
            "doctype": "Appraisal",
         },
         "Appraisal Form Template Goal": {
            "doctype": "Appraisal Form Goal",
         },
         "Appraisal Form Template Goal Competence": {
            "doctype": "Appraisal Form Goal Competence",
         },
         "Appraisal Form Template Goal Capacity": {
            "doctype": "Appraisal Form Goal Capacity",
         },
         "Appraisal Weight Template Score": {
             "doctype": "Appraisal Weight Form Goal",
         },
         "Appraisal Form Template Summary Rating": {
             "doctype": "Appraisal Form Summary Rating",
         },
         "Appraisal Form Template Recommendations": {
             "doctype": "Appraisal Form Recommendation",
         }
    }, target_doc,ignore_permissions=True)

    return target_doc;