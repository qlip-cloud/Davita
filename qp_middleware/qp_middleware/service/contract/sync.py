import frappe
import json
import requests

from qp_authorization.use_case.oauth2.authorize import get_token

URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/DavitaContratos"

payload = ""

@frappe.whitelist()
def handler():
    
    token = get_token()
    
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    response = requests.get(URL, headers=headers, data=payload)

    response_json = json.loads(response.text)

    contract_id = tuple([ contract["idContrato"] for contract in response_json["value"]])

    result = frappe.get_list(doctype = "qp_md_Contract",  filters = {"id_contrato": ["in", contract_id]}, pluck = 'id_contrato')

    new_contracts = list(filter(lambda x: x["idContrato"] not in result, response_json["value"]))
    
    for iter in new_contracts:
        
        contract = frappe.new_doc('qp_md_Contract')
        contract.id_contrato = iter['idContrato']
        contract.estado_contrato = iter['estadoContrato']
        contract.estado_aprobacion_contrato = iter['estadoAprobacionContrato']
        contract.id_contrato_padre = iter['idContratoPadre']
        contract.id_cliente = iter['idCliente']
        contract.num_contacto_cliente = iter['numContactoCliente']
        contract.tipo_regimen = iter['tipoRegimen']
        contract.fecha_inicio_contrato = iter['fechaInicioContrato']
        contract.fecha_fin_contrato = iter['fechaFinContrato']
        contract.terminos_pago = iter['terminosPago']
        contract.descuento_financiero = iter['descuentoFinanciero']
        contract.id_tipo_contrato = iter['idTipoContrato']
        contract.tipo_cliente = iter['tipoCliente']
        contract.punto_facturacion = iter['puntoFacturacion']
        contract.com_desccondicionado = iter['comDescCondicionado']

        contract.insert()

    if new_contracts:

        frappe.db.commit()

    return new_contracts