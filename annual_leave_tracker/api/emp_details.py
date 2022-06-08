import frappe

@frappe.whitelist()
def get_user_name(email):
    employee_name = frappe.db.sql(""" select name from tabEmployee where user_id = '{}' """.format(email),as_dict=True)[0]
    if employee_name:
        return employee_name['name']
