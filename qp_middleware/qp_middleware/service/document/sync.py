import frappe
import json
import math
from datetime import datetime
from qp_authorization.use_case.oauth2.authorize import get_token

from qp_middleware.qp_middleware.service.util.sync import send_petition

def handler(upload_xlsx, setup, enviroment):

    document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_xlsx.name})

    documents = []

    payloads = []

    for document_name in document_names:

        document = frappe.get_doc("qp_md_Document", document_name)

        payload = get_payload(document)

        document.request = json.dumps(payload)

        documents.append(document)

        payloads.append(payload)


    endpoint = frappe.get_doc("qp_md_Endpoint", "create_document")

    url = enviroment.get_url_ws_protocol(endpoint.url)

    #url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/WS/DAVITA/Codeunit/RegistrarFacturasVentaWS"

    #send_request(documents, setup, send_document, token, url)
    
    range_total = math.ceil(len(payloads) / setup.invoices_group)

    response_list = []

    for n in range(range_total):
        
        response, response_json, error = send_document(payloads[n * setup.invoices_group : (n+1) * setup.invoices_group], url)
        
        try:
            
            return_value = response_json["Soap:Envelope"]["Soap:Body"]["RegistrarFacturasVentaWS_Result"]["return_value"]
            
            list_split = return_value.split(";")
        
            del list_split[-1]

            list_split = list(map(lambda x: x.replace(" ", ""), list_split))

            response_list += list_split
        
        except:

            pass      
        

    is_complete = 0

    for key, document in enumerate(documents):

        try:

            int(response_list[key])

            document.document_code = response_list[key]

            document.is_complete = True

            is_complete +=1

            document.response = response

        except:
            
            document.response = response_list[key] if response_list and response_list[key] else response

        #if response_list[key] != "Error" and response_list[key] != "":
            
        #document.is_complete = True

        #document.document_code = response_list[key]


        document.save()

    frappe.db.commit()

    return {
        "send_success": is_complete,
        "send_error": len(documents) - is_complete
    }

def send_document(payload, url):

    token = get_token()

    payload_xml = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope  xmlns:nav="urn:microsoft-dynamics-schemas/codeunit/RegistrarFacturasVentaWS" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><nav:RegistrarFacturasVentaWS><nav:factura>{}</nav:factura></nav:RegistrarFacturasVentaWS></soap:Body></soap:Envelope>""".format(json.dumps(payload))
    
    payload_xml = payload_xml.replace("'","")
    
    #URL_HEADER = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/api/v2.0/companies(798ec2fe-ddfe-ed11-8f6e-6045bd3980fd)/salesInvoices"
    
    add_header = {
        "SOAPAction": "#POST"
    }

    response, response_json, error = send_petition(token, url, payload_xml, add_header = add_header, is_json= False)
    
    return response, response_json, error
    #document.response = response

    """if not error:
        
        document.document_code = response_json["number"]

        document.is_complete = True

    elif(document.is_complete):
        
        document.is_complete = False"""

def get_payload(document):

    customer_nit = document.customer_code.split("-")

    return {
        #"externalDocumentNumber": "API_Ex con dimensiones",
        "invoiceDate": datetime.strftime(document.posting_date, "%Y-%m-%d"),
        "postingDate": datetime.strftime(document.posting_date, "%Y-%m-%d"),
        "customerNumber": document.customer_code,
        "LHCPuntodefacturacion": document.lhc_punto_de_facturacion,
        "LHCContrato": document.lhc_contrato or "",
        "LHCCuotaModeradora": int(document.lhc_cuota_moderadora),
        "LHCCopago": int(document.lhc_copago),
        "LHCCuotaRecuperacion": int(document.lhc_cuota_recuperacion),
        "LHCPagosCompartidosPVS": int(document.lhc_pagos_compartidos_pvs),
        "LHCNumeroAutorizacion": document.lhc_numero_autorizacion if document.lhc_numero_autorizacion else "",
        "LHCPeriodoInicioFechaFact": document.lhc_periodo_inicio_fecha_fact,
        "LHCPeriodoFinFechaFact": document.lhc_periodo_fin_fecha_fact,
        "LHCNumeroContacto": document.lhc_numero_contacto,
        "LHCNumeroOrdenCompra": document.lhc_numero_orden_compra,
        "LHCConsecutivoInterno": document.lhc_consecutivo_interno,
        "LHCDocumento": document.lhc_documento,
        "LHCTipoOperacion": document.lhc_tipo_operacion_davita,
        "LHCTipoFacturaDoc": document.lhc_tipo_factura_doc,
        "LHCMIPRES": document.lhc_mipres,
        "LHCIDMIPRES": document.lhc_id_mipres,
        "LHCNoPoliza": document.lhc_no_poliza,
        "CurrencyCode": document.currency_code,
        "ResponsibilityCenter": document.responsibility_center,
        "WorkDescription": document.work_description,
        "ExternalDocumentNo": document.name,
        "dimensionSetLines": [
             {            
                "code": "TERCERO",            
                "valueCode": customer_nit[0]    
            },
            {            
                "code": "SEDE",            
                "valueCode": document.headquarter_code          
            },
            {       
                "code": "PACIENTE",            
                "valueCode": document.patient_code         
            },
            {      
                "code": "LIBRO",            
                "valueCode": "NCIF"        
            }
        ],

        "SalesInvoiceLine": get_items_payload(document)

    }

def get_items_payload(document):

    requests = []
    
    for key, item in enumerate(sorted(document.items, key=lambda x: x.line)):
    
        request = {
            "Document_Type": "Invoice",
            "Line_No": item.line,
            "Type": item.type_code,
            "No": item.item_code,
            "Quantity": int(item.quantity),            
            "Unit_of_Measure_Code": "UND",
            "Unit_Price": float(item.unit_price),
            "CantidadPBI": item.quantity_invoice,
            "Modalidad": item.modality_code
        }

        if item.type_code == "G/L Account":

            request.update({    
                "Line_Amount": float(item.line_amount)
            })

        requests.append(request)
        
    return requests