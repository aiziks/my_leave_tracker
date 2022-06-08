# Copyright (c) 2022, SWIFTA SERVICES LIMITED and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate

from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class Onboarding(Document):
	def validate(self):
		self.calculate()
		self.set_status()

	def calculate(self):
		i = 0
		for d in self.get('task'):
			if d.progress == "Completed":
				i += 1
		self.completed = i

		total = len(self.get('task'))
		self.total = total

	def set_status(self):
		if self.total != 0 and self.total == self.completed:
			self.status = "Completed"
		elif self.completed != 0 and self.completed < self.total:
			self.status = "In Process"
		else:
			self.status = "Pending"

@frappe.whitelist()
def onboarding_template(source_name, target_doc=None):
	target_doc = get_mapped_doc("Onboarding Template", source_name, {
		"Onboarding Template": {
			"doctype": "Onboarding",
		},
		"Onboarding Template Activity": {
			"doctype": "Onboarding Activity",
		}
	}, target_doc)

	return target_doc
