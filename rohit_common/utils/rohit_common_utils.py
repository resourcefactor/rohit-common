# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
# from validate_email import validate_email
from frappe.utils import get_files_path


def check_system_manager(user):
    sys_list = frappe.db.sql("""SELECT name FROM `tabHas Role` WHERE parenttype = 'User' AND parent = '%s' 
        AND role = 'System Manager'""" % user, as_list=1)
    if sys_list:
        return 1
    else:
        return 0


def rebuild_tree(doctype, parent_field, group_field):
    # call rebuild_node for all root nodes
    # get all roots
    lft = 1
    result = frappe.db.sql("SELECT name, %s, lft, rgt FROM `tab%s` WHERE `%s`='' or `%s` IS NULL "
                           "ORDER BY name ASC" % (group_field, doctype, parent_field, parent_field), as_dict=1)
    for r in result:
        if r.get(group_field) == 1:
            rebuild_group(doctype, parent_field, r.name, group_field, lft)
        else:
            frappe.db.sql("""UPDATE `tab%s` SET lft=%s, rgt=%s WHERE name='%s'""" % (doctype, lft, lft+1, r.name))
            lft += 2


def rebuild_group(doctype, parent_field, parent, group_field, left):
    right = left + 1
    non_gp_query = """SELECT name, %s, lft, rgt FROM `tab%s` WHERE %s = '%s' 
    AND %s = 0""" % (group_field, doctype, parent_field, parent, group_field)
    non_grp_results = frappe.db.sql(non_gp_query, as_dict=1)
    for r in non_grp_results:
        frappe.db.sql("""UPDATE `tab%s` SET lft=%s, rgt=%s WHERE name='%s'""" % (doctype, right, right+1, r.name))
        right += 2
    grp_result = frappe.db.sql("""SELECT name, %s FROM `tab%s` WHERE %s = '%s' 
    AND %s = 1""" % (group_field, doctype, parent_field, parent, group_field), as_dict=1)
    for r in grp_result:
        print(f"Updating Groups for {r.name}")
        right = rebuild_group(doctype, parent_field, r.name, group_field, right)
    frappe.db.sql("""UPDATE `tab%s` SET lft=%s, rgt=%s WHERE name='%s'""" % (doctype, left, right, parent))
    return right


def move_file_folder(file_name, old_folder, new_folder, is_folder=0):
    frappe.msgprint(f"File={file_name} OldFolder={old_folder} NewFolder={new_folder} IsFolder={is_folder}")


def get_folder_details(folder_name):
    return frappe.db.sql("""SELECT name, parent, parentfield, parenttype, idx, file_name, attached_to_doctype, rgt, 
    lft, (rgt-lft) as diff,is_home_folder, is_folder, folder, is_private, attached_to_field 
    FROM `tabFile` WHERE name = '%s'""" % folder_name, as_dict=1)


def make_file_path(file_doc):
    if file_doc.is_private == 1:
        fpath = get_files_path(is_private=1)
    else:
        fpath = get_files_path()
    return fpath + '/' + file_doc.file_name


def get_email_id(email_id):
    if email_id:
        if email_id != "NA":
            return email_id
        else:
            return ""


def validate_email_addresses(comm_sep_email, backend=0):
    email_domain = frappe.db.sql("""SELECT name, email_id FROM `tabEmail Domain` 
    WHERE use_domain_to_verify_email_addresses = 1 AND docstatus=0""", as_dict=1)
    if len(email_domain) > 1:
        frappe.throw("There are more than 1 Email Domains Defined to Check Email Addresses. Please make sure only "
                     "1 Email Domain is Checked to Check the Email Addresses")
    elif len(email_domain) != 1:
        frappe.throw("There are NO Email Domains Defined to Check Email Addresses. Please make sure EXACTLY "
                     "1 Email Domain is Checked to Check the Email Addresses")
    else:
        em_domain = email_domain[0].name
        test_email = email_domain[0].email_id
    is_valid = 0
    if comm_sep_email:
        emails = comm_sep_email.split(',')
        for email_id in emails:
            if email_id:
                # is_valid = validate_email(email_id, check_regex=True, check_mx=True, from_address=test_email,
                #                           helo_host=em_domain, smtp_timeout=10, dns_timeout=10,
                #                           use_blacklist=True, debug=True)
                if is_valid != 1:
                    if email_id != "NA":
                        if backend == 0:
                            frappe.msgprint(f"{email_id} is Not Valid Email Address either enter Valid Email ID or NA")
                        else:
                            return 0
                    else:
                        return 0
            else:
                frappe.msgprint("Email ID is Empty, either enter Valid Email or NA")
        return is_valid


def check_sales_taxes_integrity(document):
    template = frappe.get_doc("Sales Taxes and Charges Template", document.taxes_and_charges)
    if len(template.taxes) != len(document.taxes):
        frappe.throw("Tax Template {} Data does not match with Document# {}'s Tax {}".
                     format(template.name,document.name, document.taxes_and_charges))
    if document.taxes:
        for tax in document.taxes:
            for temp in template.taxes:
                if tax.idx == temp.idx:
                    if tax.charge_type != temp.charge_type or tax.row_id != temp.row_id or tax.account_head != \
                            temp.account_head or tax.included_in_print_rate != temp.included_in_print_rate or tax.rate !=\
                            temp.rate:
                        frappe.throw(("Selected Tax {0}'s table does not match with tax table of Sales Order# {1}. Check "
                                      "Row # {2} or reload Taxes").format(document.taxes_and_charges, document.name,
                                                                          tax.idx))
    else:
        frappe.throw("Empty Tax Table is not Allowed for Sales Invoice {0}".format(document.name))


def check_dynamic_link(parenttype, parent, link_doctype, link_name):
    link_type = frappe.db.sql("""SELECT name FROM `tabDynamic Link` 
        WHERE docstatus = 0 AND parenttype = '%s' AND parent = '%s'
        AND link_doctype = '%s' AND link_name = '%s'""" % (parenttype, parent, link_doctype, link_name), as_list=1)
    if not link_type:
        frappe.throw("{} {} does not belong to {} {}".format(parenttype, parent, link_doctype, link_name))


def replace_java_chars(string):
    replace_dict = {
        "false": "False",
        "true": "True",
        "&&": " and ",
        "||": " or ",
        "&gt;": ">",
        "&lt;": "<"
    }
    for k, v in replace_dict.items():
        string = string.replace(k, v)
    return string


def fn_check_digit(id_without_check):
    # This code generates the checkdigit for a given string
    # allowable characters within identifier
    valid_chars = "0123456789ABCDEFGHJKLMNPQRSTUVYWXZ"

    # remove leading or trailing whitespace, convert to uppercase
    id_without_checkdigit = id_without_check.strip().upper()

    # this will be a running total
    sum = 0;

    # loop through digits from right to left
    for n, char in enumerate(reversed(id_without_checkdigit)):

        if not valid_chars.count(char):
            frappe.throw('Invalid Character has been used for Item Code check Attributes')

        # our "digit" is calculated using ASCII value - 48
        digit = ord(char) - 48

        # weight will be the current digit's contribution to
        # the running total
        weight = None
        if (n % 2 == 0):

            # for alternating digits starting with the rightmost, we
            # use our formula this is the same as multiplying x 2 &
            # adding digits together for values 0 to 9.  Using the
            # following formula allows us to gracefully calculate a
            # weight for non-numeric "digits" as well (from their
            # ASCII value - 48).
            weight = (2 * digit) - int((digit / 5)) * 9
        else:
            # even-positioned digits just contribute their ascii
            # value minus 48
            weight = digit

        # keep a running total of weights
        sum += weight

    # avoid sum less than 10 (if characters below "0" allowed,
    # this could happen)
    sum = abs(sum) + 10

    # check digit is amount needed to reach next number
    # divisible by ten. Return an integer
    return int((10 - (sum % 10)) % 10)


def fn_next_string(doc,s):
    #This function would increase the serial number by One following the
    #alpha-numeric rules as well
    if len(s) == 0:
        return '1'
    head = s[0:-1]
    tail = s[-1]
    if tail == 'Z':
        return fn_next_string(doc, head) + '0'
    if tail == '9':
        return head+'A'
    if tail == 'H':
        return head+'J'
    if tail == 'N':
        return head+'P'
    return head + chr(ord(tail)+1)
