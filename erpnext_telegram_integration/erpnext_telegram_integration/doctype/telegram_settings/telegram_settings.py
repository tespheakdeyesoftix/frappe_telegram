# -*- coding: utf-8 -*-
# Copyright (c) 2019, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import stat
from epos_restaurant_2023.api.printing import trim
import frappe
import telegram
import asyncio
from frappe.model.document import Document
from frappe.utils import get_url_to_form
from frappe.utils.data import quoted
from frappe import _
from bs4 import BeautifulSoup
from html2image import Html2Image
from datetime import datetime
from telegram.ext import Application
import base64
import io
import requests
import mimetypes
 

class TelegramSettings(Document):
	pass


@frappe.whitelist()

def send_to_telegram(telegram_user, message,print_format_template = None, reference_doctype=None, reference_name=None, attachment=None,sending_alert_as_image=0, estimate_image_height=5000,width=600,css="",caption=""):
	
	frappe.enqueue("erpnext_telegram_integration.erpnext_telegram_integration.doctype.telegram_settings.telegram_settings.send_to_telegram_queue",
				 queue='short', 
				 telegram_user=telegram_user,
				   message=message,
				   reference_doctype=reference_doctype,
				   reference_name=reference_name,
				   attachment=attachment,
				   sending_alert_as_image=sending_alert_as_image, 
				   estimate_image_height=estimate_image_height,
				   print_format_template = print_format_template,
				   width=width,
				   css=css,
				   caption=caption)
	# send_to_telegram_queue(
	# 	telegram_user=telegram_user,
	# 	message=message,
	# 	reference_doctype=reference_doctype,
	# 	reference_name=reference_name,
	# 	attachment=attachment,
	# 	sending_alert_as_image=sending_alert_as_image, 
	# 	estimate_image_height=estimate_image_height,
	# 	print_format_template = print_format_template,
	# 	width=width,
	# 	css=css,
	# 	caption=caption)



 # Decode Base64 and Send as Image

def base64_to_image(caption, base64_string,):	
	image_bytes = base64.b64decode(base64_string)
	image_io = io.BytesIO(image_bytes)
	image_io.name = "{}.jpg".format(caption)  # Required for Telegram API
	return image_io 

@frappe.whitelist()
def send_to_telegram_queue(telegram_user, message,print_format_template = None, reference_doctype=None, reference_name=None, attachment=None,sending_alert_as_image=0, estimate_image_height=5000,width=600,css="",caption=""):

	space = "\n" * 2
	telegram_chat_id = frappe.db.get_value('Telegram User Settings', telegram_user,'telegram_chat_id')
	telegram_settings = frappe.db.get_value('Telegram User Settings', telegram_user,'telegram_settings')
	telegram_token = frappe.db.get_value('Telegram Settings', telegram_settings,'telegram_token')
	timeout = frappe.db.get_value('Telegram User Settings', telegram_user,'time_out')
	application = Application.builder().token(telegram_token).read_timeout(timeout).connect_timeout(timeout).build()
	bot = application.bot
	if reference_doctype and reference_name:
		doc_url = get_url_to_form(reference_doctype, reference_name)
		telegram_doc_link =""# _("See the document at {0}").format(doc_url)

		if message:
			if sending_alert_as_image==0:
				# send pdf
				if print_format_template:
					from epos_restaurant_2023.api.printing import get_pdf_from_print_format
					pos_profile = None
					outlet = None
					meta = frappe.get_meta(reference_doctype)
					if meta.has_field("pos_profile") or  meta.has_field("outlet"):
						doc = frappe.get_doc(reference_doctype,reference_name)
						if meta.has_field("pos_profile"):
							pos_profile = 	doc.pos_profile		
						if 	 meta.has_field("outlet"):
							outlet = doc.outlet

					content_pdf = get_pdf_from_print_format(data = {
						"action" : "send telegram",                
						"doc": reference_doctype,
						"name":reference_name,
						"print_format": print_format_template,
						"pos_profile":pos_profile,
						"outlet":outlet,
						"letterhead":""
					}) 

					try:
						asyncio.run(bot.send_document(
							chat_id=telegram_chat_id,
							document=content_pdf,
							filename="{}({}).pdf".format(print_format_template,reference_name),
							caption="{} 📄".format(caption)
						)) 
						
					except Exception as e:
						if str(e)=="Timed out":
								frappe.get_doc({
									"doctype":"Telegram Notification Fail Log",
									"chat_id":telegram_chat_id,
									"error_message":str(frappe.as_json(e)),
									"message":message,
									"telegram_user":telegram_user,
									"css":css,
									"is_image":1,
									"noted":caption,
									"document_name":reference_name,
									"document_type":reference_doctype,
									"token":telegram_token
								}).insert()

				else:				
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
						# bot.send_message(chat_id=telegram_chat_id, text=message)
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

				if print_format_template:
					from epos_restaurant_2023.api.printing import print_from_print_format
					pos_profile = None
					outlet = None
					meta = frappe.get_meta(reference_doctype)
					if meta.has_field("pos_profile") or  meta.has_field("outlet"):
						doc = frappe.get_doc(reference_doctype,reference_name)
						if meta.has_field("pos_profile"):
							pos_profile = 	doc.pos_profile		
						if 	 meta.has_field("outlet"):
							outlet = doc.outlet

					image_base64 = print_from_print_format(data = {
						"action" : "send telegram",                
						"doc": reference_doctype,
						"name":reference_name,
						"print_format": print_format_template,
						"pos_profile":pos_profile,
						"outlet":outlet,
						"letterhead":""
					})

					image_io = base64_to_image(caption, image_base64)
					try:
						asyncio.run(bot.send_photo(chat_id=telegram_chat_id, photo=image_io,caption=caption))	
						
					except Exception as e:
						if str(e)=="Timed out":
								frappe.get_doc({
									"doctype":"Telegram Notification Fail Log",
									"chat_id":telegram_chat_id,
									"error_message":str(frappe.as_json(e)),
									"message":message,
									"telegram_user":telegram_user,
									"css":css,
									"is_image":1,
									"noted":caption,
									"document_name":reference_name,
									"document_type":reference_doctype,
									"token":telegram_token
								}).insert()

				else:
					image_path = generate_image(height=estimate_image_height,width=width, html=message, css= css,caption=caption)
					if image_path:
						try:
							asyncio.run(bot.send_photo(chat_id=telegram_chat_id, photo=open(image_path, 'rb'),caption=caption))
							# bot.send_photo(chat_id=telegram_chat_id, photo=open(image_path, 'rb'),caption=caption)					
							if os.path.isfile(image_path):
								os.remove(image_path)

						except Exception as e:
							if str(e)=="Timed out":
								frappe.get_doc({
									"doctype":"Telegram Notification Fail Log",
									"chat_id":telegram_chat_id,
									"error_message":str(frappe.as_json(e)),
									"message":message,
									"telegram_user":telegram_user,
									"css":css,
									"is_image":1,
									"noted":caption,
									"document_name":reference_name,
									"document_type":reference_doctype,
									"token":telegram_token
								}).insert()
	
	else:
		message = space + str(message) + space		
		# bot.send_message(chat_id=telegram_chat_id, text=message)
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
	data = frappe.db.sql("""
					  select name,
					  token, 
					  chat_id, 
					  message,
					  is_image,
					  css,
					  coalesce(note,'') note,
					  coalesce(document_type,'' ) document_type,
					  coalesce(document_name,'') document_name
					  from `tabTelegram Notification Fail Log` 
					  where status='Not Sent' order by creation""",as_dict=1)
	if data:
		for d in data:
			application = Application.builder().token(d["token"]).read_timeout(30).connect_timeout(30).build()
			bot = application.bot
			if d["document_type"] == "Sale" and d["document_name"] != "" and d["note"] == "":
				custom_bill_number = frappe.db.get_value('Sale', d["document_name"], 'custom_bill_number')
				d["note"] = custom_bill_number if custom_bill_number != "" else d["document_name"]
			if d["is_image"] == 1:
				image_path = generate_image(height=50000,width=600,html=d['message'], css= d["css"],caption=d["note"])
				if image_path:
					try:
						asyncio.run(bot.send_photo(chat_id=d["chat_id"], photo=open(image_path, 'rb'),caption=d["note"] or ""))
						if os.path.isfile(image_path):
							os.remove(image_path)
					except Exception as e:
						frappe.log_error(str(e))
			else:
				# bot.send_message(chat_id=d["chat_id"], text=d["message"])
				asyncio.run(bot.send_message(chat_id=d["chat_id"], text=d["message"]))			

			frappe.db.sql("update `tabTelegram Notification Fail Log` set status='Sent' where name='{}'".format(d["name"]))
		frappe.db.commit()

def generate_image(height,width,html,css,caption):
	chrome_path = "/usr/bin/google-chrome"
	# Set the CHROME_PATH environment variable
	os.environ['CHROME_PATH'] = chrome_path
	height = height 
	hti = Html2Image()
	hti.chrome_path=chrome_path
	hti.size=(width, height)

	css += """body{
        background:white;
    }"""  
	
	hash_generate = frappe.generate_hash(length=15)
	img_name =hash_generate # caption.lower().replace(' ','_').replace('-','_')

	now = datetime.now() 
	day_folder = now.strftime('%Y%m%d')
	directory = "{}/file/telegram/{}".format(frappe.get_site_path(),day_folder)
	if not os.path.exists(directory):
		os.makedirs(directory)
		# Set full permissions (read, write, execute for everyone)
		os.chmod(directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

	hti.output_path = directory
	hti.screenshot(html_str=html, css_str=css, save_as='{}.png'.format(img_name))  

	image_path = '{}/{}'.format(directory,'{}.png'.format(img_name))  
	trim(image_path)	 
	return image_path

def delete_telegram_folder():
	now = datetime.now() 
	current_day = now.strftime('%Y%m%d')
	directory = "{}/file/telegram".format(frappe.get_site_path())
	if os.path.exists(directory):
		all_entries = os.listdir(directory)
		folders = [entry for entry in all_entries if os.path.isdir(os.path.join(directory, entry) )] 
		for f in folders:
			if f != current_day:
				try:
					path = "{}/{}".format(directory, f)
					if os.path.exists(path):
						import shutil
						shutil.rmtree(path)
				except Exception as e:
					pass
		return "Folder Deleted"
	return "No folder"



### Whatsapp
@frappe.whitelist()
def send_to_whatsapp(telegram_user, message,print_format_template = None, reference_doctype=None, reference_name=None, attachment=None,sending_alert_as_image=0, estimate_image_height=5000,width=600,css="",caption=""):
	frappe.enqueue("erpnext_telegram_integration.erpnext_telegram_integration.doctype.telegram_settings.telegram_settings.send_to_whatsapp_queue",
				 queue='short', 
				 telegram_user=telegram_user,
				   message=message,
				   reference_doctype=reference_doctype,
				   reference_name=reference_name,
				   attachment=attachment,
				   sending_alert_as_image=sending_alert_as_image, 
				   estimate_image_height=estimate_image_height,
				   print_format_template = print_format_template,
				   width=width,
				   css=css,
				   caption=caption)
	return "In Queue"
	
@frappe.whitelist()
def send_to_whatsapp_queue(telegram_user, message,print_format_template = None, reference_doctype=None, reference_name=None, attachment=None,sending_alert_as_image=0, estimate_image_height=5000,width=600,css="",caption=""):
	data = frappe.db.get_value('Telegram User Settings', telegram_user, 
		['whatsapp_phone_number_id', 'whatsapp_to_number','telegram_settings', 'time_out'], as_dict=True)
	phone_number_id = data.whatsapp_phone_number_id
	to_number = data.whatsapp_to_number
	telegram_settings = data.telegram_settings 
	# return telegram_settings
	if phone_number_id and to_number:
		whatsapp_token = frappe.db.get_value('Telegram Settings', telegram_settings, 'whatsapp_token')
 
		if whatsapp_token: 	
			validate = send_message_validation(reference_doctype=reference_doctype, 
									reference_name=reference_name,
									sending_alert_as_image=sending_alert_as_image,
									print_format_template=print_format_template, 
									message=message,
									caption=caption, 
									attachment=attachment,
									height=estimate_image_height,
									width=width,
									css=css)

		 
			if validate:
				caption="{}{}".format(caption, "📄" if validate["type"]=="ducument" else"") 			 
				if validate["type"] == "document" or validate["type"] == "image":
					filename="{}({}).{}".format(print_format_template or caption,reference_name,"pdf" if validate["type"]=="document" else "jpeg"),
					return whatsapp_send_message(phone_number_id=phone_number_id, 
						   whatsapp_token=whatsapp_token, 
						   to_numbers=to_number, 
						   message_type=validate["type"],  
						   file_path=validate["file_path"],
						   file_data=validate["content"],
						   filename=filename,
						   caption=caption) 
				elif validate["type"] == "text":
					return whatsapp_send_message(phone_number_id=phone_number_id, 
						   whatsapp_token=whatsapp_token, 
						   to_numbers=to_number, 
						   message_type=validate["type"],  
						   file_path=None,
						   file_data=None,
						   filename=None,
						   caption=
						   validate["content"]) 
		  

def whatsapp_upload_document(phone_number_id,whatsapp_token, filename = None, file_path=None, file_data=None):	
	url = f"https://graph.facebook.com/v22.0/{phone_number_id}/media"
     # Auto detect MIME type based on file extension

	file_location = None
	if file_data and not file_path:
		# mime_type = file_data.get("mime_type")
		if isinstance(filename, tuple):
			filename = filename[0]
		
		now = datetime.now() 
		current_day = now.strftime('%Y%m%d')
		folder_path = "{}/file/telegram/{}".format(frappe.get_site_path(), current_day)  
		file_location = "{}/{}".format(folder_path, filename) 
		os.makedirs(folder_path, exist_ok=True)
		
		from io import BytesIO		
		if isinstance(file_data, BytesIO):			
			file_data.seek(0)
			with open(file_location, "wb") as f:
				f.write(file_data.read())

		else:
			with open(file_location, "wb") as f:
				f.write(file_data)
			

		mime_type = mimetypes.guess_type(file_location)[0] or 'application/octet-stream'
		files = {
			'file': (file_location.split('/')[-1], open(file_location, 'rb'), mime_type)
		} 

 
	if file_path:
		mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
		files = {
			'file': (file_path.split('/')[-1], open(file_path, 'rb'), mime_type)
		}
 
	data = {
		'messaging_product': 'whatsapp'
	}
	headers = {
		"Authorization": "Bearer {}".format(whatsapp_token)
	}
 
	try:
		response = requests.post(url, headers=headers, files=files, data=data)	
		if response.status_code == 200:
			if file_location:
				os.remove(file_location)			
			
			 
		return  response.json() 
	except Exception as e: 
		frappe.throw(str(e)) 

### filetype = image, document,text
def whatsapp_send_document(phone_number_id, whatsapp_token, to_numbers, media_id,message_type, filename,message):
		url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
		headers = {
			"Authorization": f"Bearer {whatsapp_token}",
			"Content-Type": "application/json"
		}
		recipients = to_numbers.split(",")
		responses =[]
		message_type_content = {
			"image": {
				"id": media_id,
				"caption":message
			},
			"document": {
				"id": media_id,
				"filename": filename,
				"caption":message
			},
			"text": {
				"body": message
			}
		}


		for recipient in recipients:
			if message_type == "text":
				long_message = message_type_content[message_type]["body"] 
				chunks = whatsapp_chunk_text(long_message)
				total = len(chunks)
				for i, chunk in enumerate(chunks, start=1):
					msg = f"====== Page {i}/{total} ========\n{chunk}" if total > 1 else chunk
					payload = {
						"messaging_product": "whatsapp",
						"to": recipient,
						"type": message_type,
						message_type:  {
							"body": msg
						}
					}
					resp = requests.post(url, headers=headers, json=payload)
					responses.append(resp.json())

			else:
				payload = {
					"messaging_product": "whatsapp",
					"to": recipient,
					"type": message_type,
					message_type:  message_type_content[message_type]
				}
				resp = requests.post(url, headers=headers, json=payload)
				responses.append(resp.json())
		return responses 
	
def whatsapp_chunk_text(text, max_len=4096):
	safe_max_len = max_len - 120
	return [text[i:i+safe_max_len] for i in range(0, len(text), safe_max_len)]


### filetype = image, document,text
@frappe.whitelist()
def whatsapp_send_message(phone_number_id, whatsapp_token, to_numbers,message_type,caption, filename = None, file_path = None,file_data = None):
	if isinstance(filename, tuple):
		filename = filename[0]

	if message_type in ["image","text", "document"]: 	

		media_id = "text"
		if message_type != "text":
			upload_result = whatsapp_upload_document(phone_number_id=phone_number_id, 
											whatsapp_token=whatsapp_token, 
											filename=filename,
											file_path=file_path,
											file_data=file_data)			
			media_id = upload_result.get("id")	
		# Step 2: Send Document
		if media_id:
			resp = whatsapp_send_document(phone_number_id, whatsapp_token, to_numbers, media_id,message_type, filename, caption)
			return resp

	frappe.throw("Invalid filetype (image, document, text)")


## send message validation
def send_message_validation(reference_doctype, reference_name,sending_alert_as_image,print_format_template, message,caption,attachment, height,width,css):
	space = "\n" * 2
	if reference_doctype and reference_name:
		if message:
			# doc_url = get_url_to_form(reference_doctype, reference_name)
			telegram_doc_link =""# _("See the document at {0}").format(doc_url) 
			if str(sending_alert_as_image) == "0":
				if print_format_template:
					from epos_restaurant_2023.api.printing import get_pdf_from_print_format
					pos_profile = None
					outlet = None
					meta = frappe.get_meta(reference_doctype)
					if meta.has_field("pos_profile") or  meta.has_field("outlet"):
						doc = frappe.get_doc(reference_doctype,reference_name)
						if meta.has_field("pos_profile"):
							pos_profile = 	doc.pos_profile		
						if 	 meta.has_field("outlet"):
							outlet = doc.outlet

					content_pdf = get_pdf_from_print_format(data = {
						"action" : "send telegram",                
						"doc": reference_doctype,
						"name":reference_name,
						"print_format": print_format_template,
						"pos_profile":pos_profile,
						"outlet":outlet,
						"letterhead":""
					})
					
					return {
						"type":"document",
						"content":content_pdf,
						"caption":caption
					}
				
				else:
					soup = BeautifulSoup(message)
					msg = soup.get_text('\n') + space + str(telegram_doc_link)
					if type(attachment) is str:
						attachment = int(attachment)
					else:
						if attachment:
							attachment = 1
					if attachment == 1:
						attachment_url =get_url_for_telegram(reference_doctype, reference_name)
						msg = msg + space +  attachment_url
					
					return {
						"type":"text",
						"content":"********* {} *********\n{}".format(caption,msg),
						"caption":"----------- {} ----------\n{}".format(caption,msg)
					}

			else:
				if print_format_template:
					from epos_restaurant_2023.api.printing import print_from_print_format
					pos_profile = None
					outlet = None
					meta = frappe.get_meta(reference_doctype)
					if meta.has_field("pos_profile") or  meta.has_field("outlet"):
						doc = frappe.get_doc(reference_doctype,reference_name)
						if meta.has_field("pos_profile"):
							pos_profile = 	doc.pos_profile		
						if 	 meta.has_field("outlet"):
							outlet = doc.outlet

					image_base64 = print_from_print_format(data = {
						"action" : "send telegram",                
						"doc": reference_doctype,
						"name":reference_name,
						"print_format": print_format_template,
						"pos_profile":pos_profile,
						"outlet":outlet,
						"letterhead":""
					})

					image_io = base64_to_image(caption, image_base64)
					return {
						"type":"image",
						"content":image_io,
						"caption":caption
					}
				else:
					image_path = generate_image(height=height,width=width, html=message, css= css,caption=caption)
					if image_path:
						return {
							"type":"image",
							"content":open(image_path, 'rb'),
							"caption":caption,
							"file_path":image_path
						}
					
					return False
		else:
			return False
	else:
		message = space + str(message) + space

		return {
			"type":"text",
			"content":message,
			"caption":caption,
		  }