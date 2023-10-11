from qp_authorization.use_case.oauth2.authorize import get_token
import frappe
import time
import json
from datetime import datetime
import requests
import threading

def handler(upload_xlsx):


    document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_xlsx.name})

    documents = []

    for document_name in document_names:

        document = frappe.get_doc("qp_md_Document", document_name)

        document.request = get_header_payload(document)

        documents.append(document)
    
    setup = frappe.get_doc("qp_md_Setup")

    token = get_token()

    send_request(documents, setup, send_header, token)

    for document in documents:

        if document.is_complete:
        
            document.update_request = get_update_header_payload(document)

            for item in document.items:
                
                item.document_code = document.document_code

                item.request = get_item_payload(item)

    token = get_token()

    send_request(documents,setup, send_update_header, token)

    token = get_token()

    for document in documents:
        
        if document.is_complete:
            
            send_request(document.items, setup, send_item, token)
    
    is_complete = 0

    for document in documents:

        list_complete = set(list(map(lambda x: x.is_complete, document.items)))

        if False in list_complete:

            document.is_complete = False

        if document.is_complete:

            is_complete +=1

        document.save()

    frappe.db.commit()

    return {
        "send_success": is_complete,
        "send_error": len(documents) - is_complete
    }

def callback(document,threads, setup, target, token):

    if threading.active_count() <= setup.number_request:
        
        t = threading.Thread(target=target, args=(document, token))

        threads.append(t)

        t.start()
    
    else:
        
        time.sleep(setup.wait_time)

        callback(document,threads, setup, target, token)

def send_request(documents, setup, target, token):

    setup = frappe.get_doc("qp_md_Setup")

    threads = list()

    for document in documents:
        
        callback(document,threads, setup, target, token)
    
    for t in threads:
        
        t.join()

def send_update_header(document, token):

    if document.is_complete:
    
        url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company('DAVITA')/SalesInvoice('Invoice', '{}')".format(document.document_code)
        
        add_header = {
            'If-Match': '*'
        }
        
        response, response_json, error = send_petition(token, url, document.update_request, "PATCH", add_header)

        document.update_response = response

        if error and document.is_complete:
            
            document.is_complete = False

def send_header(document, token):

    URL_HEADER = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/api/v2.0/companies(798ec2fe-ddfe-ed11-8f6e-6045bd3980fd)/salesInvoices"
    
    response, response_json, error = send_petition(token, URL_HEADER, document.request)

    document.response = response

    if not error:
        
        document.document_code = response_json["number"]

        document.is_complete = True

    elif(document.is_complete):
        
        document.is_complete = False


def send_item(item, token):

    URL_LINE = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/SalesInvoiceLine"
    
    response, response_json, error = send_petition(token, URL_LINE, item.request)

    item.response = response
        
    item.is_complete = False if error else True

def get_header_payload(document):

    return json.dumps({
        "externalDocumentNumber": "API_Ex con dimensiones",
        "invoiceDate": datetime.strftime(document.posting_date, "%Y-%m-%d"),
        "postingDate": datetime.strftime(document.posting_date, "%Y-%m-%d"),
        "customerNumber": document.customer_code,
        "shortcutDimension1Code": document.customer_code,
        "shortcutDimension2Code": document.headquarter_code,   
        "dimensionSetLines": [
            {            
                "code": "MODALIDADES",            
                "valueCode": "AG"           
            },
            {       
                "code": "PACIENTE",            
                "valueCode": document.patient_code         
            }
        ]
    })

def get_update_header_payload(document):

    return json.dumps({   
        #"LHCPuntodefacturacion": document.lhc_punto_de_facturacion,
        "LHCContrato": document.lhc_contrato or "",
        "LHCCuotaModeradora": int(document.lhc_cuota_moderadora),
        "LHCCopago": int(document.lhc_copago),
        "LHCCuotaRecuperacion": int(document.lhc_cuota_recuperacion),
        "LHCPagosCompartidosPVS": int(document.lhc_pagos_compartidos_pvs),
        "LHCNumeroAutorizacion": document.lhc_numero_autorizacion,
        "LHCPeriodoInicioFechaFact": document.lhc_periodo_inicio_fecha_fact,
        "LHCPeriodoFinFechaFact": document.lhc_periodo_fin_fecha_fact,
        "LHCNumeroContacto": document.lhc_numero_contacto,
        "LHCNumeroOrdenCompra": document.lhc_numero_orden_compra,
        "LHCConsecutivoInterno": document.lhc_consecutivo_interno,
        "LHCDocumento": document.lhc_documento,
        "LHCTipoOperacion": document.lhc_tipo_operacion_davita,
        "LHCTipoFacturaDoc": document.lhc_tipo_factura_doc
    })

def get_item_payload(item):
    
    request = {
        "Document_Type": "Invoice",
        "Document_No": item.document_code,
        "Line_No": item.line,
        "Type": item.type_code,
        "FilteredTypeField": item.type_code,
        "No": item.item_code,
        "Quantity": int(item.quantity),            
        "Shortcut_Dimension_1_Code": item.customer_code,
        "Shortcut_Dimension_2_Code": item.headquarter_code,
        "ShortcutDimCode3": "",
        "ShortcutDimCode4": "",
        "ShortcutDimCode5": item.patient_code,
        "ShortcutDimCode6": item.modality_code,
        "ShortcutDimCode7": "",
        "ShortcutDimCode8": ""
    }

    if item.type_code == "G/L Account":

        request.update({    
            "Unit_Price": float(item.unit_price),
            "Line_Amount": float(item.line_amount)
        })
    
    return json.dumps(request)

def send_petition(token, url, payload, method = "POST", add_header = None):
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }

    if add_header:

        headers.update(add_header)

    response = requests.request(method, url, headers=headers, data=payload)

    response_json = json.loads(response.text)

    return response.text, response_json, "error" in response_json

@frappe.whitelist()
def confirm(upload_id):

    document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_id, "is_complete": True, 'is_confirm': False})

    documents = []

    for document_name in document_names:

        document = frappe.get_doc("qp_md_Document", document_name)

        document.confirm_request = get_confirm_payload(document)

        documents.append(document)
    
    setup = frappe.get_doc("qp_md_Setup")

    token = get_token()

    send_request(documents, setup, send_confirm, token)

    success = 0

    for document in documents:

        if document.is_confirm:

            success += 1    

        document.save()
    
    frappe.db.commit()

    return {
        'status': 200,
        "total": len(documents),
        "success": success,
        'error': len(documents) - success
    }
def get_confirm_payload(document):

    return json.dumps({
        "no": document.document_code
    })

def send_confirm(document, token):

    url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/DavitaRegistroDocumentoWS_RegistrarFacturaVenta"
    
    add_header = {
            'If-Match': '*',
            'company': '798ec2fe-ddfe-ed11-8f6e-6045bd3980fd'
    }
        
    response, response_json, error = send_petition(token, url, document.confirm_request, add_header = add_header)

    document.confirm_response = response

    if not error:
        
        document.document_confirm = response_json["value"]

        document.is_confirm = True