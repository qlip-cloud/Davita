import frappe
import json
import requests
from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/DavitaContratos"

@frappe.whitelist()
def handler():
    
    response_json = get_response("list_contrats")

    id_cliente = tuple([ contract["idCliente"] for contract in response_json["value"]])

    result = frappe.get_list(doctype = "qp_md_Contract",  filters = {"id_cliente": ["in", id_cliente]}, pluck = 'id_cliente')

    new_contracts = list(filter(lambda x: x["idCliente"] not in result, response_json["value"]))
    
    values = []  

    for iter in new_contracts:
        
        values.append((iter['idContrato'], iter['idContrato'], iter['estadoContrato'],iter['estadoAprobacionContrato'], iter['idContratoPadre'], iter['idCliente'],
                       iter['numContactoCliente'], iter['tipoRegimen'], iter['fechaInicioContrato'],iter['fechaFinContrato'], iter['terminosPago'], iter['descuentoFinanciero'],
                       iter['idTipoContrato'], iter['tipoCliente'], iter['puntoFacturacion'],iter['comDescCondicionado'], now(), 'Administrator'))

    if new_contracts:

        table = "tabqp_md_Contract"

        fields = "(name, id_contrato, estado_contrato, estado_aprobacion_contrato, id_contrato_padre, id_cliente, num_contacto_cliente, tipo_regimen \
                    ,fecha_inicio_contrato, fecha_fin_contrato, terminos_pago, descuento_financiero, id_tipo_contrato, tipo_cliente, punto_facturacion \
                    ,com_desccondicionado, creation, owner)"
        
        persist(table, fields, values)

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(new_contracts)
    }

    