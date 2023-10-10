from qp_authorization.use_case.oauth2.authorize import get_token
import frappe
import time
import json
from datetime import datetime
import requests
import threading
TOKEN = get_token()
def handler(upload_xlsx, method):

    document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_xlsx.name})

    documents = []

    for document_name in document_names:

        document = frappe.get_doc("qp_md_Document", document_name)

        document.request = get_header_payload(document)

        documents.append(document)
    
    setup = frappe.get_doc("qp_md_Setup")
    
    send_request(documents, setup, send_header)

    for document in documents:

        document.update_request = get_update_header_payload(document)

        for item in document.items:
            
            item.document_code = document.document_code
            item.request = get_item_payload(item)

    send_request(documents,setup, send_update_header)        
    for document in documents:

        for item in document.items:
            
            send_request(document.items, setup, send_item)

    for document in documents:

        document.save()

    frappe.db.commit()

def callback(document,threads, setup, target):

    if threading.active_count() <= setup.number_request:
        
        t = threading.Thread(target=target, args=(document, ))
        threads.append(t)
        t.start()
    
    else:
        
        time.sleep(setup.wait_time)

        callback(document,threads, setup, target)

def send_request(documents, setup, target):

    setup = frappe.get_doc("qp_md_Setup")

    threads = list()

    for document in documents:
        
        callback(document,threads, setup, target)
    
    for t in threads:
        
        t.join()

def send_update_header(document):

    url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company('DAVITA')/SalesInvoice('Invoice', '{}')".format(document.document_code)
    
    add_header = {
        'If-Match': '*'
    }
    
    response, response_json, error = send_petition(url, document.update_request, "PATCH", add_header)

    document.update_response = response

    if error and document.is_complete:
        
        document.is_complete = False

def send_header(document):

    URL_HEADER = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/api/v2.0/companies(798ec2fe-ddfe-ed11-8f6e-6045bd3980fd)/salesInvoices"
    
    response, response_json, error = send_petition(URL_HEADER, document.request)

    document.response = response

    if not error:
        
        document.document_code = response_json["number"]

    elif(document.is_complete):
        
        document.is_complete = False


def send_item(item):

    URL_LINE = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/SalesInvoiceLine"
    
    response, response_json, error = send_petition(URL_LINE, item.request)

    item.response = response

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
        "LHCDocumento": document.lhc_documento  
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
            "Unit_Price": item.unit_price,
            "Line_Amount": item.line_amount
        })
    
    return json.dumps(request)

def send_petition(url, payload, method = "POST", add_header = None):

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(TOKEN)
    }

    if add_header:

        headers.update(add_header)

    response = requests.request(method, url, headers=headers, data=payload)

    response_json = json.loads(response.text)

    return response.text, response_json, "error" in response_json