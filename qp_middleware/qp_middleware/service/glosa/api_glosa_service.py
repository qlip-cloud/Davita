import frappe
import json
from frappe.utils import flt
from qp_authorization.use_case.bearer.authorize import send_request_status
from qp_middleware.qp_middleware.service.glosa.exceptions import GlosaNotFoundError, ResponseStatusError, GlosaTypeLineError, GlosaObjectionLineError, GlosaTimeoutError, is_timeout_response
from qp_middleware.qp_middleware.service.glosa.api_invoice_service import get_glosa_timeout

DOCTYPE = "qp_md_GlosaLine"

class ApiGlosaService:
    
    def __init__(self, id_invoice):
        
        self.id_invoice = id_invoice
        self.doctype_base = DOCTYPE
        self.timeout = get_glosa_timeout()
        self.init_status()
        
    def init_status(self):
        
        self.status = {
            200: "Glosa enviada correctamente",
            400: "Datos inválidos",
            401: "No autorizado",
            403: "Acceso prohibido",
            404: "Seguimiento no encontrado",
            500: "Error interno del servidor (MINSAlUD)",
        }
        
        self.last_request_name = None
    
    def init_glosas(self):
        
        if self.id_invoice:  
            
            self.glosas = self.get_glosas_by_id_invoice()   
    
    def init_returns(self):
        
        if self.id_invoice:  
            
            self.returns = self.get_returns_by_id_invoice()
    
    def get_last_glosa(self, glosa_line):
        
        if glosa_line.is_objection_glosa() and hasattr(self, "glosas"):
            
            return self.glosas[-1] if self.glosas else None
        
        if glosa_line.is_objection_devolucion() and hasattr(self, "returns"):
            
            return self.returns[-1] if self.returns else None
        
        raise GlosaNotFoundError(self.id_invoice, endpoint = "get_last_glosa", glosa_id = glosa_line.index_number)
            
    def search_glosa(self, glosa_line, match_mode = "first"):
        
        records = self.__get_records_by_objection_type(glosa_line)
        
        matches = [glosa_iter for glosa_iter in records if self.__match_glosa(glosa_line, glosa_iter)]
        
        if not matches:
            
            return None
        
        return matches[-1] if match_mode == "last" else matches[0]
    
    def __get_records_by_objection_type(self, glosa_line):
        
        if glosa_line.is_objection_glosa():
            
            return getattr(self, "glosas", [])
        
        if glosa_line.is_objection_devolucion():
            
            return getattr(self, "returns", [])
        
        return []
    
    def __match_glosa(self, glosa_line, glosa_iter):
        
        if glosa_line.is_objection_glosa():
            
            return (
                flt(glosa_line.claim_amount) == flt(glosa_iter.gloss_value) and
                glosa_line.claim_code == glosa_iter.gloss_code_id and
                str(glosa_line.notification_date)[:10] == str(glosa_iter.formulation_date)[:10]
            )
        
        if glosa_line.is_objection_devolucion():
            
            return (
                flt(glosa_line.claim_amount) == flt(glosa_iter.return_value) and
                glosa_line.claim_code == glosa_iter.return_code_id and
                str(glosa_line.notification_date)[:10] == str(glosa_iter.formulation_date)[:10]
            )
        
        return False
        
    def get_glosas_by_id_invoice(self):
        
        #/api/SeguimientoFacturaGlosa/ByIdFactura GET
        endpoint = "get_glosas"
        
        query_param = f"IdFactura={self.id_invoice}"
        
        response, status, status_code = self.__send_request_status(endpoint, param = query_param, is_query_param = True)
        
        try:
                
            result = get_result(response, self.id_invoice, endpoint)
        
        except GlosaNotFoundError:
        
            self.__persist_no_info_request("qp_md_GlosaRequest", endpoint)
        
            raise
            
        return list(map(lambda glosa: self.__set_glosa_request(glosa), result))
            
    def get_returns_by_id_invoice(self):
        #/api/SeguimientoFacturaDevolucion/ByIdFactura GET
        endpoint = "get_returns"
        
        query_param = f"IdFactura={self.id_invoice}"
        
        response, status,status_code = self.__send_request_status(endpoint, param = query_param, is_query_param = True)
        
        try:
                
            result = get_result(response, self.id_invoice, endpoint)
        
        except GlosaNotFoundError:
        
            self.__persist_no_info_request("qp_md_ReturnRequest", endpoint)
        
            raise
            
        return list(map(lambda glosa: self.__set_return_request(glosa), result))
        
    def __persist_no_info_request(self, doctype, endpoint):
        
        existing_name = frappe.db.exists(doctype, {"invoice_id": self.id_invoice})
        
        if existing_name:
        
            request = frappe.get_doc(doctype, existing_name)
        
        else:
        
            request = frappe.new_doc(doctype)
        
        request.invoice_id = self.id_invoice
        
        request.save()
        
        self.last_request_name = request.name
        
    def send_minsalud_response(self, glosa_line):
                
        if glosa_line.objection_type.lower() == "Glosas".lower():
            
            if glosa_line.type_line.lower() == "Glosa".lower():
                
                return self.send_glosa(glosa_line)
            
            if glosa_line.type_line.lower() == "Reiteración".lower():
     
                return self.send_glosa_reiteracion(glosa_line)
                
            raise GlosaTypeLineError(self.id_invoice, glosa_line.get_title_type_line(), glosa_id=glosa_line.index_number)
            
        if glosa_line.objection_type.lower() == "DEVOLUCIONES".lower():
            
            if glosa_line.type_line.lower() == "Glosa".lower():
            
                return self.send_return(glosa_line)
        
            if glosa_line.type_line.lower() == "Reiteración".lower():
            
                return self.send_return_reiteracion(glosa_line)
            
            raise GlosaTypeLineError(self.id_invoice, glosa_line.get_title_type_line(), glosa_id=glosa_line.index_number)
        
        raise GlosaObjectionLineError(self.id_invoice, glosa_line.get_title_objection_type(), glosa_id=glosa_line.index_number)
        
    def send_glosa(self, glosa_line):
        #/api/SeguimientoFacturaGlosa/Respuesta PUT
        endpoint = "send_glosa"        
        
        return self.__send_request_status(endpoint, payload = glosa_line.get_payload(), glosa_id = glosa_line.index_number)
    
    def send_glosa_reiteracion(self, glosa_line):
        #/api/SeguimientoFacturaGlosa/ReiteracionRespuesta PUT
        endpoint = "send_glosa_reiteracion"        
        
        return self.__send_request_status(endpoint, payload = glosa_line.get_payload(), glosa_id = glosa_line.index_number)
    
    def send_return(self, glosa_line):
        #/api/SeguimientoFacturaDevolucion/Respuesta PUT
        endpoint = "send_return"        
        
        return self.__send_request_status(endpoint, payload = glosa_line.get_payload(), glosa_id = glosa_line.index_number)
    
    def send_return_reiteracion(self, glosa_line):
        #/api/SeguimientoFacturaDevolucion/ReiteracionRespuesta PUT
        endpoint = "send_return_reiteracion"        
        
        return self.__send_request_status(endpoint, payload = glosa_line.get_payload(), glosa_id = glosa_line.index_number)
                        
    def __send_request_status(self, endpoint, payload = "", param = "", glosa_id = "", is_query_param = False):
        
        response, status_code = send_request_status(endpoint, payload = payload, param = param, is_query_param = is_query_param, timeout = self.timeout)
        
        self.assert_that_status_code_valid(response, status_code, glosa_id, endpoint)
        
        status = self.status.get(status_code, "Estado no definido")
        
        if status_code != 200 and is_already_responded(response):
            
            status = "Glosa ya respondida en MINSALUD"
        
        return response, status, status_code
    
    def assert_that_status_code_valid(self, response, status_code, glosa_id, endpoint):

        if is_timeout_response(response):
            
            raise GlosaTimeoutError(self.id_invoice, str(response), endpoint, glosa_id)
        
        if status_code != 200 and not is_already_responded(response):
            
            raise ResponseStatusError(self.id_invoice, self.status.get(status_code, "Error desconocido"), str(response), endpoint, glosa_id)
        
    def __set_return_request(self, return_data):
        
        return_request = frappe.new_doc("qp_md_ReturnRequest")
        
        return_request.load_from_external_json(return_data)
        
        return return_request
    
    def __set_glosa_request(self, glosa):
        
        glosa_request = frappe.new_doc("qp_md_GlosaRequest")
        
        glosa_request.load_from_external_json(glosa)
        
        return glosa_request
    
def get_result(response, id_invoice, endpoint):
    
    if not response or "resultado" not in response or not response.get("resultado"):
        
        raise GlosaNotFoundError(id_invoice, endpoint = endpoint)
    
    return response.get("resultado")

ALREADY_RESPONDED_MESSAGE = "ya tiene un registro previo de respuesta"

def is_already_responded(response):
    
    if not response:
        
        return False
    
    errors = response.get("errors")
    
    if not errors:
        
        return False
    
    if isinstance(errors, dict):
        
        errors = list(errors.values())
    
    text = json.dumps(errors)
    
    return ALREADY_RESPONDED_MESSAGE in text
