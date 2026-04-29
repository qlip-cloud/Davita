# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class qp_md_ReturnRequest(Document):
    
	def load_from_external_json(self, data):

		self.gloss_tracking_id = data.get("idSeguimientoFacturaGlosa")
		self.invoice_id = data.get("idFactura")
		self.return_value = data.get("valorDevolucion")
		self.observation = data.get("observacion")
		self.return_code_id = data.get("idSeguimientoTipoCodigoDevolucion")
		self.return_code_description = data.get("descripcionSeguimientoTipoCodigoDevolucion")
		self.formulation_date = data.get("fechaFormulacion")
		self.report_date = data.get("fechaReporte")
		self.report_user = data.get("usuarioReporte")
		self.response_code_id = data.get("idSeguimientoTipoCodigoRespuesta")
		self.response_code_description = data.get("descripcionSeguimientoTipoCodigoRespuesta")
		self.response_observation = data.get("observacionRespuesta")
		self.response_date = data.get("fechaRespuesta")
		self.response_report_user = data.get("usuarioReporteRespuesta")
		self.response_report_date = data.get("fechaReporteRespuesta")
		self.reiteration_return_code_id = data.get("idSeguimientoTipoCodigoDevolucionReiteracion")
		self.reiteration_return_code_description = data.get("descripcionSeguimientoTipoCodigoDevolucionReiteracion")
		self.reiteration_observation = data.get("observacionReiteracion")
		self.reiteration_return_formulation_date = data.get("fechaFormulacionDevolucionReiteracion")
		self.reiteration_return_report_date = data.get("fechaReporteDevolucionReiteracion")
		self.reiteration_return_report_user = data.get("usuarioReporteDevolucionReiteracion")
		self.reiteration_return_response_code_id = data.get("idSeguimientoTipoCodigoDevolucionReiteracionRespuesta")
		self.reiteration_return_response_code_description = data.get("descripcionSeguimientoTipoCodigoDevolucionReiteracionRespuesta")
		self.reiteration_return_response_observation = data.get("observacionReiteracionRespuesta")
		self.reiteration_return_response_formulation_date = data.get("fechaFormulacionDevolucionReiteracionRespuesta")
		self.reiteration_return_response_report_date = data.get("fechaReporteDevolucionReiteracionRespuesta")
		self.reiteration_return_response_report_user = data.get("usuarioReporteDevolucionReiteracionRespuesta")
		self.attachment = data.get("anexo")
		

