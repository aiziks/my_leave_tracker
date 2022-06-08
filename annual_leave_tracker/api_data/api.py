from site import USER_BASE

from requests import request
import frappe
from frappe import auth
from annual_leave_tracker.api.utils import generate_response
import json



# REGISTER USER
@frappe.whitelist(allow_guest = True)
def RegisterUser():
    reg_data = json.loads(frappe.request.data)
    data = {"email":reg_data.get('email'), "first_name":reg_data.get('first_name')}
    print(f'The data is : {data}')
    email = reg_data.get('email')
    first_name = reg_data.get('email')
    # check if a user exist
    user_exist = frappe.db.sql(f""" select * from `tabUser` where email='{email}' ;  """)
    if user_exist:
        print(f'User {email} already exist')
    else:
        print(f'User {email} does not exist ')
    return data
    



# USER LOGIN API
@frappe.whitelist(allow_guest=True)
def login( usr , pwd ) :
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr , pwd=pwd)
        login_manager.post_login()

    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key":0,
            "message":"Authentication Error!"
        }

        return

    
    # print(frappe.session.user)
    # from here the user is login without exceptions and a session has been generated for the user
    api_generate = generate_keys(frappe.session.user) #generates a string name e.g Administrator
    print(frappe.session.user)
    user = frappe.get_doc('User' , frappe.session.user)  #the currently login user using name=Administrator to fetch the user object


    frappe.response["message"] = {
        "success_key": 1 ,
        "message":"Authentication success",
        "sid": frappe.session.sid,
        "api_key": user.api_key,
        "api_secret" : api_generate,
        "token": user.api_key+":"+api_generate,
        "username": user.username,
        "email": user.email
    }

    # print(frappe.response["message"])



# GENERATING USER LOGIN KEYS  
def generate_keys(user):
    user_details = frappe.get_doc('User' , user)
    api_secret = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key

    user_details.api_secret = api_secret
    user_details.save()

    return api_secret




# logout function
@frappe.whitelist()
def logout():
    try:
        user = frappe.session.user
        login_manager = frappe.auth.LoginManager()
        login_manager.logout(user=user)
        return generate_response("S", "200", message="Logged Out")
    except Exception as e :
        return generate_response("F", error=e)








# GETTING THE DETAILS
@frappe.whitelist()
def get_patient_details(patient_id=None):
    users = frappe.db.sql(f""" SELECT first_name from  `tabUser` where username='administrator'; """ , as_dict=True)    
    print(users)
    return frappe.db.sql(f""" SELECT * from  `tabUser` ; """ , as_dict=True)

