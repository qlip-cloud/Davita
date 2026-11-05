import frappe
from qp_authorization.use_case.bearer.authorize import send_request_status
from qp_middleware.qp_middleware.service.glosa.exceptions import InvoiceNotFoundError, ResponseStatusError, GlosaTimeoutError, is_timeout_response

GLOSA_TIMEOUT_DEFAULT = 30

def get_glosa_timeout():
    
    setup = frappe.get_all("qp_md_Setup", fields = ["glosa_timeout"], limit = 1)
    
    value = setup[0].get("glosa_timeout") if setup else None
    
    return value or GLOSA_TIMEOUT_DEFAULT

class ApiInvoiceService:
    
    def __init__(self, invoice_prefix, nit_emisor):
        self.invoice_prefix = invoice_prefix
        self.nit_emisor = nit_emisor
        self.timeout = get_glosa_timeout()
        self.status = {
            200: "Lista paginada de facturas obtenida exitosamente",
            400: "Parámetros de consulta inválidos.",
            401: "No autorizado",
            500: "Error interno del servidor (MINSAlUD)",
        }
        self.init_invoice()
        

    def init_invoice(self):
        
        if self.invoice_prefix:  
            
            self.invoice = self.get_invoice_by_number_invoice()
            
    def get_id_invoice(self):
        
        if self.invoice:
            
            return self.invoice.invoice_id
        
        return None
            
    def get_invoice_by_number_invoice(self):
        
        #/api/Factura?NumeroFactura=9839&NitEmisor=string$NumeroPagina=1&RegistrosPorPagina=1 GET
        
        endpoint = "get_invoice"
        
        query_param = f"NumeroFactura={self.invoice_prefix}&NitEmisor={self.nit_emisor}"
        
        response, status_code = send_request_status(endpoint, param = query_param, is_query_param = True, timeout = self.timeout)
        
        self.assert_that_status_code_valid(response, status_code, endpoint)
            
        result = get_result(response, self.invoice_prefix)
            
        return self.__set_invoice_request(result[0])

    def __set_invoice_request(self, invoice):
        
        invoice_request = frappe.new_doc("qp_md_InvoiceRequest")
        
        invoice_request.load_from_external_json(invoice)
        invoice_request.save()
        return invoice_request
    
    def assert_that_status_code_valid(self, response, status_code, endpoint):
    
        if is_timeout_response(response):
        
            raise GlosaTimeoutError(self.invoice_prefix, str(response), endpoint)
    
        if status_code != 200:
        
            raise ResponseStatusError(self.invoice_prefix, self.status.get(status_code, "Error desconocido"), str(response), endpoint)
    
def get_result(invoice_response, invoice_prefix):
    
    if "resultado" not in invoice_response or not invoice_response.get("resultado"):
        
        raise InvoiceNotFoundError(invoice_id=invoice_prefix)
    
    return invoice_response.get("resultado")