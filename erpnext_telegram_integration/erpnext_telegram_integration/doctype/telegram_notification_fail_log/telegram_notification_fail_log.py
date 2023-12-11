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
	# 	asyncio.run(bot.send_message(chat_id=self.chat_id, text=self.message))
		
