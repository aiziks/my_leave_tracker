from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.auth import LoginManager
import uuid
import json
from frappe.utils.pdf import get_pdf
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import nowdate, getdate, cint, today, add_to_date, add_months, date_diff, get_year_start, get_last_day,get_year_ending, add_years
from erpnext.hr.doctype.holiday_list.holiday_list import get_events
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import requests
import babel.dates
from erp_generic.api.utlis import (
    xml_to_dic,
    send_welcome_mail_to_user,
    reset_password,
    to_base64,
    add_file,
    delete_file,
    generate_response,
    portal_settings,
)



@frappe.whitelist()
def others_in_dept():        
    user = frappe.session.user
    
    if user == "Administrator":
        return "not allowed"

    dpt = frappe.db.get_value("Employee",{'user_id': user}, ['department'])
    doc = frappe.get_all('Employee', fields=["*"],filters={'department':dpt})
    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def employee_dashboards():
    dashboard = {}
    user = frappe.session.user
    name,dpt = frappe.db.get_value("Employee",{'user_id': user}, ['employee','department'])
    
    total_in_dept = len(frappe.get_all('Employee',filters={'department':dpt, 'status':'Active'}))
    dashboard['total_in_department'] = total_in_dept

    active_goal_plans = len(frappe.get_all("Goals", filters={'employee':name, 'stage':['!=','Completed']}))
    dashboard['active_goal_plans'] = active_goal_plans

    active_activities = len(frappe.get_all("Activities", filters={'employee':name, 'status':['!=','Complete']}))
    dashboard['active_activities'] = active_activities

    y_start = get_year_start(nowdate()).strftime('%Y-%m-%d')
    x = add_years(y_start,-1)
    y = get_year_ending(x)
    achievements = len(frappe.get_all("Activities", filters={"mark_as_achievement": 1, 'creation':['between',[x,y]]}))
    dashboard['achievements'] = achievements
    
    return generate_response("S", "200", message="Success", data=dashboard)


@frappe.whitelist()
def upcoming_task():
    if not frappe.has_permission('Task', "read"):
        return "No Task"
    
    upcoming_task = frappe.get_list('Task',fields=['*'],filters=[['status','in',['Open','Working','Pending Review','Overdue','Template']]], order_by='exp_end_date')[0]
    
    return generate_response("S", "200", message="Success", data=upcoming_task)

@frappe.whitelist()
def employee_bar():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    present_chart = []
    absent_chart = []
    leave_chart = []
    for i in range(0,12):
        y_start = get_year_start(nowdate()).strftime('%Y-%m-%d')
        month_start = add_months(y_start,i)
        month_end = get_last_day(month_start).strftime('%Y-%m-%d')
        
        present = len(frappe.get_all('Attendance', filters={'Status':'Present', 'employee':name, 'attendance_date': ['between', [month_start,month_end]]}))
        present_chart.append(present)

        absent = len(frappe.db.get_all('Attendance', filters={'Status': 'Absent', 'employee':name, 'attendance_date' : ['between', [month_start, month_end]]}))
        absent_chart.append(absent)

        leave = len(frappe.db.get_all('Attendance', filters={'Status': 'On Leave', 'employee':name, 'attendance_date' : ['between', [month_start, month_end]]}))
        leave_chart.append(leave)

        bar_chart = [list(x) for x in zip(present_chart, absent_chart, leave_chart)]
    return generate_response("S", "200", message="Success", data=bar_chart)


@frappe.whitelist()
def employee_pie():
    user = frappe.session.user
    dpt = frappe.db.get_value("Employee",{'user_id': user}, ['department'])

    pie_chart = []
    male = len(frappe.get_all("Employee", filters={'status':'Active','gender':'Male','department':dpt}))
    female = len(frappe.get_all("Employee", filters={'status':'Active', 'gender':'Female', 'department':dpt}))
    male_chart = {'title': 'Male', 'value': male}
    pie_chart.append(male_chart)
    female_chart = {'title': 'Female', 'value': female}
    pie_chart.append(female_chart)
    return generate_response("S", "200", message="Success", data=pie_chart)

@frappe.whitelist()
def user_designation():
    user = frappe.session.user
    doc = {}
    desig = frappe.db.get_value("Employee",{'user_id': user}, ['designation'])
    return generate_response("S", "200", message="Success", data=desig)

@frappe.whitelist()
def user_desig():
    user = frappe.session.user
    doc =[]
    desig = frappe.db.get_value("Employee",{'user_id': user}, ['designation'])
    doc.append(desig)
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def get_appraisal_template():
    user = frappe.session.user
    category = frappe.db.get_value("Employee",{'user_id': user}, ['category'])
    template_name = frappe.db.get_value("Appraisals Template", {"specify_employee_category":category},['name'])
    template = frappe.get_doc("Appraisals Template", template_name)
    return generate_response("S", "200", message="Success", data=template)

@frappe.whitelist()
def get_leave_overview():
    user = frappe.session.user
    dpt = frappe.db.get_value("Employee",{'user_id': user}, ['department'])
    
    response = dict()
    today =  datetime.now().strftime('%Y-%m-%d')
    y = get_year_start(nowdate()).strftime('%Y-%m-%d')
    x = get_year_ending(y)
    leaves = frappe.get_list("Leave Application", fields=["*"], filters={'creation':['between',[y,x]]})

    present_on_leave = frappe.get_all('Leave Application',fields=["*"], filters={'Status': 'Approved', "department":dpt, "from_date" :['<=', today], "to_date" :['>=', today]})
    upcoming_leave = frappe.get_all('Leave Application',fields=["*"], filters={'status': 'Approved',"department":dpt, "from_date" :['>', today]})
    
    response['leaves'] = leaves
    response['present_on_leave'] = present_on_leave
    response['upcoming_leave'] = upcoming_leave
    return generate_response("S", "200", message="Success", data=response)


@frappe.whitelist()
def get_leave_application(
    fields=None,
    order_by=None,
    group_by=None,
    start=None,
    page_length=None,
    leave_type=None,
    status=None,
    from_date=None,
    to_date=None,
    total_leave_days=None
):
    
    filters = {}
    try:
        if not fields:
            fields = []
        if leave_type:
            filters["leave_type"] = leave_type
        if status:
            filters["status"] = status
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["end_date"] = to_date
        if total_leave_days:
            filters["total_leave_days"] = total_leave_days

        data = frappe.get_list("Leave Application", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
            
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def get_emp_slip(
    fields=None,
    order_by=None,
    group_by=None,
    start=None,
    page_length=None
):
    filters = {}
    try:
        if not fields:
            fields = []

        user = frappe.session.user
        emp = frappe.db.get_value("Employee",{'user_id':user},'employee')
        filters["employee"] = emp
        
        data = frappe.get_list("Salary Slip", ["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        for i in data:
            dt = getdate(i.start_date)
            month = babel.dates.format_date(dt, 'MMMM', locale='en')
            year = babel.dates.format_date(dt, 'yyyy', locale='en')
            i["month"] = month
            i["year"] = year

        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def notification_log():
    try:
        logs = frappe.get_list("Notification Log", fields=["*"])
        for log in logs:
            img = frappe.db.get_value("Employee",{'user_id':log.from_user},'image')
            log['image'] = img
        return generate_response("S", "200", message="Success", data=logs)
    except Exception as e:
        return generate_response("F", error=e)