# -*- coding: utf-8 -*-
# Copyright (c) 2020, Rohit Industries Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
from frappe.model.document import Document
from frappe.utils import getdate
from ...india_gst_api.eway_bill_api import *


class PulleWayBills(Document):

	def pull_eway_bills(self):
		self.check_already_pulled(self.start_date)
		last_exe_dt, formatted_date = self.get_eway_dates()
		json_reply = get_ewb_date(formatted_date)
		last_ft_dt = self.start_date
		self.update_db(json_reply, last_exe_dt, last_ft_dt)
		self.reload()
		self.create_ewb_from_json()

	def eway_bill_others(self):
		self.check_already_pulled(self.start_date, inward=1)
		last_exe_dt, formatted_date = self.get_eway_dates()
		json_reply = get_ewb_others(formatted_date)
		last_ft_dt = self.start_date
		self.update_db(json_reply, last_exe_dt, last_ft_dt, inward=1)
		self.reload()
		self.create_ewb_from_json()

	def check_already_pulled(self, ewb_date, inward=0):
		gstin = frappe.get_value('Rohit Settings', 'Rohit Settings', 'gstin')
		for d in self.details:
			message = 'Already Pulled eWay Bills for {} Created by {} for GSTIN: {}'.format(ewb_date,
																							d.type_of_eway_bill, gstin)
			if d.date == ewb_date and d.gstin == gstin:
				if inward == 1 and d.type_of_eway_bill == 'Others':
					frappe.throw(message)
				elif inward == 0 and d.type_of_eway_bill == 'Self':
					frappe.throw(message)

	def get_eway_dates(self):
		last_exe_dt = datetime.now()
		if self.start_date:
			if getdate(self.start_date) < datetime.today().date():
				formatted_date = (getdate(self.start_date)).strftime('%d/%m/%Y')
			else:
				frappe.throw('Cannot Get eWay Bills for Today or Future')
		else:
			frappe.throw('Start Date is Needed')
		return last_exe_dt, formatted_date

	def update_db(self, json, last_exe, last_pull_dt, inward=0):
		det_dict = {}
		gstin = frappe.get_value("Rohit Settings", "Rohit Settings", "gstin")
		det_dict["date"] = last_pull_dt
		if inward == 1:
			det_dict["type_of_eway_bill"] = "Others"
		else:
			det_dict["type_of_eway_bill"] = "Self"
		det_dict["gstin"] = gstin
		self.append("details", det_dict.copy())
		self.sort_details_table()
		self.save()
		frappe.db.set_value('Pull eWay Bills', 'Pull eWay Bills', 'json_reply', str(json))
		frappe.db.set_value('Pull eWay Bills', 'Pull eWay Bills', 'last_execution', last_exe)
		frappe.db.set_value('Pull eWay Bills', 'Pull eWay Bills', 'last_fetched_date', last_pull_dt)
		frappe.db.set_value('Pull eWay Bills', 'Pull eWay Bills', 'inward_json', inward)
		frappe.db.commit()

	def sort_details_table(self):
		sorted_table = []
		row_dict = {}
		for row in self.details:
			row_dict["date"] = row.date
			row_dict["type_of_eway_bill"] = row.type_of_eway_bill
			row_dict["gstin"] = row.gstin
			sorted_table.append(row_dict.copy())
		sorted_table = sorted(sorted_table, key=lambda i:i["date"], reverse=1)
		self.details = []
		for d in sorted_table:
			self.append("details", d)

	def create_ewb_from_json(self, type=None):
		json_reply = frappe.db.get_value('Pull eWay Bills','Pull eWay Bills', 'json_reply')
		json_reply = str(json_reply).replace("'", '"')
		json_reply = json.loads(json_reply)
		if isinstance(json_reply, dict):
			if int(json_reply.get('status_cd', 1)) == 0:
				frappe.throw('Json Status Shows Error')
		else:
			if self.inward_json == 0:
				for ewb in json_reply:
					ewb_from_ewb_summary(ewb)
			else:
				for ewb in json_reply:
					others_ewb_from_summary(ewb)
