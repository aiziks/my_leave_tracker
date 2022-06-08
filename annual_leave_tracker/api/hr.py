
from __future__ import unicode_literals
import frappe
from frappe import _
from erp_generic.api.utlis import generate_response
from frappe.utils import nowdate, getdate, cint,ceil, today, add_to_date, add_months, date_diff,get_year_start, get_last_day,get_year_ending
from frappe.model.rename_doc import rename_doc
from frappe.core.doctype.data_import.exporter import Exporter
from frappe.core.doctype.data_import.data_import import start_import
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leaves_for_period, get_pending_leaves_for_period, get_leave_allocation_records, get_leave_approver,get_number_of_leave_days
import json, datetime
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
import requests
import calendar
from  .utils import compare_dict
from six import string_types
from frappe.core.utils import ljust_list
from frappe.desk.query_report import get_column_as_dict,normalize_result,add_custom_column_data,get_filtered_data,add_total_row,get_report_doc,get_script
from frappe.core.doctype.data_import.importer import Importer

def get_login_employee():
    user = str(frappe.session.user)
    employees = frappe.get_all(
        "Employee", filters={"user_id": user, "status": "Active"})
    if len(employees) > 0:
        return employees[0].name


@frappe.whitelist()
def get_doc(doctype=None, docname=None, fieldname=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")
    if not docname:
        return generate_response("F", error="'docname' parameter is required")

    try:
        if not frappe.has_permission(doctype, "read"):
            frappe.local.response.http_status_code = 403
            return generate_response("F", "403", error="Access denied")
        if not frappe.db.exists(doctype, docname):
            frappe.local.response.http_status_code = 404
            return generate_response("F", "404", error="{0} '{1}' not exist".format(doctype, docname))
        doc = frappe.get_doc(doctype, docname)
        employee = get_login_employee()
        field = 'employee' if not fieldname else fieldname
        if doc.get(field) != employee:
            frappe.local.response.http_status_code = 403
            return generate_response("F", "403", error="Access denied")
        return generate_response("S", "200", message="Success", data=doc)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_leave_details(employee=None, date=None):
    if not employee:
        return generate_response("F", error="'employee' parameter is required")
    if not date:
        return generate_response("F", error="'date' parameter is required")
    try:
        allocation_records = get_leave_allocation_records(employee, date)
        leave_allocation = {}
        for d in allocation_records:
            allocation = allocation_records.get(d, frappe._dict())

            total_allocated_leaves = frappe.db.get_value('Leave Allocation', {
                'from_date': ('<=', date),
                'to_date': ('>=', date),
                'employee': employee,
                'leave_type': allocation.leave_type,
            }, 'SUM(total_leaves_allocated)') or 0

            remaining_leaves = get_leave_balance_on(employee, d, date, to_date=allocation.to_date,
                                                    consider_all_leaves_in_the_allocation_period=True)

            end_date = allocation.to_date
            leaves_taken = get_leaves_for_period(
                employee, d, allocation.from_date, end_date) * -1
            leaves_pending = get_pending_leaves_for_period(
                employee, d, allocation.from_date, end_date)

            leave_allocation[d] = {
                "total_leaves": total_allocated_leaves,
                "expired_leaves": total_allocated_leaves - (remaining_leaves + leaves_taken),
                "leaves_taken": leaves_taken,
                "pending_leaves": leaves_pending,
                "remaining_leaves": remaining_leaves}

        # is used in set query
        lwps = frappe.get_list("Leave Type", filters={"is_lwp": 1})
        lwps = [lwp.name for lwp in lwps]

        ret = {
            'leave_allocation': leave_allocation,
            'leave_approver': get_leave_approver(employee),
            'lwps': lwps
        }
        generate_response("S", "200", message="Success", data=ret)

    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_training_events(employee=None):
    if not employee:
        return generate_response("F", error="'employee' parameter is required")
    try:
        events = frappe.get_all("Training Event Employee",
                                filters={
                                    "employee": employee,
                                    "docstatus": 1
                                },
                                fields=["parent"]
                                )
        events_list = []
        for event in events:
            if event.parent not in events_list:
                events_list.append(event.parent)

        training_events = frappe.get_all("Training Event",
                                         filters={
                                             "name": ["in", events_list],
                                             "docstatus": 1
                                         },
                                         fields=["*"]
                                         )
        generate_response("S", "200", message="Success", data=training_events)

    except Exception as e:
        return generate_response("F", error=e)



@frappe.whitelist()
def get_leave_policy():

    response = dict()
    leave_policy = frappe.get_list("Leave Policy",fields=["*"])
    leave_policy_assignment = frappe.get_list("Leave Policy Assignment",fields=["*"])

    for l_id in leave_policy:
        n =l_id["name"]
        l_id["total_employee_assigned"] =len([x["leave_policy"] for x in leave_policy_assignment if x["leave_policy"] == n])

    
    response['leave_policy'] = leave_policy
    return generate_response("S", "200", message="Success", data=response)



@frappe.whitelist()
def get_training_results(employee=None):
    if not employee:
        return generate_response("F", error="'employee' parameter is required")
    try:
        results = frappe.get_all("Training Result Employee",
                                 filters={
                                     "employee": employee,
                                     "docstatus": 1
                                 },
                                 fields=[
                                     "parent as name", "parenttype as doctype", "employee", "employee_name", "department", "hours", "grade", "comments"]
                                 )
        for item in results:
            item["training_event"] = frappe.get_value(
                "Training Result", item.name, "training_event")
        generate_response("S", "200", message="Success", data=results)

    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_supervisor_appraisal(docname=None):
    if not docname:
        return generate_response("F", error="'docname' parameter is required")
    try:
        record_doc = frappe.get_doc("HR Supervisor Appraisal Record", docname)
        if record_doc.done:
            return generate_response("F", error="Appraisal '{0}' is done".format(docname))
        doc = frappe.new_doc("HR Supervisor Appraisal")
        template = frappe.get_doc("HR Appraisal Template", record_doc.template)
        for el in template.jobs:
            row = doc.append('jobs', {})
            row.title = el.title
            row.description = el.description
        for el in template.performances:
            row = doc.append('performances', {})
            row.title = el.title
            row.description = el.description
        for el in template.form:
            row = doc.append('form', {})
            row.description = el.description
            row.employee_comment = ""
        doc.supervisor = record_doc.supervisor
        doc.supervisor_name = frappe.get_value(
            "Employee", record_doc.supervisor, "employee_name")
        doc.posting_date = nowdate()
        doc.phase = record_doc.phase
        doc.end_date = record_doc.end_date
        doc.template = record_doc.template
        doc.owner = None

        generate_response("S", "200", message="Success", data=doc)

    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def pending(emp=None):
    if not emp:
        return generate_response("F", error="'Employee ID' parameter is required")
    pend = []
    pending = frappe.get_list("Goals", fields=["*"], filters={'employee':emp, 'status':'Pending Approval', 'stage':'Completed'})
    for v in pending:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    pend.append(pending)

    return generate_response("S", "200", message="Success", data=pend)
    
@frappe.whitelist()
def not_started(emp=None):
    if not emp:
        return generate_response("F", error="'Employee ID' parameter is required")
    doc = []
    not_started = frappe.get_list("Goals", fields=["*"], filters={'employee':emp,'stage':'Not Started'})
    for v in not_started:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(not_started)

    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def in_progress(emp=None):
    if not emp:
        return generate_response("F", error="'Employee ID' parameter is required")
    doc = []
    in_progress = frappe.get_list("Goals", fields=["*"], filters={'employee':emp,'stage':'In Progress'})
    for v in in_progress:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(in_progress)

    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def completed(emp=None):
    if not emp:
        return generate_response("F", error="'Employee ID' parameter is required")
    doc = []
    completed = frappe.get_list("Goals", fields=["*"], filters={'employee':emp, 'status':'Approved', 'stage':'Completed'})
    for v in completed:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(completed)

    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def cancelled(emp=None):
    doc = []
    cancelled = frappe.get_list("Goals", fields=["*"], filters={'employee':emp,'stage':'Cancelled'})
    for v in cancelled:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(cancelled)
    
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def high(emp=None):
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':emp,'status':'High'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def medium(emp=None):
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':emp,'status':'Medium'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def low(emp=None):
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':emp,'status':'Low'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def complete(emp=None):
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':emp,'status':'Complete'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def paused(emp=None):
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':emp,'status':'Paused'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def achievement(emp=None):
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':emp,'mark_as_achievement':1})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def submit_supervisor_appraisal(doc=None, record_name=None):
    if not doc:
        return generate_response("F", error="'doc' parameter is required")
    if not record_name:
        return generate_response("F", error="'record_name' parameter is required")
    try:
        record_doc = frappe.get_doc(
            "HR Supervisor Appraisal Record", record_name)
        if record_doc.done:
            return generate_response("F", error="Appraisal '{0}' is done".format(record_name))
        else:
            cur_doc = frappe.new_doc("HR Supervisor Appraisal")
            cur_doc.flags.ignore_permissions = True
            doc["owner"] = "Administrator"
            cur_doc.update(doc)
            cur_doc.save(ignore_permissions=True)
            cur_doc.submit()
            frappe.db.sql(
                """update `tabHR Supervisor Appraisal` set modified_by = "Administrator" where name = %s""", cur_doc.name)
            record_doc.done = 1
            record_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return generate_response("S", "200", message="{0}: '{1}' {2} Successfully".format(cur_doc.doctype, cur_doc.name, "Created"), data=cur_doc)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def appraisal_completed(emp=None):
    doc = frappe.get_list("Appraisals", fields=["*"], filters={'employee':emp,'status':'Approved'})
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def appraisal_in_progress(emp=None):
    doc = frappe.get_list("Appraisals", fields=["*"], filters={'employee':emp,'status':['!=','Approved']})
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def appraisals(emp=None):
    doc = frappe.get_list("Appraisals", fields=["*"], filters={'employee':emp})
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def get_dept_list():
    department_list=[]
    department_list = frappe.get_list("Department")
    return generate_response("S", "200", message="Success", data=department_list) #Employee Grade

@frappe.whitelist()
def get_grade_list():
    grade_list=[]
    grade_list = frappe.get_list("Employee Grade")
    return generate_response("S", "200", message="Success", data=grade_list)

@frappe.whitelist()
def get_branch_list():
    branch_list=[]
    branch_list = frappe.get_list("Branch")
    return generate_response("S", "200", message="Success", data=branch_list)

@frappe.whitelist()
def get_designation_list():
    d_list = frappe.get_list("Designation")
    return generate_response("S", "200", message="Success", data=d_list)


@frappe.whitelist()
def get_employee_type_list():
    type_list=[]
    type_list = frappe.get_list("Employment Type")
    return generate_response("S", "200", message="Success", data=type_list)

@frappe.whitelist()
def get_employee_doc(docname=None):
    if not docname:
        return generate_response("F", error="'docname' parameter is required")

    if not frappe.has_permission("Employee", "read"):
        frappe.local.response.http_status_code = 403
        return generate_response("F", "403", error="Access denied")

    if not frappe.db.exists("Employee", docname):
        frappe.local.response.http_status_code = 404
        return generate_response(
            "F", "404", error="{0} '{1}' not exist".format("Employee", docname)
        )
    doc = frappe.get_doc("Employee", docname)
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def sort_employee(order_by=None):
    doc = frappe.get_all("Employee",fields=["*"], order_by=order_by)
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def appraisal_dashboard():
    doc = {}
    y = get_year_start(nowdate()).strftime('%Y-%m-%d')
    x = get_year_ending(y)
    total_appraisal = len(frappe.get_all("Appraisals", filters={'creation':['between',[y,x]]}))
    completed = len(frappe.get_all("Appraisals", filters={'status':'Approved','creation':['between',[y,x]]}))
    not_completed = len(frappe.get_all("Appraisals", filters={'status':['!=','Approved'],'creation':['between',[y,x]]}))
    doc['total_appraisal'] = total_appraisal
    doc['completed'] = completed
    doc['not_completed'] = not_completed
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def get_appraisal(
    fields=None,
    order_by=None,
    group_by=None,
    start=None,
    page_length=None,
    template=None,
    employee=None,
    start_date=None,
    end_date=None,
    stage=None,
    branch=None,
    department=None,
    
):
    
    filters = {}
    try:
        if not fields:
            fields = []
        if template:
            filters["template"] = template
        if employee:
            filters["employee"] = employee
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if stage:
            filters["stage"] = stage
        if branch:
            filters["branch"] = branch
        if department:
            filters["department"] = department

        data = frappe.get_all("Appraisals", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
            
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_list(
    fields=None,
    # filters=None,
    order_by=None,
    group_by=None,
    #start=None,
    page=None,
    #page_length=None,
    employee_type=None,
    branch=None,
    grade=None,
    department=None,
    
):
    # if not doctype:
    #     return generate_response("F", error="'doctype' parameter is required")
    filters = {}
    print(order_by)
    try:
        if not fields:
            fields = []
        if employee_type:
            filters["employment_type"] = employee_type
        if branch:
            filters["branch"] = branch
        if grade:
            filters["grade"] = grade
        if department:
            filters["department"] = department
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 20
            current_page = page

        doc_length = len(frappe.get_all("Employee", filters, order_by=order_by))
        total_pages = ceil(doc_length / 20)
        page_length = 20

        data = frappe.get_all(
            "Employee", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length
        )
        for v in data:
            doc = frappe.get_list("Employee", fields=["*"], filters={'employee':v.name})
            for i in doc:
                items = len({key:value for key,value in i.items()})
                completed = len({key:value for key,value in i.items() if value != None and value != ""})
                per_completed = round((completed / items) * 100 , 2)
                v['completion_rate'] = per_completed

        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
            
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)



@frappe.whitelist()
def update_employee_record(doc_name, emp):
    try:
        if not doc_name:
            return generate_response(
                "F", "400", error="'doc_name' parameter is required"
                )
        if not emp:
            return generate_response(
                "F", "400", error="'emp' parameter is required"
                )
        if frappe.db.exists("Employee",doc_name):
            cur_doc = frappe.get_doc("Employee",doc_name)
            # emp = json.loads(emp)
            cur_doc = cur_doc.as_dict()
            er_child_tb={}
            for doc_field, doc_value in emp.items():
                if doc_field in cur_doc.keys():
                    continue
                else:
                    return generate_response(
                    "F", "400", error="'{}' field name  ".format(doc_field)
                    )
            if not frappe.db.count('Employee Record Pending Approval',{'name': doc_name}):
                
                employee_record_doc = frappe.get_doc({
                        'doctype': 'Employee Record Pending Approval',
                        'er_employee_id': doc_name
                        })
                # employee_record_doc = frappe.new_doc("Employee Record Pending Approval")
                # employee_record_doc.name=doc_name
                # employee_record_doc.er_employee_id = doc_name
                employee_record_doc.insert(ignore_permissions=True)
                
                # employee_record_doc = frappe.db.sql("""insert into`tabEmployee Record Pending Approval` 
                # (name, er_employee_child) values(%s,%s)""", (doc_name,doc_name),as_dict=True)
                # employee_record_doc = frappe.get_doc("Employee Record Pending Approval", doc_name)
                # for i in range(len(emp.keys())):
                print("\nTESTSTETSTSTS\n")
                print(emp)

                print("\nTESTSTETSTSTS\n")

                args = {
                    "email_employee_name" : cur_doc["employee_name"],
                    "email_employee_id" : cur_doc["name"]
                }
                
                for k, v in emp.items():
                    employee_record_doc.append('er_employee_child',{
                        "erc_field_name":k,
                        "erc_field_value":v
                    })
                employee_record_doc.save()
                frappe.db.commit()                
                # employee_record_doc.save(ignore_permissions=True) 
                print("\nTESTSTETSTSTSxxxxxxxxxxxxxxxxxx\n")
                  
                user_email = frappe.db.sql("""select * from `tabHas Role` 
                where parenttype = 'User' and parent <> 'Administrator'
                and role = %s""", ("HR Manager",),as_dict=True)
                print(user_email)
                recipients = []

                for i in range(len(user_email)):
                    recipients.append(user_email[i].parent)
                # email_template = frappe.get_doc("Email Template", "Employee Profile Update")
                # message = frappe.render_template(email_template.response)
                # frappe.errprint('Notifying HR Manager: '+ json.dumps(recipients))

                frappe.sendmail(recipients=recipients, subject="Employee Profile Update Alert",args=args, template='notification_hr_employee_update', header=_("Employee Profile Update Alert"))
                print("\n  test\n")
                return generate_response("S", "200", message="Success", data="Notifying HR Manager About Update")
            else:
                return generate_response(
                "F", "400", error="'{}' Employee have existing record awaiting approval".format(doc_name)
                )
    except:
        return generate_response(
                "F", "400", error="Error not exist"
            )


@frappe.whitelist()
def approve_update_employee(doc_name, rec_update=None):
    """
    doc_name : document name
    rec_update = "{'first_name':'update value'}"
    Proper checks are performed before inserting into 'Employee Record Pending Approval'
    """
    if not rec_update:
        return generate_response(
                "F", "400", error=f"{rec_update} parram is empty"
            )
    try:
        rec_update = json.loads(rec_update)
        emp_rec = frappe.get_doc("Employee", doc_name)
        # emp_data= emp_rec.as_dict()
        for k , v in rec_update.items():
            emp_rec.set(k,v)
        emp_rec.save(ignore_permissions=True)
        frappe.db.commit()
            # emp_rec.db_Set(k , v,commit=True)
        frappe.sendmail(recipients=[emp_rec.user_id], subject="Update on record approval",template='notify_hr_employee_profile_update', header=_("Employee Profile Update Alert"))
        rec_app=frappe.get_doc('Employee Record Pending Approval',doc_name)
        print(rec_app)
        rec_app.delete(ignore_permissions=True)
        frappe.db.commit()
        return generate_response("S", "200", message="Success", data="Data Update Succesful")
    except Exception as e:
        return generate_response("F", "400", error=f"{e} ---Error Updating Employee {doc_name} record")


@frappe.whitelist()
def update_doc(doc=None, doctype=None, docname=None, action="Save"):
    try:
        if not doctype:
            frappe.throw("'doctype' parameter is required")
        if not doc:
            frappe.throw("'doc' parameter is required")
        cur_doc = None
        status = None
        if not doc.get("doctype") and doctype:
            doc["doctype"] = doctype
        if not doc.get("name") and docname:
            doc["name"] = docname
        if frappe.db.exists(doc.get("doctype"), doc.get("name")):
            cur_doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))
            status = "Updated"
        else:
            doc["name"] = ""
            cur_doc = frappe.new_doc(doc.get("doctype"))
            status = "Created"
        if not cur_doc:
            return generate_response("F")
        cur_doc.flags.ignore_permissions = True
        cur_doc.update(doc)
        cur_doc.save(ignore_permissions=True)
        if action == "Submit":
            cur_doc.submit()

        return generate_response(
            "S",
            "200",
            message="{0}: '{1}' {2} Successfully".format(
                cur_doc.doctype, cur_doc.name, status
            ),
            data=cur_doc,
        )
    except Exception as e:
        return generate_response("F", error=e)


	# 	frappe.errprint('Updating existing record done');

	# 	user_email = frappe.db.sql("""select * from `tabHas Role` 
	# 		where parenttype = 'User' and parent <> 'Administrator'
	# 		and role = %s""", ("HR Manager",),as_dict=True);
		
	# 	# frappe.errprint('Retrieve HR Manager email: '+ json.dumps(user_email, indent=4, sort_keys=True, default=str))

	# 	recipients = [];

	# 	for i in range(len(user_email)):
	# 		recipients.append(user_email[i].parent);

	# 	doc = frappe.get_doc('Employee', doc_name);

	# 	args = {
	# 		'email_employee_name':doc.first_name,
	# 		'email_employee_id':doc.name,
	# 		'link': frappe.utils.get_url()+ doc.get_url()
	# 	}

	# 	# sender      	    = dict()
	# 	# sender['email']     = frappe.get_doc('User', frappe.session.user).email
	# 	# sender['full_name'] = frappe.utils.get_fullname(sender['email'])

	# 	# Employee Profile Update

	# 	# template = frappe.db.get_single_value('HR Settings', 'leave_status_notification_template')
	# 	# if not template:
	# 	# 	frappe.msgprint(_("Please set default template for Leave Status Notification in HR Settings."))
	# 	# 	return
	# 	email_template = frappe.get_doc("Email Template", "Employee Profile Update");
	# 	message = frappe.render_template(email_template.response, args);

	# 	frappe.errprint('Notifying HR Manager: '+ json.dumps(recipients));

	# 	# try:
	# 	# 	frappe.sendmail(
	# 	# 		recipients = recipients,
	# 	# 		subject = email_template.subject,
	# 	# 		message = message,
	# 	# 		)
	# 	# 	# frappe.msgprint(_("Email sent to {0}").format(contact))
	# 	# except frappe.OutgoingEmailError:
	# 	# 	pass

	# 	frappe.sendmail(recipients=recipients, subject=email_template.subject,
	# 		template='notification_hr_employee_update', args=args, header=[email_template.subject, "green"])

	# return "done";



@frappe.whitelist()
def update_employee_rec_v2(emp):
    try:
        if not emp:
            return generate_response(
                "F", "400", error="'emp' parameter is required"
                )
        
        # emp = json.loads(emp)
        if frappe.db.exists("Employee",emp["employee"]):
            cur_doc = frappe.get_doc("Employee",emp["employee"])
            try:
                doc_name = emp["employee"]
                print(type(cur_doc))
                cur_doc = cur_doc.as_dict()
                diff = compare_dict(emp, cur_doc)
                print(diff)
                if not frappe.db.count('Employee Record Pending Approval',{'name': doc_name}):
                
                    employee_record_doc = frappe.get_doc({
                            'doctype': 'Employee Record Pending Approval',
                            'er_employee_id': doc_name
                            })
                    employee_record_doc.insert(ignore_permissions=True)
                    print(diff)
                    args = {
                        "email_employee_name" : cur_doc["employee_name"],
                        "email_employee_id" : cur_doc["name"]
                    }                    
                    for k, v in diff.items():
                        print(k,v)
                        employee_record_doc.append('er_employee_child',{
                            "erc_field_name":k,
                            "erc_field_value":v["new_value"]
                        })
                    employee_record_doc.save()
                    frappe.db.commit()
                    
                    user_email = frappe.db.sql("""select * from `tabHas Role` 
                    where parenttype = 'User' and parent <> 'Administrator'
                    and role = %s""", ("HR Manager",),as_dict=True)
                    recipients = []

                    for i in range(len(user_email)):
                        recipients.append(user_email[i].parent)
                    # email_template = frappe.get_doc("Email Template", "Employee Profile Update")
                    # message = frappe.render_template(email_template.response)
                    # frappe.errprint('Notifying HR Manager: '+ json.dumps(recipients))
                    print(recipients)
                    frappe.sendmail(recipients=recipients, subject=frappe._("Employee Profile Update Alert"),args=args, template="notify_hr_employee_profile_update", header=_("Employee Profile Update Alert"))
                    print("\n  test\n")
                    return generate_response("S", "200", message="Success", data="Notifying HR Manager About Update")
                else:
                    return generate_response(
                "F", "400", error="'{}' Employee have existing record awaiting approval".format(doc_name)
                )
            except Exception as e:
                print(e)
        else:
            return generate_response(
                "F", "400", error="'{}' Employee Doesn't Exist".format(emp["employee"])
                )
    except Exception as e:
        return generate_response(
                "F", "400", error=f"{e}"
            )

""""""""""""""""""""""""
"""Manager View API"""
""""""""""""""""""""""""

@frappe.whitelist()
def get_employee_total_dept(dept_name):
    """
    deptName - name of department
    """
    y = get_year_start(nowdate()).strftime('%Y-%m-%d')
    x = get_year_ending(y)
    
    if not dept_name:
        return generate_response("F", error="'dept_name' parameter is required")

    if not frappe.has_permission("Employee", "read"):
        frappe.local.response.http_status_code = 403
        return generate_response("F", "403", error="Access denied")
    
    data = {}
    user = frappe.session.user
    name= frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    
    employee_dept_count = 0
    if frappe.db.exists("Department", dept_name):
        data["department"] = dept_name
        data["employee_total_in_dept"] = len(frappe.get_all("Employee", filters={'department':dept_name}))
        data["employee_total_new"] = len(frappe.get_all("Employee", filters={'department':dept_name,'status':'Active', 'date_of_joining':['between', [x,y]]}))
        data["total_exit_dept"] = len(frappe.get_all("Employee", filters={'department':dept_name, 'status':'Left'}))
        data["employee_count_report"] = len(frappe.get_all(doctype='Employee', filters={'reports_to':name,'status':'Active'}))
        return generate_response("S", "200", message="Success", data=data)
    else:
        return generate_response(
            "F",
            "404",
            message="Department '{}' doesn't exist".format(
                dept_name),
        )



@frappe.whitelist()
def bar_dashboard_hr(dept_name):
    present_chart = []
    absent_chart = []
    leave_chart = []
    for i in range(0,12):
        y_start = get_year_start(nowdate()).strftime('%Y-%m-%d')
        month_start = add_months(y_start,i)
        month_end = get_last_day(month_start).strftime('%Y-%m-%d')

        present = len(frappe.get_all('Attendance', filters={'Status': 'Present', 'department':dept_name,'attendance_date' : ['between', [month_start, month_end]]}))
        present_chart.append(present)

        absent = len(frappe.get_all('Attendance', filters={'Status': 'Absent','department':dept_name,'attendance_date' : ['between', [month_start, month_end]]}))
        absent_chart.append(absent)

        leave = len(frappe.get_all('Attendance', filters={'Status': 'On Leave','department':dept_name,'attendance_date' : ['between', [month_start, month_end]]}))
        leave_chart.append(leave)

        bar_chart = [list(x) for x in zip(present_chart, absent_chart, leave_chart)]

    return generate_response("S", "200", message="Success", data=bar_chart)


@frappe.whitelist()
def pie_dashboard_mgr(dept_name):
    pie_chart = []
    male = len(frappe.get_all("Employee", filters={'Status':'Active','Gender':'Male','department':dept_name}))
    female = len(frappe.get_all("Employee", filters={'Status':'Active', 'Gender':'Female','department':dept_name}))
    male_chart = {'title': 'Male', 'value': male}
    pie_chart.append(male_chart)
    female_chart = {'title': 'Female', 'value': female}
    pie_chart.append(female_chart)
    #pie_chart['Female'] = female
    return generate_response("S", "200", message="Success", data=pie_chart)


@frappe.whitelist()
def holiday_list(start_date, end_date, days):
    start_date, end_date = getdate(start_date), getdate(end_date)

    from dateutil import relativedelta
    
    days = json.loads(days)
    data = {}
    existing_date_list = []
    for i, day in enumerate(days):
        date_list = []
        weekday = getattr(calendar, day.upper())
        reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

        while reference_date <= end_date:
            if reference_date:
                date_list.append(reference_date)
            reference_date += timedelta(days=7)
        i +=1
        
        data[day] = date_list
    
    return generate_response("S", "200", message="Success", data=data)

@frappe.whitelist()
def leave_days(
    employee,
    leave_type,
    from_date,
    to_date,
    half_day = None
):
    try:
        number = get_number_of_leave_days(
            employee, leave_type, from_date, to_date, half_day)
        return generate_response("S", "200", message="Success", data=number)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def get_salary_component(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    type=None,
    status=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if type:
            filters["type"] = type
        if status:
            if status == "Enabled":
                filters["disabled"] = 0
            else:
                filters["disabled"] = 1
        if page:page = cint(page)
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Salary Component", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10
        
        data = frappe.get_list("Salary Component", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        for i in data:
            if i.disabled == 0:
                i["status"] = "Enabled"
            else:
                i["status"] = "Disabled"
        
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def get_payroll_entry(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    company=None,
    branch=None,
    start_date=None,
    end_date=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Payroll Entry", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10
        
        data = frappe.get_list("Payroll Entry", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def get_salary_structure(
    page=None
):
    try:
        if page:page = cint(page)    
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Salary Structure"))
        total_pages = ceil(doc_length / 10)
        page_length = 10
        data = frappe.get_list("Salary Structure",["*"],filters={'docstatus':1},start=start, page_length=page_length)
        for i in data:
            assigned = len(frappe.get_list("Salary Structure Assignment",filters={"docstatus": 1,"salary_structure":i.name}))
            i["employee_assigned"] = assigned
        
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def get_salary_slip(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    company=None,
    branch=None,
    department=None,
    salary_structure=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        if department:
            filters["department"] = department
        if salary_structure:
            filters["salary_structure"] = salary_structure
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Salary Slip", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10
        
        data = frappe.get_list("Salary Slip", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def rename(doctype=None, old=None, new=None):
    response = rename_doc(doctype,old,new)
    return generate_response("S", "200", message="Success", data=response)


@frappe.whitelist()
def download_template(
	doctype, export_fields=None, export_records=None, export_filters=None, file_type="CSV"
):
	export_fields = frappe.parse_json(export_fields)
	export_filters = frappe.parse_json(export_filters)
	export_data = export_records != "blank_template"

	e = Exporter(
		doctype,
		export_fields=export_fields,
		export_data=export_data,
		export_filters=export_filters,
		file_type=file_type,
		export_page_length=5 if export_records == "5_records" else None,
	)
	e.build_response()

@frappe.whitelist()
def form_start_import(data_import):
    data = frappe.get_doc("Data Import", data_import).start_import()
    return generate_response("S", "200", message="Success", data=data)

@frappe.whitelist()
def start_import(data_import):
    data_import = frappe.get_doc("Data Import", data_import)
    try:
        i = Importer(data_import.reference_doctype, data_import=data_import)
        i.import_data()
        return generate_response("S", "200", message="Success")
    except Exception:
        frappe.db.rollback()
        data_import.db_set("status", "Error")
        frappe.log_error(title=data_import.name)
    finally:
        frappe.flags.in_import = False

    frappe.publish_realtime("data_import_refresh", {"data_import": data_import.name})


@frappe.whitelist()
def payroll_dashboard():
    try:
        data = dict()
        doc = []
        y = get_year_start(nowdate()).strftime('%Y-%m-%d')
        x = get_year_ending(y)
        active_salary_component = len(frappe.get_all("Salary Component",filters={'disabled':0,'creation':['between',[y,x]]}))
        pay_slip = len(frappe.get_all("Salary Slip", filters={'status':'Submitted'}))
        salary_structure = frappe.get_all("Salary Structure Assignment",fields=['salary_structure'],filters={'creation':['between',[y,x]]},as_list=True)
        for i in salary_structure:
            doc.extend(i)
        doc = {i:doc.count(i) for i in doc}
        
        data["active_salary_component"] = active_salary_component
        data["pay_slip"] = pay_slip
        data["salary_structure"] = doc
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)




@frappe.whitelist()
def generate_report_result(
    report_name,
    from_date=None,
    to_date=None,
    company=None,
    employee=None,
    currency=None,
    docstatus=None,
    user=None,
    custom_columns=None
    ):
    try:
        report = get_report_doc(report_name)
        user = user or frappe.session.user
        filters = {}
        
        filters["from_date"]= from_date if from_date else None
        filters["to_date"]= to_date if to_date else None
        filters["company"]= company if company else None
        filters["employee"]= employee if employee else None
        filters["currency"]= currency if currency else None
        filters["docstatus"]= docstatus if docstatus else None


        # if filters and isinstance(filters, string_types):
        #     filters = json.loads(filters)

        res = []

        if report.report_type == "Query Report":
            res = report.execute_query_report(filters)

        elif report.report_type == "Script Report":
            res = report.execute_script_report(filters)

        columns, result, message, chart, report_summary, skip_total_row = ljust_list(res, 6)
        columns = [get_column_as_dict(col) for col in columns]
        report_column_names = [col["fieldname"] for col in columns]

        # convert to list of dicts
        result = normalize_result(result, columns)

        if report.custom_columns:
            # saved columns (with custom columns / with different column order)
            columns = report.custom_columns

        # unsaved custom_columns
        if custom_columns:
            for custom_column in custom_columns:
                columns.insert(custom_column["insert_after_index"] + 1, custom_column)

        # all columns which are not in original report
        report_custom_columns = [column for column in columns if column["fieldname"] not in report_column_names]

        if report_custom_columns:
            result = add_custom_column_data(report_custom_columns, result)

        if result:
            result = get_filtered_data(report.ref_doctype, columns, result, user)
        
        if cint(report.add_total_row) and result and not skip_total_row:
            result = add_total_row(result, columns)
        
        for ind,rec in enumerate(result):
            if isinstance(rec, dict):
                result[ind]["month_13"]=result[ind].pop("13th_month")
                result[ind]["month_13_bonus"]=result[ind].pop("13th_month_bonus")

        data = {
            "result": result,
            "columns": columns
        }
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_onboarding(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    department=None,
    designation=None,
    status=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if designation:
            filters["designation"] = designation
        if status:
            filters["status"] = status
        if department:
            filters["department"] = department
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Onboarding", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10

        data = frappe.get_list("Onboarding", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_onboarding_template(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    department=None,
    designation=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if designation:
            filters["designation"] = designation
        if department:
            filters["department"] = department
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Onboarding Template", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10

        data = frappe.get_list("Onboarding Template", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_offboarding(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    department=None,
    designation=None,
    status=None,
    type=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if designation:
            filters["designation"] = designation
        if status:
            filters["status"] = status
        if department:
            filters["department"] = department
        if type:
            filters["offboarding_type"] = type
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Offboarding", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10
        data = frappe.get_list("Offboarding", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)

        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_offboarding_template(
    fields=None,
    order_by=None,
    group_by=None,
    page=None,
    department=None,
    designation=None
):
    filters = {}
    try:
        if not fields:
            fields = []
        if designation:
            filters["designation"] = designation
        if department:
            filters["department"] = department
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_list("Offboarding", filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10

        data = frappe.get_list("Offboarding Template", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def lifecycle_dashboard():
    data = dict()
    on_doc = []
    off_doc = []
    y = get_year_start(nowdate()).strftime('%Y-%m-%d')
    x = get_year_ending(y)
    total_onboarded = len(frappe.get_all("Onboarding", filters={"status":"Completed",'creation':['between',[y,x]]}))
    total_promotion = len(frappe.get_all("Employee Promotion", filters={'creation':['between',[y,x]]}))
    total_offboarded = len(frappe.get_all("Offboarding", filters={"status":"Completed",'creation':['between',[y,x]]}))
    total_transferred = len(frappe.get_all("Employee Transfer", filters={'creation':['between',[y,x]]}))
    
    data['total_onboarded'] = total_onboarded
    data['total_offboarded'] = total_offboarded
    data['total_promotion'] = total_promotion
    data['total_transferred'] = total_transferred

    onboarded = frappe.get_all("Onboarding", fields=["department"],filters={"status":"Completed",'creation':['between',[y,x]]},as_list=True)
    for i in onboarded:
        on_doc.extend(i)
    on_doc = {i:on_doc.count(i) for i in on_doc}

    offboarded = frappe.get_all("Offboarding", fields=["department"],filters={"status":"Completed",'creation':['between',[y,x]]},as_list=True)
    for i in offboarded:
        off_doc.extend(i)
    off_doc = {i:off_doc.count(i) for i in off_doc}

    data['onboarded'] = on_doc
    data['offboarded'] = off_doc
    return generate_response("S", "200", message="Success", data=data)

@frappe.whitelist()
def employee_dashboard():
    try:
        data = {}
        dept_list = []
        type_list = []
        total_department = len(frappe.get_all("Department", filters={"name":["!=","All Departments"]}))
        total_designation = len(frappe.get_all("Designation"))
        total_branch = len(frappe.get_all("Branch"))
        total_emp_type = len(frappe.get_all("Employment Type",as_list=True))
        employee_total = len(frappe.get_all("Employee", filters={'status':'Active'}))
        department = frappe.get_all("Employee",fields=["department"], as_list=True)
        for i in department:
            dept_list.extend(i)
        dept = {i:dept_list.count(i) for i in dept_list}
        emp_type = frappe.get_all("Employee",fields=["employment_type"], as_list=True)
        for j in emp_type:
            type_list.extend(j)
        type = {i:type_list.count(i) for i in type_list}
        
        data["total_department"] = total_department
        data["total_designation"] = total_designation
        data["total_branch"] = total_branch
        data["total_emp_type"] = total_emp_type
        data["total_employee"] = employee_total
        data["department"] = dept
        data["employment_type"] = type
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def report_dashboard(
):
    employee_reports = frappe.get_list("Report",
        filters=[["ref_doctype","=","Employee"],
        ["name","not like","%leave%"],["disabled","=",0]])
    emp_total = len(employee_reports)    
    
    leave_reports = frappe.get_list("Report",
        filters=[["name","like","%leave%"],["disabled","=",0]])
    leave_total = len(leave_reports)

    payroll_reports = frappe.get_list("Report",
        filters=[["ref_doctype","=","Salary Slip"],["disabled","=",0]])
    payroll_total = len(payroll_reports)
    
    performance_reports = frappe.get_list("Report",
        filters=[["ref_doctype","=","Appraisals"],["disabled","=",0]])
    perf_total = len(performance_reports)
    
    lifecycle_reports = frappe.get_list("Report",
        filters=[["ref_doctype","in",["Onboarding",
        "Employee Transfer","Employee Promotion","Offboarding"]],
        ["disabled","=",0]])
    life_total = len(lifecycle_reports)

    reports = {
        'employee': {
            'total': emp_total,
            'icon': get_icon("Employee.png")
            },
        'leave': {
            'total':leave_total,
            'icon':get_icon("Leave.png")
            },
        'payroll': {
            'total':payroll_total,
            'icon':get_icon("Payroll.png")
            },
        'performance': {
            'total':perf_total,
            'icon':get_icon("Performance.png")
            },
        'lifecycle': {
            'total':life_total,
            'icon':get_icon("Lifecycle.png")
            }
    }
    
    total = (emp_total+leave_total+
        payroll_total+perf_total+life_total)

    data ={
        'total_reports':total,
        'reports':reports
    }
    return generate_response("S", "200", message="Success", data=data)

def get_icon(file_name):
    icon = frappe.db.get_value("File",{'file_name':file_name},'file_url')
    return icon

@frappe.whitelist()
def get_reports(
    order_by=None,
    page=None
):

    reports = ["Employee","Salary Slip","Appraisals","Onboarding",
        "Employee Transfer","Employee Promotion","Offboarding"]

    filters = [["ref_doctype","in",reports],["disabled","=",0]]
    
    if page:page = cint(page)        
    if not page or page == 1:
        start = 0
        current_page = 1
    else:
        start = (page - 1) * 10
        current_page = page

    doc_length = len(frappe.get_all("Report", filters, order_by=order_by))
    total_pages = ceil(doc_length / 10)
    page_length = 10

    data = frappe.get_all(
            "Report",filters,order_by=order_by,
            start=start, page_length=page_length
        )
    resp = {
        'total_pages':total_pages,
        'current_page':current_page,
        'data':data
    }
    return generate_response("S", "200", message="Success", data=resp)

@frappe.whitelist()
def report_list(
    module=None,
    page=None,
    order_by=None
):
    if not module:
        return generate_response("F", error="'module' parameter is required")
    if module == "Employee":
        filters = [["ref_doctype","=","Employee"],
            ["name","not like","%leave%"],["disabled","=",0]]
    elif module == "Leave":
        filters = [["name","like","%leave%"],["disabled","=",0]]
    elif module == "Payroll":
        filters=[["ref_doctype","=","Salary Slip"],["disabled","=",0]]
    elif module == "Performance":
        filters=[["ref_doctype","=","Appraisals"],["disabled","=",0]]
    elif module == "Lifecycle":
        filters=[["disabled","=",0],["ref_doctype","in",["Onboarding",
            "Employee Transfer","Employee Promotion","Offboarding"]]]
    else:
        return generate_response("F", error="'module' parameter is incorrect")

    if page:page = cint(page)        
    if not page or page == 1:
        start = 0
        current_page = 1
    else:
        start = (page - 1) * 10
        current_page = page

    doc_length = len(frappe.get_all("Report",
        filters, order_by=order_by))
    total_pages = ceil(doc_length / 10)
    page_length = 10

    data = frappe.get_all(
            "Report",filters,order_by=order_by,
            start=start, page_length=page_length
        )
    resp = {
        'total_pages':total_pages,
        'current_page':current_page,
        'data':data
    }
    return generate_response("S", "200", message="Success", data=resp)
    
@frappe.whitelist()
def get_report_script(report=None):
    doc = get_script(report)
    
    return {
        'script': doc.get('script')
    }

@frappe.whitelist()
def get_project():
    """
    Get Project report list
    """
    data ={}
    if not frappe.has_permission("Project", "read"):
        frappe.local.response.http_status_code = 403
        return generate_response("F", "403", error="Access denied")
    project_list= frappe.get_list("Project",['*'])
    data["project_list"] = project_list
    return generate_response("S", "200", message="Success", data=data)

    
@frappe.whitelist()
def create_project(project_name,expected_start_date,expected_end_date):
    if not frappe.has_permission("Project", "create"):
        frappe.local.response.http_status_code = 403
        return generate_response("F", "403", error="Access denied")
    doc = frappe.get_doc({
    'doctype': 'Project',
    'project_name': project_name,
    'expected_start_date': expected_start_date,
    'expected_end_date':expected_end_date
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return generate_response("S", "200", message="Success")