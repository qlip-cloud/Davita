# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class qp_md_GlosaRequest(Document):
	
	def load_from_external_json(self, data):

		
		self.gloss_tracking_id = data.get("idSeguimientoFacturaGlosa")
		self.invoice_id = data.get("idFactura")
		self.user_id = data.get("idUsuario")
		self.gloss_value = data.get("valorGlosa")
		self.attachment = data.get("anexo")
		self.observation = data.get("observacion")
		self.report_date = data.get("fechaReporte")
		self.report_user = data.get("usuarioReporte")
		self.formulation_date = data.get("fechaFormulacion")
		self.gloss_code_id = data.get("idSeguimientoTipoCodigoGlosa")
		self.gloss_code_description = data.get("descripcionSeguimientoTipoCodigoGlosa")
		self.response_date = data.get("fechaRespuesta")
		self.response_observation = data.get("observacionRespuesta")
		self.response_code_id = data.get("idSeguimientoTipoCodigoRespuesta")
		self.response_code_description = data.get("descripcionSeguimientoTipoCodigoRespuesta")
		self.response_report_date = data.get("fechaReporteRespuesta")
		self.response_report_user = data.get("usuarioReporteRespuesta")
		self.reiteration_gloss_code_id = data.get("idSeguimientoTipoCodigoGlosaReiteracion")
		self.reiteration_gloss_code_description = data.get("descripcionSeguimientoTipoCodigoGlosaReiteracion")
		self.reiteration_gloss_report_date = data.get("fechaReporteGlosaReiteracion")
		self.reiteration_gloss_report_user = data.get("usuarioReporteGlosaReiteracion")
		self.reiteration_gloss_formulation_date = data.get("fechaFormulacionGlosaReiteracion")
		self.reiteration_observation = data.get("observacionReiteracion")
		self.reiteration_gloss_response_code_id = data.get("idSeguimientoTipoCodigoGlosaReiteracionRespuesta")
		self.reiteration_gloss_response_code_description = data.get("descripcionSeguimientoTipoCodigoGlosaReiteracionRespuesta")
		self.reiteration_gloss_response_report_date = data.get("fechaReporteGlosaReiteracionRespuesta")
		self.reiteration_gloss_response_report_user = data.get("usuarioReporteGlosaReiteracionRespuesta")
		self.reiteration_gloss_response_formulation_date = data.get("fechaFormulacionGlosaReiteracionRespuesta")
		self.reiteration_response_observation = data.get("observacionReiteracionRespuesta")
		self.medication_id = data.get("idMedicamento")
		self.procedure_id = data.get("idProcedimiento")
		self.emergency_id = data.get("idUrgencia")
		self.consultation_id = data.get("idConsulta")
		self.hospitalization_id = data.get("idHospitalizacion")
		self.newborn_id = data.get("idRecienNacido")
		self.other_service_id = data.get("idOtroServicio")