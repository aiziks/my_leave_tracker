from __future__ import unicode_literals
import re
from warnings import filters
import frappe
from frappe import _
from frappe import auth
from frappe.auth import LoginManager
import uuid
import json
from frappe.utils.pdf import get_pdf
from frappe.desk.query_report import run
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import nowdate, getdate, cint, ceil, today, add_to_date, add_months, date_diff,get_year_start, get_last_day,get_year_ending,add_years,get_first_day
from erpnext.hr.doctype.holiday_list.holiday_list import get_events
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import requests
from six import string_types, iteritems
from erp_generic.api.utils import (
    xml_to_dic,
    send_welcome_mail_to_user,
    reset_password,
    to_base64,
    add_file,
    delete_file,
    generate_response,
    portal_settings,
)
import base64
from frappe.utils.password import update_password as _update_password

days_per_year = 365.24


# @frappe.whitelist(allow_guest=True)
# def login(usr=None, pwd=None):
#     if not usr:
#         return generate_response("F", error="'usr' parameter is required")
#     if not pwd:
#         return generate_response("F", error="'pwd' parameter is required")
#     try:
#         login_manager = LoginManager()
#         login_manager.authenticate(usr, pwd)
#         login_manager.post_login()
#         if frappe.response["message"] == "Logged In":
#             # frappe.response["token"] = generate_key(login_manager.user),
#             frappe.response["user"] = login_manager.user
#             frappe.response["token"] = generate_key(login_manager.user)
#             user_details = frappe.get_doc('User',frappe.session.user) #after_10_days = add_to_date(datetime.now(), days=10, as_string=True)
#             frappe.session.data.session_expiry = add_to_date(nowdate(),days=3, as_string=True)
#             frappe.response["sid"] = frappe.session
#             # frappe.response["api_key"] = user_details.api_key
#     except Exception as e:
#         return generate_response("F", error=e)



@frappe.whitelist( allow_guest=True )
def login(usr, pwd):
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key":0,
            "message":"Authentication Error!"
        }

        return

    api_generate = generate_keys(frappe.session.user)
    user = frappe.get_doc('User', frappe.session.user)

    frappe.response["message"] = {
        "success_key":1,
        "message":"Authentication success",
        "sid":frappe.session.sid,
        "api_key":user.api_key,
        "api_secret":api_generate,
        "token":user.api_key+":"+api_generate,
        "username":user.username,
        "email":user.email
    }


@frappe.whitelist()
def logout():
    try:
        user = frappe.session.user
        login_manager = LoginManager()
        login_manager.logout(user=user)
        return generate_response("S", "200", message="Logged Out")
    except Exception as e:
        return generate_response("F", error=e)






@frappe.whitelist()
def dashboard_details():
    tod = today()
    dashboard_dict = {}
    last_year = add_years(tod,-1)
    y_start = get_year_start(last_year).strftime('%Y-%m-%d')
    y_end = get_year_ending(last_year)
    last_month = add_months(tod,-1)
    m_start = get_first_day(last_month).strftime('%Y-%m-%d')
    m_end = get_last_day(last_month).strftime('%Y-%m-%d')
    # events= get_events(add_to_date(datetime.now(), months=-2, as_string=True), datetime.now().strftime('%Y-%m-%d'))
    # date_diff = datetime.now().strftime('%Y-%m-%d'), add_to_date(datetime.now(), years=-1, as_string=True)
    employee_total = len(frappe.get_all("Employee", filters={'status':'Active'}))
    employee_left_last_year = len(frappe.get_all("Employee", filters={'status':['in',['Left','Inactive']],'relieving_date':['between',[y_start, y_end]]}))
    employee_joined_last_year = len(frappe.get_all("Employee", filters={'Status':'Active','date_of_joining':['between',[y_start, y_end]]}))
    leave_last_month = len(frappe.get_all("Leave Application",filters={'status':'Approved','from_date':['between',[m_start,m_end]]}))
    dashboard_dict["employee_total"] = employee_total
    dashboard_dict["employee_left_within_year"] = employee_left_last_year
    dashboard_dict["employee_joined_within_year"] = employee_joined_last_year
    dashboard_dict["leave_last_month"] = leave_last_month
    return generate_response("S", "200", message="Success", data=dashboard_dict)




@frappe.whitelist()
def pie_dashboard():
    pie_chart = []
    male = len(frappe.get_all("Employee", filters={'Status':'Active','Gender':'Male'}))
    female = len(frappe.get_all("Employee", filters={'Status':'Active', 'Gender':'Female'}))
    male_chart = {'title': 'Male', 'value': male}
    pie_chart.append(male_chart)
    female_chart = {'title': 'Female', 'value': female}
    pie_chart.append(female_chart)
    #pie_chart['Female'] = female
    return generate_response("S", "200", message="Success", data=pie_chart)



@frappe.whitelist()
def bar_dashboard():
    if not frappe.has_permission("Attendance", "read"):
        frappe.local.response.http_status_code = 403
        return generate_response("F", "403", error="Access denied")

    present_chart = []
    absent_chart = []
    leave_chart = []
    for i in range(0,12):
        y_start = get_year_start(nowdate()).strftime('%Y-%m-%d')
        month_start = add_months(y_start,i)
        month_end = get_last_day(month_start).strftime('%Y-%m-%d')

        present = len(frappe.db.get_list('Attendance', filters={'Status': 'Present', 'attendance_date' : ['between', [month_start, month_end]]}))
        present_chart.append(present)

        absent = len(frappe.db.get_list('Attendance', filters={'Status': 'Absent', 'attendance_date' : ['between', [month_start, month_end]]}))
        absent_chart.append(absent)

        leave = len(frappe.db.get_list('Attendance', filters={'Status': 'On Leave', 'attendance_date' : ['between', [month_start, month_end]]}))
        leave_chart.append(leave)

        bar_chart = [list(x) for x in zip(present_chart, absent_chart, leave_chart)]

    return generate_response("S", "200", message="Success", data=bar_chart)


@frappe.whitelist()
def goal_dashboard():
    doc = {}
    y = get_year_start(nowdate()).strftime('%Y-%m-%d')
    x = get_year_ending(y)
    total_goals = len(frappe.get_all("Goals", filters={'creation':['between',[y,x]]}))
    completed = len(frappe.get_all("Goals", filters={'stage':'Completed','creation':['between',[y,x]]}))
    not_completed = len(frappe.get_all("Goals", filters={'stage':['!=','Completed'],'creation':['between',[y,x]]}))
    doc['total_goals'] = total_goals
    doc['completed'] = completed
    doc['not_completed'] = not_completed
    return generate_response("S", "200", message="Success", data=doc)



@frappe.whitelist()
def profile_completion(docname=None):
    if not docname:
        return generate_response("F", error="'docname' parameter is required")

    doc = frappe.get_list("Employee", fields=["*"], filters={'employee':docname})
    for i in doc:
        items = len({key:value for key,value in i.items()})
        completed = len({key:value for key,value in i.items() if value != None and value != ""})
        per_completed = round((completed / items) * 100 , 2)
        return generate_response("S", "200", message="Success", data=per_completed)


def generate_keys(user):
    user_details = frappe.get_doc('User', user)
    api_secret = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key

    user_details.api_secret = api_secret
    user_details.save()
    frappe.db.commit()

    return api_secret
    


def generate_key_old(user):
    """
    generate api key and api secret
    :param user: str
    """
    user_details = frappe.get_doc('User', user)
    # user_details = frappe.db.sql(""" select * from tabUser where name='{}'""".format(user),as_dict=0)
    print(user_details)
    print(user_details.api_secret)
    # if api key is not set generate api key
    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
    # if not user_details.api_secret:
    api_secret = frappe.generate_hash(length=15)
    user_details.api_secret = api_secret
    user_details.save(ignore_permissions=True)
    user_details.reload()
    api_kyes_base64 = user_details.api_key + ":" + api_secret
    # api_kyes_base64_dec = base64.b64encode(api_kyes_base64.encode("ascii"))
    # api_kyes_base64 = to_base64(user_details.api_key + ":" + user_details.api_secret)
    token = "{0}".format(api_kyes_base64)
    return token

@frappe.whitelist()
def get_user():
    try:
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)
        return generate_response("S", "200", message="Success", data=user_doc)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def get_user_image():
    try:
        user = frappe.session.user
        user_doc = frappe.get_doc("User", user)
        image = user_doc.user_image
        return generate_response("S", "200", message="Success", data=image)
    except Exception as e:
        return generate_response("F", error=e)



@frappe.whitelist()
def current_employee():
    user = frappe.session.user
    if user == "Administrator":
        return "not allowed"
    doc = frappe.get_list("Employee",fields=["*"],filters={'user_id':user})
    for i in doc:
        # reporting_manager = frappe.db.get_value('Employee', i.name,'reporting_manager')
        # email_id = frappe.db.get_value('Employee', reporting_manager, 'user_id')
        # i["reporting_manager_email"] = email_id
        leave_approver_email = frappe.db.get_value("Employee", i.name, 'leave_approver')
        leave_approver_name = frappe.db.get_value("User",leave_approver_email,'full_name')
        # user_id = frappe.db.get_value("Employee", i.name, 'user_id')
        roles = []
        role =frappe.db.sql(""" select role from `tabHas Role` where role is not null and role!='' and parent = '{}' """.format(user),as_dict=True)
        for j in role:
            roles.append(j.role)
        i["leave_approver_name"] = leave_approver_name
        i["roles"] = roles

    return generate_response("S", "200", message="Success", data=doc)



@frappe.whitelist()
def appraisal_completed():
    doc = frappe.get_list("Appraisals", fields=["*"], filters={'status':'Approved'})
    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def appraisal_in_progress():
    doc = frappe.get_list("Appraisals", fields=["*"], filters={'status':['!=','Approved']})
    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def user_goal():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'] )
    doc = frappe.get_list("Goals", filters={'employee':name})
    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def pending():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    pend = []
    pending = frappe.get_list("Goals", fields=["*"], filters={'employee':name,'status':'Pending Approval', 'stage':'Completed'})
    for v in pending:
        li = []
        act = frappe.get_list("Activities", fields=['name','activity'],filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    pend.append(pending)

    return generate_response("S", "200", message="Success", data=pend)

@frappe.whitelist()
def not_started():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = []
    not_started = frappe.get_list("Goals", fields=["*"], filters={'employee':name,'stage':'Not Started'})
    for v in not_started:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(not_started)

    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def in_progress():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = []
    in_progress = frappe.get_list("Goals", fields=["*"], filters={'employee':name,'stage':'In Progress'})
    for v in in_progress:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(in_progress)

    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def completed():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = []
    completed = frappe.get_list("Goals", fields=["*"], filters={'employee':name,'status':'Approved', 'stage':'Completed'})
    for v in completed:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(completed)

    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def cancelled():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = []
    cancelled = frappe.get_list("Goals", fields=["*"], filters={'employee':name,'stage':'Cancelled'})
    for v in cancelled:
        li = []
        act = frappe.get_list("Activities",fields=['name','activity'], filters={'linked_goal': v.name})
        li.append(act)
        v['activities'] = act
    doc.append(cancelled)
    
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def high():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':name,'status':'High'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def medium():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':name,'status':'Medium'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def low():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':name,'status':'Low'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def complete():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':name,'status':'Complete'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def paused():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':name,'status':'Paused'})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def achievement():
    user = frappe.session.user
    name = frappe.db.get_value("Employee",{'user_id': user}, ['employee'])
    doc = frappe.get_list("Activities", fields=["*"], filters={'employee':name,'mark_as_achievement':1})
    for i in doc:
        goal_name = frappe.db.get_value("Goals",{'name': i.linked_goal}, ['goal_name'])
        i["goal_name"] = goal_name
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def get_doc(doctype=None, docname=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")
    if not docname:
        return generate_response("F", error="'docname' parameter is required")

    if not frappe.has_permission(doctype, "read"):
        frappe.local.response.http_status_code = 403
        return generate_response("F", "403", error="Access denied")

    if not frappe.db.exists(doctype, docname):
        frappe.local.response.http_status_code = 404
        return generate_response(
            "F", "404", error="{0} '{1}' not exist".format(doctype, docname)
        )
    doc = frappe.get_doc(doctype, docname)
    return generate_response("S", "200", message="Success", data=doc)

@frappe.whitelist()
def leave_application(
    order_by=None,
    group_by=None,
    start=None,
    page_length=None,
    leave_type=None
):
    # filters={}
    try:
        doc = {}

        pending = frappe.get_list("Leave Application", ["*"], filters={'status': "Open"}, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        for i in pending:
            designation, image = frappe.db.get_value("Employee",{'name': i.employee}, ['designation', "image"])
            i["designation"] = designation
            i["image"] = image

        resolved = frappe.get_list("Leave Application", ["*"], filters={'status':['in',['Approved','Rejected','Cancelled']]}, order_by=order_by, group_by=group_by, start=start, page_length=page_length)
        for i in resolved:
            designation, image = frappe.db.get_value("Employee",{'name': i.employee}, ['designation', "image"])
            i["designation"] = designation
            i["image"] = image

        doc["pending"] = pending
        doc["resolved"] = resolved

        return generate_response("S", "200", message="Success", data=doc)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def leave_profile(id=None):
    if not id:
        return generate_response("F", error="'Leave ID' parameter is required")
    
    doc = pending = frappe.get_list("Leave Application", ["*"], filters={'name': id})
    for i in doc:
        designation, image = frappe.db.get_value("Employee",{'name': i.employee}, ['designation', "image"])
        i["designation"] = designation
        i["image"] = image
    return generate_response("S", "200", message="Success", data=doc)





@frappe.whitelist()
def get_leave_overview():

    response = dict()
    today =  datetime.now().strftime('%Y-%m-%d')
    present_on_leave = frappe.get_list("Leave Application",fields=["*"], filters={'status':['=',['Approved']],"from_date" :['<=', today], "to_date" :['>=', today]})
    for i in present_on_leave:
        designation, image = frappe.db.get_value("Employee",{'name': i.employee}, ['designation', "image"])
        i["designation"] = designation
        i["image"] = image

    upcoming_leave = frappe.get_list("Leave Application",fields=["*"], filters={'status': ['=',['Approved']],"from_date" :['>', today]})
    for i in upcoming_leave:
            designation, image = frappe.db.get_value("Employee",{'name': i.employee}, ['designation', "image"])
            i["designation"] = designation
            i["image"] = image
    
    response['present_on_leave'] = present_on_leave
    response['upcoming_leave'] = upcoming_leave
    
    return generate_response("S", "200", message="Success", data=response)



@frappe.whitelist()
def new_doc(doctype=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")
    try:
        if not frappe.has_permission(doctype, "read"):
            frappe.local.response.http_status_code = 403
            return generate_response("F", "403", error="Access denied")

        doc_dict = frappe.new_doc(doctype, as_dict=True)
        doc = frappe.new_doc(doctype, as_dict=False)
        meta = frappe.get_meta(doctype).fields
        for df in meta:
            if not doc_dict.get(df.fieldname):
                doc_dict[df.fieldname] = ""
        doc.update(doc_dict)
        return generate_response("S", "200", message="Success", data=doc)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_meta(doctype=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")

    try:
        if not frappe.has_permission(doctype, "read"):
            return generate_response("F", "403", error="Access denied")
        data = frappe.get_meta(doctype)
        generate_response("S", "200", message="Success", data=data)
    except Exception:
        frappe.local.response.http_status_code = 404
        return generate_response("F", "404", error="{0} not exist".format(doctype))

@frappe.whitelist()
def employee_meta():
    doc = frappe.get_meta('Employee')
    doc_fields = doc.fields
    name_type = {a.fieldname:a.fieldtype for a in doc_fields}
    generate_response("S", "200", message="Success", data=name_type)

@frappe.whitelist()
def meta_data(doctype=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")
    if not frappe.has_permission(doctype, "read"):
        return generate_response("F", "403", error="Access denied")
    
    doc = frappe.get_meta(doctype)
    doc_fields = doc.fields
    name_type = {a.fieldname:a.fieldtype for a in doc_fields}
    generate_response("S", "200", message="Success", data=name_type)

@frappe.whitelist()
def get_doc_meta(doctype=None, docname=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")
    if not docname:
        return generate_response("F", error="'docname' parameter is required")

    if not frappe.has_permission(doctype, "read"):
        return generate_response("F", "403", error="Access denied")

    if not frappe.db.exists(doctype, docname):
        frappe.local.response.http_status_code = 404
        return generate_response(
            "F", "404", error="{0} '{1}' not exist".format(doctype, docname)
        )
    doc = frappe.get_doc(doctype, docname)
    meta = frappe.get_meta(doctype)
    data = {"doc": doc, "meta": meta}
    return generate_response("S", "200", message="Success", data=data)

@frappe.whitelist()
def doc_fields(doctype):
    try:
        meta_data = frappe.get_meta(doctype)
        meta_fields = meta_data.fields
        fields = [a.fieldname for a in meta_fields]
        generate_response("S", "200", message="Success", data=fields)
    except Exception as e:
        return generate_response("F", error=e)

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


@frappe.whitelist()
def get_all(
    doctype=None,
    fields=None,
    filters=None,
    order_by=None,
    group_by=None,
    page=None
):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")

    try:
        if not fields:
            fields = ["*"]
        if not filters:
            filters = {}
        if page:page = cint(page)
        
        if not page or page == 1:
            start = 0
            current_page = 1
        else:
            start = (page - 1) * 10
            current_page = page

        doc_length = len(frappe.get_all(doctype, filters, order_by=order_by))
        total_pages = ceil(doc_length / 10)
        page_length = 10
        
        
        data = frappe.get_all(
            doctype, fields, filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length
        )
        resp = {
            'total_pages':total_pages,
            'current_page':current_page,
            'data':data
        }
        return generate_response("S", "200", message="Success", data=resp)
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_list(
    doctype=None,
    fields=None,
    filters=None,
    order_by=None,
    group_by=None,
    start=None,
    page_length=None
):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")

    try:
        if not fields:
            fields = []
        if not filters:
            filters = {}

        data = frappe.get_all(
            doctype,["*"], filters, order_by=order_by, group_by=group_by, start=start, page_length=page_length
        )
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)

@frappe.whitelist()
def all_list(doctype=None):
    if not doctype:
        return generate_response("F", error="'doctype' parameter is required")

    doc = frappe.get_list(doctype, fields=["*"])
    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist(allow_guest=True)
def get_item(docname=None):
    if not docname:
        return generate_response("F", error="'docname' parameter is required")

    if not frappe.db.exists("Item", docname):
        return generate_response("F", error="Item not exist")
    doc = frappe.get_doc("Item", docname)
    return generate_response("S", "200", message="Success", data=doc)


@frappe.whitelist()
def get_pdf_file(doctype=None, docname=None):
    try:
        if not doctype:
            frappe.local.response.http_status_code = 500
            return generate_response("F", error="'doctype' parameter is required")
        if not docname:
            frappe.local.response.http_status_code = 500
            return generate_response("F", error="'docname' parameter is required")
        if not frappe.has_permission(doctype, "read"):
            frappe.local.response.http_status_code = 403
            return generate_response("F", "403", error="Access denied")
        if not frappe.db.exists(doctype, docname):
            frappe.local.response.http_status_code = 404
            return generate_response(
                "F", "404", error="{0} '{1}' not exist".format(doctype, docname)
            )

        print_format = ""
        default_print_format = frappe.db.get_value(
            "Property Setter",
            dict(property="default_print_format", doc_type=doctype),
            "value",
        )
        if default_print_format:
            print_format = default_print_format
        else:
            print_format = "Standard"

        html = frappe.get_print(
            doctype, docname, print_format, doc=None, no_letterhead=0
        )

        frappe.response["status_code"] = 200
        frappe.response["msg"] = "Success"
        frappe.response.filename = "{name}.pdf".format(
            name=docname.replace(" ", "-").replace("/", "-")
        )
        frappe.response.filecontent = get_pdf(html)
        frappe.response.type = "pdf"

    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist(allow_guest=True)
def test_password_strength(new_password, user_data=None):
    from frappe.utils.password_strength import (
        test_password_strength as _test_password_strength,
    )

    password_policy = (
        frappe.db.get_value(
            "System Settings",
            None,
            ["enable_password_policy", "minimum_password_score"],
            as_dict=True,
        )
        or {}
    )

    enable_password_policy = cint(password_policy.get("enable_password_policy", 0))
    minimum_password_score = cint(password_policy.get("minimum_password_score", 0))

    if not enable_password_policy:
        return {}

    if not user_data:
        user_data = frappe.db.get_value(
            "User",
            frappe.session.user,
            ["first_name", "middle_name", "last_name", "email", "birth_date"],
        )

    if new_password:
        result = _test_password_strength(new_password, user_inputs=user_data)
        password_policy_validation_passed = False

        # score should be greater than 0 and minimum_password_score
        if result.get("score") and result.get("score") >= minimum_password_score:
            password_policy_validation_passed = True

        result["feedback"][
            "password_policy_validation_passed"
        ] = password_policy_validation_passed
        return result


def handle_password_test_fail(result):
    suggestions = (
        result["feedback"]["suggestions"][0]
        if result["feedback"]["suggestions"]
        else ""
    )
    warning = result["feedback"]["warning"] if "warning" in result["feedback"] else ""
    suggestions += (
        "<br>"
        + _("Hint: Include symbols, numbers and capital letters in the password")
        + "<br>"
    )
    frappe.throw(" ".join([_("Invalid Password:"), warning, suggestions]))


@frappe.whitelist()
def update_password(new_password):
    try:
        result = test_password_strength(new_password)
        feedback = result.get("feedback", None)

        if feedback and not feedback.get("password_policy_validation_passed", False):
            handle_password_test_fail(result)

        user = frappe.session.user

        _update_password(user, new_password)

        frappe.local.login_manager.login_as(user)

        frappe.db.set_value("User", user, "last_password_reset_date", today())
        frappe.db.set_value("User", user, "reset_password_key", "")
        return generate_response("S", "200", message="Success")
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def get_employee_paroll(start_date, end_date, company=None,department=None):
    try:
        record_list = frappe.get_list("Salary Structure Assignment",fields=["*"], filters=["docstatus","1",["from_date","between",[start_date,end_date]]])
        record_list = [x for x in record_list if x["docstatus"]==1]
        if company:
            record_list = [x for x in record_list if x["company"]==company]
        if department:
            record_list = [x for x in record_list if x["department"]==department]
        return generate_response("S", "200", message="Success", data=record_list)
    except Exception as e:
        return generate_response("F",error=e)


def send_welcome_mail(doc, method):
    if doc.is_new and doc.send_emp_welcome_email:
        send_welcome_mail_to_user(doc)


@frappe.whitelist(allow_guest=True)
def reset_pass(user):
    try:
        if user == "Administrator":
            return "not allowed"

        try:
            user = frappe.get_doc("User", user)
            if not user.enabled:
                return "disabled"

            user.validate_reset_password()
            reset_password(user, send_email=True)

            return frappe.msgprint(
                _("Password reset instructions have been sent to your email")
            )

        except frappe.DoesNotExistError:
            frappe.clear_messages()
            return "User not found"
    except Exception as e:
        return generate_response("F", error=e)


def validate_reset_password(user):
    pass


@frappe.whitelist()
def upload_image(doctype=None, docname=None, field_name=None, image=None):
    try:
        if not doctype:
            frappe.throw("'doctype' parameter is required")
        if not docname:
            frappe.throw("'docname' parameter is required")
        if not field_name:
            frappe.throw("'field_name' parameter is required")
        if not image:
            frappe.throw("'image' parameter is required")
        exists = frappe.db.exists(doctype, docname)
        if not exists:
            frappe.throw("Doctype {0} is not exist".format(docname))

        delete_file(doctype, docname, field_name)
        image_link = add_file(image, "image", doctype, docname)

        frappe.set_value(doctype, docname, field_name, image_link)
        frappe.db.commit()
        if image_link:
            return generate_response(
                "S", "200", message="Image Added Successfully", data=image_link
            )
    except Exception as e:
        return generate_response("F", error=e)


@frappe.whitelist()
def upload_file(doctype=None, docname=None, field_name=None, file=None, file_name=None):
    try:
        if not doctype:
            frappe.throw("'doctype' parameter is required")
        if not docname:
            frappe.throw("'docname' parameter is required")
        if not field_name:
            frappe.throw("'field_name' parameter is required")
        if not file:
            frappe.throw("'file' parameter is required")
        if not file_name:
            frappe.throw("'file_name' parameter is required")
        exists = frappe.db.exists(doctype, docname)
        if not exists:
            frappe.throw("Doctype {0} is not exist".format(docname))

        delete_file(doctype, docname, field_name)
        file_link = add_file(file, field_name, doctype, docname, file_name)

        frappe.set_value(doctype, docname, field_name, file_link)
        frappe.db.commit()
        if file_link:
            return generate_response(
                "S", "200", message="File Added Successfully", data=file_link
            )
    except Exception as e:
        return generate_response("F", error=e)

def make_filters(slf):
    filters = frappe._dict()
    filters['company'] = slf.company
    filters['branch'] = slf.branch
    filters['department'] = slf.department
    filters['designation'] = slf.designation
    return filters

@frappe.whitelist()
def get_employee_list(docname):
    """
    Returns list of active employees based on selected criteria
    and for which salary structure exists
    """
    from erpnext.payroll.doctype.payroll_entry.payroll_entry import  get_filter_condition, get_joining_relieving_condition,get_sal_struct,remove_payrolled_employees,get_emp_list
    doc = frappe.get_doc("Payroll Entry", docname)
    # doc = doc.as_dict()
    filters = make_filters(doc)
    cond = get_filter_condition(filters)
    cond += get_joining_relieving_condition(doc.start_date, doc.end_date)
    
    condition = ''
    if doc.payroll_frequency:
        condition = """and payroll_frequency = '%(payroll_frequency)s'"""% {"payroll_frequency": doc.payroll_frequency}

    sal_struct = get_sal_struct(doc.company, doc.currency, doc.salary_slip_based_on_timesheet, condition)
    if sal_struct:
        cond += "and t2.salary_structure IN %(sal_struct)s "
        cond += "and t2.payroll_payable_account = %(payroll_payable_account)s "
        cond += "and %(from_date)s >= t2.from_date"
        emp_list = get_emp_list(sal_struct, cond, doc.end_date, doc.payroll_payable_account)
        emp_list = remove_payrolled_employees(emp_list, doc.start_date, doc.end_date)
        return emp_list

@frappe.whitelist()
def get_salary_register(from_date=None,to_date=None,company=None,employee=None,currency=None,docstatus=None):
# def get_salary_register(filters):
    filters = {}
    filters["from_date"]= from_date if from_date else None
    filters["to_date"]= to_date if to_date else None
    filters["company"]= company if company else None
    filters["employee"]= employee if employee else None
    filters["currency"]= currency if currency else None
    filters["docstatus"]= docstatus if docstatus else None
    # filters = json.loads(filters)
    from erpnext.payroll.report.salary_register.salary_register import execute
    return execute(filters)


@frappe.whitelist()
def get_emp_salary(
    employee,
    status=None,
    order_by=None,
    page=None
):
    # if order_by:
    #     emp_ls = frappe.get_all("Salary Slip", filters={"employee":employee, "status":status},fields=["*"], order_by=order_by)
    # else:
    #     emp_ls = frappe.get_all("Salary Slip", filters={"employee":employee, "status":status},fields=["*"])
    # return generate_response(
    #             "S", "200", message="Successfully", data=emp_ls
    #         )
    if page:page = cint(page)        
    if not page or page == 1:
        start = 0
        current_page = 1
    else:
        start = (page - 1) * 10
        current_page = page

    doc_length = len(frappe.get_all("Salary Slip",
        filters={"employee":employee,
        "status":status},
        order_by=order_by))
    
    total_pages = ceil(doc_length / 10)
    page_length = 10

    data = frappe.get_all("Salary Slip",
        fields=["*"],
        filters={"employee":employee, "status":status},
        order_by=order_by,start=start, 
        page_length=page_length)
    
    resp = {
        'total_pages':total_pages,
        'current_page':current_page,
        'data':data
    }
    return generate_response("S", "200", message="Success", data=resp)


@frappe.whitelist()
def export_report(doctype=None, document=None, method=None, file_type=None,report_name=None, filters=None, page=None, columns=None):
    # from frappe.model.document import Document
	user = frappe.session.user
	# return frappe.utils.cstr(filters)
	return filters
    
	doc = frappe.get_doc({
		'doctype': 'Access Log',
		'user': user,
		'export_from': doctype,
		'reference_document': document,
		'file_type': file_type,
		'report_name': report_name,
		'page': page,
		'method': method,
		# 'filters': frappe.utils.cstr(filters) if filters else None,
		'filters': filters if filters else None,
		'columns': columns
	})
	doc.insert(ignore_permissions=True)

    # if frappe.request and frappe.request.method == 'GET':
	# 	frappe.db.commit()

@frappe.whitelist()
def get_employee_promotion(department=None, designation=None, company=None,employee=None,order_by=None, page=1):
    filters = ""
    if department:
        filters += f"ep.department=\"{department}\""
    if designation:
        if(department):  filters+=" AND "
        filters += f"emp.designation=\"{designation}\""
    if company:
        if(department or designation):  filters+=" AND "
        filters += f"ep.company=\"{company}\""
    if employee:
        if(department or designation or company):  filters+=" AND "
        filters += f"ep.employee=\"{employee}\"" 
    # data_len = len(frappe.get_all("Employee Promotion",fields=["*"], filters=filters))
    page= cint(page)
    limit_expression = f"LIMIT {cint(page)*10},10" if page != 1 else "LIMIT 10"

    if  filters:
        data_len = len(frappe.db.sql(f"""select ep.*, emp.designation from `tabEmployee Promotion` ep left join `tabEmployee` emp on ep.employee=emp.name where {filters} order by ep.creation """,as_dict=1))
        data = frappe.db.sql(f"""select ep.*, emp.designation from `tabEmployee Promotion` ep left join `tabEmployee` emp on ep.employee=emp.name where {filters} order by {"ep."+order_by or ""} {limit_expression}""",as_dict=1)
    else:
        data_len = len(frappe.db.sql(f"""select ep.*, emp.designation from `tabEmployee Promotion` ep left join `tabEmployee` emp on ep.employee=emp.name order by ep.creation """,as_dict=1))
        data = frappe.db.sql(f"""select ep.*, emp.designation from `tabEmployee Promotion` ep left join `tabEmployee` emp on ep.employee=emp.name order by {"ep."+order_by or ""} {limit_expression}""",as_dict=1)
    resp = {
            'total_pages':ceil(data_len/10),
            'current_page':page,
            'data':data
        }
    return generate_response(
                "S", "200", message="Successfully", data=resp
            )

@frappe.whitelist()
def get_employee_transfer(department=None, designation=None, company=None, new_company=None,employee=None, order_by=None, page=1):
    filters = ""
    if department:
        filters += f"ep.department=\"{department}\""
    if designation:
        if(department):  filters+=" AND "
        filters += f"emp.designation=\"{designation}\""
    if new_company:
        if(department or designation):  filters+=" AND "
        filters += f"ep.new_company=\"{new_company}\""
    if company:
        if(department or designation or new_company):  filters+=" AND "
        filters += f"ep.company=\"{company}\""
    if employee:
        if(department or designation or new_company or company):  filters+=" AND "
        filters += f"ep.employee=\"{employee}\"" #employee
    # data_len = len(frappe.get_all("Employee Transfer",fields=["*"], filters=filters))
    page= cint(page)
    limit_expression = f"LIMIT {cint(page)*10},10" if page != 1 else "LIMIT 10"
    if  filters:
        data_len = len(frappe.db.sql(f"""select ep.*,emp.designation from `tabEmployee Transfer` ep left join `tabEmployee` emp on ep.employee=emp.name where {filters} """,as_dict=1))
        data = frappe.db.sql(f"""select ep.*,emp.designation from `tabEmployee Transfer` ep left join `tabEmployee` emp on ep.employee=emp.name where {filters} order by {"ep."+order_by or ""} {limit_expression}""",as_dict=1)
    else:
        data_len = len(frappe.db.sql(f"""select ep.*,emp.designation from `tabEmployee Transfer` ep left join `tabEmployee` emp on ep.employee=emp.name order by ep.creation """,as_dict=1))
        data = frappe.db.sql(f"""select ep.*,emp.designation from `tabEmployee Transfer` ep left join `tabEmployee` emp on ep.employee=emp.name order by {"ep."+order_by or ""} {limit_expression}""",as_dict=1)
    resp = {
            'total_pages':ceil(data_len/10),
            'current_page':page,
            'data':data
        }
    return generate_response(
                "S", "200", message="Successfully", data=resp
            )




@frappe.whitelist()
def export_query(docstatus=None, report_name=None, from_date = None, to_date=None, currency=None, employee=None, company=None):
    from frappe.desk.query_report import run, get_columns_dict,handle_duration_fieldtype_values,build_xlsx_data
    """export from query reports"""

    # data = frappe._dict(frappe.local.form_dict)
    # data.pop("cmd", None)
    # data.pop("csrf_token", None)
    # filters = frappe.parse_json(data["filters"])
    # if isinstance(data.get("filters"), string_types):
    #     filters = json.loads(data["filters"])
    # filters = json.loads(data["filters"])
    filter_new = dict()
    filter_new[docstatus] = f"\"{docstatus}\""
    if(from_date):filter_new[from_date] = f"\"{from_date}\""
    if(to_date):filter_new[to_date] = f"\"{to_date}\""
    if(currency):filter_new[currency] = f"\"{currency}\""
    if(employee):filter_new[employee] = f"\"{employee}\""
    if(company):filter_new[company] = f"\"{company}\""
    # return docstatus
    # if data.get("report_name"):
    #     report_name = data["report_name"]
    #     frappe.permissions.can_export(
	# 		frappe.get_cached_value("Report", report_name, "ref_doctype"),
	# 		raise_exception=True,
	# 	)
    if report_name:
        report_name = report_name
        frappe.permissions.can_export(
			frappe.get_cached_value("Report", report_name, "ref_doctype"),
			raise_exception=True,
		)

    file_format_type = "Excel" #data.get("file_format_type")
    # custom_columns = None
    custom_columns = "[]"
    include_indentation = None #data.get("include_indentation")
    # include_indentation = data.get("include_indentation")
    visible_idx = "[0,1,2,3,4,5,6,7,8,9,10,11,12]" #data.get("visible_idx")

    if isinstance(visible_idx, string_types):
        visible_idx = json.loads(visible_idx)

    if file_format_type == "Excel":
        data = run(report_name, filter_new, custom_columns=custom_columns)
        data = frappe._dict(data)
        if not data.columns:
            frappe.respond_as_web_page(
				_("No data to export"),
				_("You can try changing the filters of your report."),
			)
            return

        columns = get_columns_dict(data.columns)

        from frappe.utils.xlsxutils import make_xlsx

        data["result"] = handle_duration_fieldtype_values(
			data.get("result"), data.get("columns")
		)
        xlsx_data, column_widths = build_xlsx_data(columns, data, visible_idx, include_indentation)
        xlsx_file = make_xlsx(xlsx_data, "Query Report", column_widths=column_widths)

        frappe.response["filename"] = report_name + ".xlsx"
        frappe.response["filecontent"] = xlsx_file.getvalue()
        frappe.response["type"] = "binary"


@frappe.whitelist()
def export_query_new():
    
    """export from query reports"""
    from frappe.desk.query_report import run, get_columns_dict,handle_duration_fieldtype_values,build_xlsx_data

    data = frappe._dict(frappe.local.form_dict)
    data.pop("cmd", None)
    data.pop("csrf_token", None)
    
    if isinstance(data.get("filters"), string_types):
        filters = json.loads(data["filters"])

    if data.get("report_name"):
        report_name = data["report_name"]
        frappe.permissions.can_export(
			frappe.get_cached_value("Report", report_name, "ref_doctype"),
			raise_exception=True,
		)

    file_format_type = data.get("file_format_type")
    custom_columns = frappe.parse_json(data.get("custom_columns", "[]"))
    include_indentation = data.get("include_indentation")
    visible_idx = data.get("visible_idx")
    if isinstance(visible_idx, string_types):
        visible_idx = json.loads(visible_idx)
    
    if file_format_type == "Excel":
        data = run(report_name, filters, custom_columns=custom_columns)
        data = frappe._dict(data)
        if not data.columns:
            frappe.respond_as_web_page(
				_("No data to export"),
				_("You can try changing the filters of your report."),
			)
            return

        columns = get_columns_dict(data.columns)
        
        from frappe.utils.xlsxutils import make_xlsx

        data["result"] = handle_duration_fieldtype_values(
			data.get("result"), data.get("columns")
		)
        xlsx_data, column_widths = build_xlsx_data(columns, data, visible_idx, include_indentation)
        xlsx_file = make_xlsx(xlsx_data, "Query Report", column_widths=column_widths)

        frappe.response["filename"] = report_name + ".xlsx"
        frappe.response["filecontent"] = xlsx_file.getvalue()
        frappe.response["type"] = "binary"



@frappe.whitelist()
def generate_report(
    report_name,
    filters=None
):
    try:
        data = run(
            report_name,
            filters,
            ignore_prepared_report=False
        )
        return generate_response("S", "200", message="Success", data=data)
    except Exception as e:
        return generate_response("F", error=e)
