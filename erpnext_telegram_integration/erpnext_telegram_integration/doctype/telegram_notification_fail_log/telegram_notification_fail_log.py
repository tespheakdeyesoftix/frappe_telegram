# Copyright (c) 2023, Youssef Restom and contributors
# For license information, please see license.txt

import frappe
import telegram
import asyncio

from frappe.model.document import Document


class TelegramNotificationFailLog(Document):
    pass

	# def on_update(self):
	# 	bot = telegram.Bot(token=self.token)
	# 	doc = frappe.get_doc('Cashier Shift', 'CS2023-0035')
	# 	document = frappe.call("frappe.utils.print_format.download_pdf", doctype="Cashier Shift", doc=doc, name="CS2023-0035", format="Close Shift Summary Report", no_letterhead=1)
	 
	# 	asyncio.run(bot.send_message(chat_id=self.chat_id, text=self.message))
	# 	asyncio.run(bot.send_document(chat_id=self.chat_id, document=document))
		
