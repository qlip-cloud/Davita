# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class qp_md_GlosaError(Document):
	

	def add_invoice_not_found_error(self, error, traceback):
     
		self.set_line_error(error.title, error.invoice_id, error.message, traceback, additional= error.description)
  
		self.count_invoice_not_found_total()
  
	def add_invoice_response_error(self, error, traceback):
	 
		self.set_line_error(error.title, error.invoice_id, error.message, traceback, additional= error.description)

		self.count_invoice_response_total()
	
	def add_glosa_error(self, error, traceback):
     
		self.set_line_error(error.title, error.invoice_id, error.message, traceback, glosa_id = error.glosa_id, additional= error.description)
  
		self.count_glosa_error_total()
  
	def add_glosa_not_found_error(self, error, traceback):
     
		self.set_line_error(error.title, error.invoice_id, error.message, traceback, glosa_id = error.glosa_id, additional= error.description)
  
		self.count_glosa_not_found_total()
  
	def add_glosa_response_error(self, error, traceback):
	 
		self.set_line_error(error.title, error.invoice_id, error.message, traceback, glosa_id = error.glosa_id, additional= error.description)

		self.count_glosa_response_total()
	
	def add_glosa_error_unknown(self, invoice_id, message, traceback, glosa_id = None):
	 
		self.set_line_error("GlosaErrorUnknown", invoice_id, message, traceback, glosa_id = glosa_id)
  
		self.count_glosa_error_total()
 
	def add_invoice_error_unknown(self, invoice_id, message, traceback):
     
		self.set_line_error("InvoiceErrorUnknown", invoice_id, message, traceback)
  
		self.count_unknow_error_total()
  
	def set_line_error(self, title, invoice_id, message, traceback, glosa_id = None, additional = None):
     
		self.append("lines", {
			"title": title,
			"invoice_id": invoice_id,
			"glosa_id": glosa_id,
			"message": message,
			"traceback": traceback,
			"additional": additional
		})
	
	
	def count_invoice_total(self):
     
		self.invoice_total += 1
	
	def count_unknow_error_total(self):
     
		self.count_error_total()
		
		self.unknow_error_total += 1
  
	def count_glosa_error_total(self):
     
		self.count_error_total()
  
		self.glosa_error_total += 1
  
	def count_invoice_not_found_total(self):
     
		self.count_error_total()
  
		self.invoice_not_found_total += 1
  
	def count_glosa_response_total(self):
     
		self.count_error_total()
  
		self.glosa_response_error_total += 1
  
	def count_glosa_not_found_total(self):
     
		self.count_error_total()
  
		self.glosa_not_found_total += 1

	def count_invoice_response_total(self):
     
		self.count_error_total()
  
		self.invoice_response_error_total += 1
  
	def count_error_total(self):
	 
		self.error_total += 1

	def count_error_total(self):
	 
		self.error_total += 1