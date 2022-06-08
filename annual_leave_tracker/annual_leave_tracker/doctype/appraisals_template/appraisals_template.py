# Copyright (c) 2021, SWIFTA SERVICES LIMITED and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.model.document import Document
from frappe.utils import cstr, cint, get_fullname, get_url

from frappe import _
from frappe.model.mapper import get_mapped_doc

from frappe.permissions import add_user_permission, remove_user_permission, \
  set_user_permission_if_allowed, has_permission


class AppraisalsTemplate(Document):
	pass



@frappe.whitelist()
def fetch_appraisal_template(source_name, target_doc=None):
    target_doc = get_mapped_doc("Appraisals Template", source_name, {
         "Appraisals Template": {
            "doctype": "Appraisals",
         },
         "Appraisals Template Goal": {
            "doctype": "Appraisals Goal",
         },
         "Appraisals Template Goal Competence": {
            "doctype": "Appraisals Goal Competence",
         },
         "Appraisals Template Goal Capacity": {
            "doctype": "Appraisals Goal Capacity",
         },
         "Appraisals Template Summary Rating": {
             "doctype": "Appraisals Summary Rating",
         },
         "Appraisals Template Recommendations": {
             "doctype": "Appraisals Recommendation",
         }
    }, target_doc,ignore_permissions=True)

    return target_doc;

@frappe.whitelist()
def get_template_form(user_id):
    # employee = frappe.db.get_value('Employee', {"user_id": user_id}, ['category','name', 'employee_number','department', 'reporting_manager'],as_dict=1)
    employee = frappe.db.get_value('Employee', {"user_id": user_id}, ['category','name', 'employee_number','department', 'reports_to'],as_dict=1)
    # approvers = frappe.db.get_values('Department Appraisal Approver', {"parent": employee.department}, 'lm1',as_dict=1)

    # reporting_mn_email = frappe.db.get_value('Employee', {"name" : employee.reporting_manager}, 'user_id');
    reporting_mn_email = frappe.db.get_value('Employee', {"name" : employee.reports_to}, 'user_id')

    template_form = frappe.db.get_value('Appraisals Template',{"specify_employee_category": employee.category}, 'name');

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
def fetch_email_id(employee_name, for_reporting_manager):

    frappe.errprint('employee_name: '+ employee_name + ' for_reporting_manager: '+ for_reporting_manager);

    # email_id = None;

    if for_reporting_manager == 'True':
      # reporting_manager = frappe.db.get_value('Employee', employee_name,'reporting_manager');
      reporting_manager = frappe.db.get_value('Employee', employee_name,'reports_to')

      email_id = frappe.db.get_value('Employee', reporting_manager, 'user_id')

      frappe.errprint('email_id: '+ str(email_id))

      return email_id;
    else:
      email_id_2 = frappe.db.get_value('Employee', employee_name, 'user_id');

      frappe.errprint('email_id_2: '+ email_id_2);

      return email_id_2;
