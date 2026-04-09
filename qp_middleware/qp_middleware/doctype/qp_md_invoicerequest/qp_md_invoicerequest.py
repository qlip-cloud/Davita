# Copyright (c) 2026, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

TYPE_LINE = {
	"adquiriente": "buyer",
	"emisor": "issuer"
}
class qp_md_InvoiceRequest(Document):
    
	def load_from_external_json(self, data):
		
		self.issuer_invoice_id = data.get("idFacturaEmisor")
		self.buyer_invoice_id = data.get("idFacturaAdquiriente")
		self.invoice_id = data.get("idFactura")
		self.invoice_number = data.get("numeroFactura")
		self.invoice_type = data.get("tipoFactura")
		self.issue_date = data.get("fechaEmision")
		self.issue_time = data.get("horaEmision")
		self.due_date = data.get("fechaVencimiento")
		self.cufe = data.get("cufe")
		self.total_gross_value = data.get("totalValorBruto")
		self.total_taxable_base_value = data.get("totalValorBaseImponible")
		self.total_discount = data.get("descuentoTotal")
		self.total_charge = data.get("cargoTotal")
		self.total_advance_payment = data.get("anticipoTotal")
		self.invoice_value = data.get("valorFactura")
		self.total_gross_value_attributes = data.get("totalValorBrutoAtributos")
		self.invoice_currency = data.get("divisaFactura")
		self.profile_execution_id_2 = data.get("profileexecutionid2")
		self.operation_type_indicator = data.get("indicadorTipoOperacion")
		self.item_count = data.get("numeroElementos")
		self.append("lines", self._map_entity(data, "adquiriente"))
		self.append("lines", self._map_entity(data, "emisor"))

	def _map_entity(self, data, entity_type):
     
		entity_data = data.get(entity_type.lower(), {})

		return {
			"legal_name": entity_data.get("razonSocial"),
			"person_type": entity_data.get("tipoPersona"),
			"commercial_name": entity_data.get("nombreComercial"),
			"nit": entity_data.get(f"nit{entity_type.capitalize()}"),
			"type_line": TYPE_LINE[entity_type]
		}
