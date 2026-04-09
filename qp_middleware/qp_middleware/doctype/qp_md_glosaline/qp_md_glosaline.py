# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import json
ERROR = "Error"
GLOSA = "GLOSAS"
REITERACION = "REITERACION"
DEVOLUCION = "DEVOLUCION"
class qp_md_GlosaLine(Document):
    
	def is_not_error(self):
     
		return self.type_line != ERROR

	def set_is_verified(self, is_verified):
     
		self.is_verified = is_verified
  
	def set_type_line(self, type_line):
		
		self.type_line = type_line
      
	def setup_by_glosa_external(self, glosa_external):
     
		if glosa_external:
	
			self.set_id_glosa(glosa_external.gloss_tracking_id)

			self.set_payload()
  
	def set_id_glosa(self, id_glosa):
    	
		self.id_glosa = id_glosa
    
	def set_payload(self):
    
		self.payload = json.dumps({
			"idSeguimientoFacturaGlosa": self.id_glosa,
			"idSeguimientoTipoCodigoRespuesta": self.response_code,
			"observacionRespuesta": self.response_details,
			"fechaRespuesta": self.get_erp_response_date_str()
		})
	def get_title_type_line(self):
     
		return f"Tipo de línea no válida objection_type: {self.objection_type}  type_line :{self.type_line}"

	def get_title_objection_type(self):
     
		return f"Tipo de línea no válida objection_type: {self.objection_type}"

	def get_payload(self):
     
		return self.payload

	def get_erp_response_date_str(self):
		
		return self.erp_response_date.strftime("%Y-%m-%dT%H:%M:%S.000+00:00") if self.erp_response_date else None

	def set_is_sync(self):
	 
		self.is_sync = True
  
	def is_response_valid(self):
	 
		return self.is_not_error() and self.id_glosa and not self.is_sync

	def is_objection_type_valid(self):
		
		return self.objection_type.lower() in [GLOSA.lower(), DEVOLUCION.lower()]

	def is_objection_glosa(self):
		
		return self.objection_type.lower() == GLOSA.lower()

	def is_objection_devolucion(self):
		
		return self.objection_type.lower() == DEVOLUCION.lower()
