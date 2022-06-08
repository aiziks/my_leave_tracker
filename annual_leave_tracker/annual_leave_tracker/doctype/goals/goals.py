# Copyright (c) 2021, SWIFTA SERVICES LIMITED and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name

class Goals(Document):
	pass
	# def validate(self):
	# 	frappe.db.set(self, 'status', 'Pending Approval')

	# def on_submit(self):
	# 	frappe.db.set(self, 'status', 'Approved')

	# def on_cancel(self):
	# 	frappe.db.set(self, 'status', 'Cancelled')