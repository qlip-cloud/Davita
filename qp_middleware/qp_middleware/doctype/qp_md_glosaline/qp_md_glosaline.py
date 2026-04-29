# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import json
ERROR = "Error"
GLOSA = "Glosa"
GLOSAS = "GLOSAS"
REITERACION = "REITERACION"
DEVOLUCIONES = "DEVOLUCIONES"
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
		
		self.payload = json.dumps(self.get_payload_type())
  
	def get_payload_type(self):
     
		dictionary ={
			GLOSAS: {
				GLOSA: {
            		"id_glosa": "idSeguimientoFacturaGlosa",
					"response_code": "idSeguimientoTipoCodigoRespuesta",
					"observacion_respuesta": "observacionRespuesta",
					"fecha_respuesta": "fechaRespuesta"
              	},
				REITERACION: {
					"id_glosa": "idSeguimientoFacturaGlosa",
					"response_code": "idSeguimientoTipoCodigoGlosaReiteracion",
					"observacion_respuesta": "observacionReiteracion",
					"fecha_respuesta": "fechaFormulacionGlosaReiteracion"
				}
			},
   
			DEVOLUCIONES: {
				GLOSA: {
					"id_glosa": "idSeguimientoFacturaDevolucion",
					"response_code": "idSeguimientoTipoCodigoRespuesta",
					"observacion_respuesta": "observacionRespuesta",
					"fecha_respuesta": "fechaRespuesta"
				},
				REITERACION: {
					"id_glosa": "idSeguimientoFacturaDevolucion",
					"response_code": "idSeguimientoTipoCodigoGlosaReiteracion",
					"observacion_respuesta": "observacionReiteracion",
					"fecha_respuesta": "fechaFormulacionGlosaReiteracion"
				}
			}
		}
     
		if self.is_objection_type_valid() and self.is_type_line_valid():

			dictionay_key = dictionary[self.objection_type][self.type_line]
   
			return { 
           		"command": {
					dictionay_key["id_glosa"]: self.id_glosa,
					dictionay_key["response_code"]: self.response_code,
					dictionay_key["observacion_respuesta"]: self.response_details,
					dictionay_key["fecha_respuesta"]: self.get_erp_response_date_str()
				}
           	}

	def get_title_type_line(self):
     
		return f"Tipo de línea no válida objection_type: {self.objection_type}  type_line :{self.type_line}"

	def get_title_objection_type(self):
     
		return f"Tipo de línea no válida objection_type: {self.objection_type}"

	def get_payload(self):
     
		return json.loads(self.payload)

	def get_erp_response_date_str(self):
		
		return self.erp_response_date.strftime("%Y-%m-%dT%H:%M:%S.000Z") if self.erp_response_date else None

	def set_is_sync(self):
	 
		self.is_sync = True
  
	def is_response_valid(self):
	 
		return self.is_not_error() and self.id_glosa and not self.is_sync

	def is_objection_type_valid(self):
		
		return self.objection_type.lower() in [GLOSAS.lower(), DEVOLUCIONES.lower()]

	def is_type_line_valid(self):
		
		return self.type_line.lower() in [GLOSA.lower(), REITERACION.lower()]

	def is_objection_glosa(self):
		
		return self.objection_type.lower() == GLOSAS.lower()

	def is_objection_devolucion(self):
		
		return self.objection_type.lower() == DEVOLUCIONES.lower()
