# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from qp_middleware.qp_middleware.service.glosa.api_invoice_service import ApiInvoiceService
from qp_middleware.qp_middleware.service.glosa.api_glosa_service import ApiGlosaService
from qp_middleware.qp_middleware.service.glosa.exceptions import GlosaNotFoundError, ResponseStatusError, GlosaTypeLineError, GlosaObjectionLineError, InvoiceNotFoundError
import frappe
import json
GLOSA = "Glosa"
ERROR = "Error"
REITERACION = "Reiteración"

class qp_md_Glosa(Document):
	
	def execute_setup_glosa(self, nit_emisor, glosa_error_control):
     
		try:
			self.set_id_invoice_by_service(nit_emisor)

			tracking_glosa = self.get_tracking_glosa(glosa_error_control)
			
			self.order_glosas_lines()
			
			self.setup_glosa_line(tracking_glosa, glosa_error_control)
   
		except InvoiceNotFoundError as error:
			
			traceback = frappe.get_traceback()
			
			glosa_error_control.add_invoice_not_found_error(error, traceback)
   
		except ResponseStatusError as error:
        
			traceback = frappe.get_traceback()
		
			glosa_error_control.add_glosa_response_error(error, traceback)
   
		except Exception as error:
      
			traceback = frappe.get_traceback()
	  
			glosa_error_control.add_invoice_error_unknown(self.invoice_prefix, str(error), traceback)
   
	def get_tracking_glosa(self, glosa_error_control):
     
		tracking_glosa = ApiGlosaService(self.id_invoice)
		
		self.tracking_glosa_control(tracking_glosa.init_glosas, glosa_error_control)
		
		self.tracking_glosa_control(tracking_glosa.init_returns, glosa_error_control)

		return tracking_glosa
   
	def tracking_glosa_control(self, callback, glosa_error_control):
		
		try:
			
			callback()

		except GlosaNotFoundError as error:
      
			traceback = frappe.get_traceback()
	  
			glosa_error_control.add_glosa_error(error, traceback)

		except ResponseStatusError as error:
        
			traceback = frappe.get_traceback()
		
			glosa_error_control.add_glosa_response_error(error, traceback)
	
		except Exception as error:
      
			traceback = frappe.get_traceback()
	  
			glosa_error_control.add_invoice_error_unknown(self.invoice_prefix, str(error), traceback)
   
	
	def order_glosas_lines(self):
 		
		self.glosas.sort(key=lambda x: (x.registration_date, x.index_number))
  
	def set_id_factura(self, id_factura):
     
		self.id_invoice = id_factura
  
	def setup_glosa_line(self, tracking_glosa, glosa_error_control):
		
		for glosa_line in self.glosas:
	
			try:
	
				if not glosa_line.is_objection_type_valid():
		
					glosa_line.set_type_line(ERROR)

					glosa_line.set_is_verified(is_verified =  True)

					continue
	
				if not glosa_line.is_verified:
		
					self.__set_glosa_verified_and_status(glosa_line)

					glosa_external = self.setup_by_glosa_external(tracking_glosa, glosa_line)

					glosa_line.setup_by_glosa_external(glosa_external)
				
				if not glosa_line.is_sync:

					self.__send_glosa_petition(tracking_glosa, glosa_line, glosa_error_control)
			
			except GlosaNotFoundError as error:
       
				traceback = frappe.get_traceback()
	  
				glosa_error_control.add_glosa_error(error, traceback)
    
			except Exception as error:
       
				traceback = frappe.get_traceback()
	  
				glosa_error_control.add_glosa_error_unknown(self.invoice_prefix, str(error), traceback, glosa_id = glosa_line.index_number)

	def setup_by_glosa_external(self, tracking_glosa, glosa_line):
     
		if glosa_line.is_not_error():
      
			return tracking_glosa.get_last_glosa(glosa_line)
			
			#return tracking_glosa.search_glosa(glosa_line)
   
	def __set_glosa_verified_and_status(self, glosa_line):
    			
		glosa_line.set_is_verified(is_verified =  True)
			
		temp_status = GLOSA
		
		for glosa_line_aux in self.glosas:

			if glosa_line.index_number == glosa_line_aux.index_number:
				
				break
			
			same_base = (
				glosa_line.objection_type == glosa_line_aux.objection_type and
				glosa_line.claim_amount == glosa_line_aux.claim_amount and
				glosa_line.claim_code == glosa_line_aux.claim_code
			)
			
			if same_base:
				
				if glosa_line.notification_date == glosa_line_aux.notification_date:

					temp_status = ERROR

					break
				
				temp_status = REITERACION
						
		glosa_line.set_type_line(temp_status)
   
	def __send_glosa_petition(self, tracking_glosa, glosa_line, glosa_error_control):
		
		if glosa_line.is_response_valid():
      
			try:
       
				response, status, status_code = tracking_glosa.send_minsalud_response(glosa_line)
				
				self.__set_glosa_petition(glosa_line.index_number, glosa_line.get_payload(), status_code, status, response)

				self.set_is_sync_by_status_code(glosa_line, status_code)
    
			except (GlosaObjectionLineError) as error:
       
				traceback = frappe.get_traceback()
				
				glosa_error_control.add_glosa_error(error, traceback)

			except (GlosaTypeLineError) as error:
				traceback = frappe.get_traceback()

				glosa_error_control.add_glosa_error(error, traceback)

			except (ResponseStatusError) as error:
       
				traceback = frappe.get_traceback()

				glosa_error_control.add_glosa_error(error, traceback)

			except Exception as error:
       
				traceback = frappe.get_traceback()
    
				glosa_error_control.add_glosa_error_unknown(self.invoice_prefix, str(error), traceback, glosa_id = glosa_line.index_number)
    	
	def set_is_sync_by_status_code(self, glosa_line, status_code):
		
		if status_code == 200:
			
			glosa_line.set_is_sync()
   
	def __set_glosa_petition(self, index_number, payload, status_code, status, response):
           
			self.append("glosas_petition",{
				"payload": payload,
				"glosa_line_id": index_number,
				"status_code": status_code,
				"status": status,
				"response": json.dumps(response)
			})
   
	def set_id_invoice_by_service(self, nit_emisor):
    
		api_invoice_minsal = ApiInvoiceService(self.name, nit_emisor)

		invoice_id = api_invoice_minsal.get_id_invoice()
		
		self.set_id_invoice(invoice_id)
  
	def set_id_invoice(self, id_invoice):
	
		self.id_invoice = id_invoice