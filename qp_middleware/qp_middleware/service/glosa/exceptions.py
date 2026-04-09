# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

import frappe
from frappe import _


class InvoiceNotFoundError(Exception):
    """
    Excepción lanzada cuando una Factura no es encontrada en el servicio externo.
    """


    def __init__(self, invoice_id: str, description: str = "", endpoint: str = ""):
        self.invoice_id = invoice_id
        self.title = _("Factura No Encontrada")
        self.endpoint = endpoint
        self.description = description
        self.message = _("No se encontró la Factura con referencia '{0}'. Detalles: {1}").format(
            self.invoice_id, self.description
        )
        super().__init__(self.message)
        
class GlosaNotFoundError(Exception):
    """
    Excepción lanzada cuando una Glosa no es encontrada en el servicio externo.
    """

    def __init__(self, invoice_id: str,  description: str = "", endpoint: str = "", glosa_id: str = ""):
        self.invoice_id = invoice_id
        self.glosa_id = glosa_id
        self.title = _("Glosa No Encontrada")
        self.description = description
        self.endpoint = endpoint
        self.message = _("Error al conectar con el endpoint '{0}'. invoice_id: '{1}'. Glosa_id: '{2}'.").format(
            self.endpoint, self.invoice_id, self.glosa_id
        )
        super().__init__(self.message)
        
class ResponseStatusError(Exception):
    """
    Excepción lanzada cuando una Factura no es encontrada en el servicio externo.
    """

    def __init__(self, invoice_id: str, title: str = "", description: str = "", endpoint: str = "", glosa_id: str = ""):
        self.invoice_id = invoice_id
        self.glosa_id = glosa_id
        self.title = title
        self.description = description
        self.endpoint = endpoint
        self.message = _("Error al conectar con el endpoint '{0}'. invoice_id: '{1}'. Glosa_id: '{2}'.").format(
            self.endpoint, self.invoice_id, self.glosa_id
        )
        super().__init__(self.message)
        
class GlosaTypeLineError(Exception):
    
    def __init__(self, invoice_id: str, title: str = "", description: str = "", endpoint: str = "", glosa_id: str = ""):
        self.invoice_id = invoice_id
        self.glosa_id = glosa_id
        self.title = title
        self.description = description
        self.endpoint = endpoint
        self.message = _("Error al conectar con el endpoint '{0}'. invoice_id: '{1}'. Glosa_id: '{2}'.").format(
            self.endpoint, self.invoice_id, self.glosa_id
        )
        super().__init__(self.message)
        
class GlosaObjectionLineError(Exception):
    """
    Excepción lanzada cuando una Glosa no es encontrada en el servicio externo.
    """

    doctype = "qp_md_GlosaRequest"
    title = _("Glosa No Encontrada")

    def __init__(self, reference: str, description: str):
        self.reference = reference
        self.description = description
        self.message = _("No se encontró la Glosa con referencia '{0}'. Detalles: {1}").format(
            self.reference, self.description
        )
        super().__init__(self.message)