# -*- coding: utf-8 -*-
# Copyright (c) 2021, Swifta Systems and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe.permissions import add_user_permission, remove_user_permission, \
  set_user_permission_if_allowed, has_permission
from frappe.utils import cstr, cint, get_fullname, get_url
from frappe import _
import frappe, json
import frappe.share

class Appraisals(Document):

    def before_save(self):
        frappe.errprint('before save controller');
        self.notification_sent = 0
        frappe.db.set_value(self.doctype, self.name, "notification_sent", 0);
        frappe.errprint('before save notification value is: '+ str(self.notification_sent))

    def before_insert(self):
        frappe.errprint('before insert called 1');

    def validate(self):
        frappe.errprint('validation called');

    def after_insert(self):
        self.share_doc_with_appraiser();
        self.notify_appraiser();
        frappe.errprint('after_insert called');

    def on_update(self):
        notification_set_value = frappe.db.get_value(self.doctype, self.name, ['notification_sent'])
        frappe.errprint('on update notification value is: '+ str(frappe.db.exists({ 'doctype': self.doctype, 'name': self.name, 'notification_sent': 1})));

        if not frappe.db.exists({ 'doctype': self.doctype, 'name': self.name, 'notification_sent': 1}):
            self.notify_appraiser();
            self.notify_appraisee();

    def on_change(self):
        frappe.errprint('on change');
        self.reload();
        self.notify_update();
        # self.reload_doc();
        frappe.errprint('on change done');


    def share_doc_with_appraiser(self):
        frappe.errprint("sharing doc...")

        # employee_name = frappe.db.get_value("Employee", self.employee, "reporting_manager");
        employee_name = frappe.db.get_value("Employee", self.employee, "reports_to")

        reporting_user_id = frappe.db.get_value("Employee", employee_name, "user_id");

        frappe.share.add(self.doctype, self.name, reporting_user_id, write=1, share=1,
        				flags={"ignore_share_permission": True})


    def notify_appraisee(self):
        frappe.errprint('notifying appraisee at stage: '+ self.stage);
        recipients = []

        subject = 'Appraisal Form Update'

        # reporting_manager, appraisee_email_id = frappe.db.get_value('Employee', self.employee,['reporting_manager', 'user_id']);

        reporting_manager, appraisee_email_id = frappe.db.get_value('Employee', self.employee,['reports_to', 'user_id'])

        appraiser_email_id = frappe.db.get_value('Employee', reporting_manager,'user_id');

        appraisee_full_name = get_fullname(appraisee_email_id);

        appraiser_full_name = get_fullname(appraiser_email_id);

        # link = get_url() + self.get_url()
        portal_url = frappe.get_single('Portal Setting').portal_url
        link = portal_url + '/appraisal/edit-appraisal/' + self.name

        args = {
        "appraisee_employee_id": self.employee,
        "appraisee_full_name": appraisee_full_name,
        "appraiser_full_name": appraiser_full_name,
        "link": link
        }

        if self.stage == 'Appraiser Review Completed':

            template = 'Notify Employee On Update';

            recipients.append(appraisee_email_id);

            self.notify({
                "message_to": recipients,
                "subject": subject,
                "template": template,
                "args": args
                })
        else:
            frappe.errprint('No one to notify')



    def notify_appraiser(self):

        frappe.errprint('notifying appraiser at stage: '+ self.stage);

        recipients = []

        subject = 'Appraisal Form Update'

        # reporting_manager, appraisee_email_id = frappe.db.get_value('Employee', self.employee,['reporting_manager', 'user_id']);
        reporting_manager, appraisee_email_id = frappe.db.get_value('Employee', self.employee,['reports_to', 'user_id'])


        appraiser_email_id = frappe.db.get_value('Employee', reporting_manager,'user_id');

        appraisee_full_name = get_fullname(appraisee_email_id);

        appraiser_full_name = get_fullname(appraiser_email_id);

        # link = get_url() + self.get_url();
        portal_url = frappe.get_single('Portal Setting').portal_url
        link = portal_url + '/appraisal/edit-appraisal/' + self.name

        args = {
        "appraisee_employee_id": self.employee,
        "appraisee_full_name": appraisee_full_name,
        "appraiser_full_name": appraiser_full_name,
        "link": link
        }

        if self.stage == 'Pending Appraiser Review':
            template = 'Notify Reporting Manager';


            recipients.append(appraiser_email_id);

            self.notify({
              # for post in messages
              "message_to": recipients,
              # for email
              "subject": subject,
              "template": template,
              "args": args
              })
        elif self.stage == 'Appraisee Approved Review':

            frappe.errprint('user in session: '+ str(frappe.session.user));

            hr_user_email = frappe.db.sql("""select * from `tabHas Role`
            where parenttype = 'User' and parent <> 'Administrator'
            and role = %s""", ("HR Manager",),as_dict=True);

            template = 'Notify HR and Reporting Manager - Appraisal Approved';

            recipients.append(appraiser_email_id);

            for i in range(len(hr_user_email)):
                recipients.append(hr_user_email[i].parent);

            if self.owner == frappe.session.user:
                self.notify({
                  # for post in messages
                  "message_to": recipients,
                  # for email
                  "subject": subject,
                  "template": template,
                  "args": args
                });
            else:
                frappe.msgprint(_("Record updated Successfully"));


        elif self.stage == 'Appraisee Rejected Review':

            hr_user_email = frappe.db.sql("""select * from `tabHas Role`
            where parenttype = 'User' and parent <> 'Administrator'
            and role = %s""", ("HR Manager",),as_dict=True);

            template = 'Notify HR and Reporting Manager - Appraisal Disapproved';

            recipients.append(appraiser_email_id);

            for i in range(len(hr_user_email)):
                recipients.append(hr_user_email[i].parent);

            if self.owner == frappe.session.user:
                self.notify({
                    "message_to": recipients,
                    "subject":  subject,
                    "template": template,
                    "args": args
                    });
            else:
                frappe.msgprint(_("Record updated Successfully"));


    def notify(self, args):
        frappe.errprint('notification called: '+ self.name);
        args = frappe._dict(args);

        contact = args.message_to

        contact_string = ','.join(contact);

        sender      = dict()
        sender['email']     = frappe.get_doc('User', frappe.session.user).email
        sender['full_name'] = frappe.utils.get_fullname(sender['email'])

        try:
            frappe.sendmail(
                recipients = contact,
                sender = sender['email'],
                subject = args.subject,
                template = args.template,
                args = args.args
              )
            frappe.db.set_value(self.doctype, self.name, "notification_sent", 1);
            frappe.msgprint(_("Email sent to {0}").format(contact_string));
        except frappe.OutgoingEmailError:
            pass