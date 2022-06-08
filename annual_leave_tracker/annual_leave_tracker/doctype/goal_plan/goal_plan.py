# Copyright (c) 2021, SWIFTA SERVICES LIMITED and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class GoalPlan(Document):
	def validate(self):
		if not self.status:
			self.status = "Draft"

	def on_submit(self):
		frappe.db.set(self, 'status', 'Submitted')

	def on_cancel(self):
		frappe.db.set(self, 'status', 'Cancelled')
