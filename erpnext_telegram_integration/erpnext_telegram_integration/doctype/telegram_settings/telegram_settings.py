# -*- coding: utf-8 -*-
# Copyright (c) 2019, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import frappe
import telegram
import asyncio
from frappe.model.document import Document
from frappe.utils import get_url_to_form
from frappe.utils.data import quoted
from frappe import _
from bs4 import BeautifulSoup
from frappe.utils.print_format import download_pdf

class TelegramSettings(Document):
	pass


@frappe.whitelist()
def send_to_telegram(telegram_user, message, reference_doctype=None, reference_name=None, attachment=None):
	frappe.enqueue("erpnext_telegram_integration.erpnext_telegram_integration.doctype.telegram_settings.telegram_settings.send_to_telegram_queue", queue='short', telegram_user=telegram_user, message=message,reference_doctype=reference_doctype,reference_name=reference_name,attachment=attachment)
 

@frappe.whitelist()
def send_to_telegram_queue(telegram_user, message, reference_doctype=None, reference_name=None, attachment=None):
	
	space = "\n" * 2
	telegram_chat_id = frappe.db.get_value('Telegram User Settings', telegram_user,'telegram_chat_id')
	telegram_settings = frappe.db.get_value('Telegram User Settings', telegram_user,'telegram_settings')
	telegram_token = frappe.db.get_value('Telegram Settings', telegram_settings,'telegram_token')
	bot = telegram.Bot(token=telegram_token)


	if reference_doctype and reference_name:
		doc_url = get_url_to_form(reference_doctype, reference_name)
		telegram_doc_link =""# _("See the document at {0}").format(doc_url)
		if message:
			soup = BeautifulSoup(message)
			message = soup.get_text('\n') + space + str(telegram_doc_link)
			if type(attachment) is str:
				attachment = int(attachment)
			else:
				if attachment:
					attachment = 1
			if attachment == 1:
				attachment_url =get_url_for_telegram(reference_doctype, reference_name)
				message = message + space +  attachment_url
			try:
				asyncio.run(bot.send_message(chat_id=telegram_chat_id, text=message))
			except Exception as e:
				if str(e)=="Timed out":
					frappe.get_doc({
						"doctype":"Telegram Notification Fail Log",
						"chat_id":telegram_chat_id,
						"message":message,
						"token":telegram_token
					}).insert()
			
		
	else:
		message = space + str(message) + space
		
		asyncio.run(bot.send_message(chat_id=telegram_chat_id, text=message))



def get_url_for_telegram(doctype, name):
	doc = frappe.get_doc(doctype, name)
	return "{url}/api/method/erpnext_telegram_integration.get_pdf.pdf?doctype={doctype}&name={name}&key={key}".format(
		url=frappe.utils.get_url(),
		doctype=quoted(doctype),
		name=quoted(name),
		key=doc.get_signature()
	)

@frappe.whitelist()
def retry_send_the_fail_telegrame_message():
	data = frappe.db.sql("select name,token, chat_id, message from `tabTelegram Notification Fail Log` where status='Not Sent' order by creation",as_dict=1)
	if data:
		for d in data:
			bot = telegram.Bot(token=d["token"])
			asyncio.run(bot.send_message(chat_id=d["chat_id"], text=d["message"]))
			frappe.db.sql("update `tabTelegram Notification Fail Log` set status='Sent' where name='{}'".format(d["name"]))
		frappe.db.commit()



