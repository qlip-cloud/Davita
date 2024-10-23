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


    endpoint = frappe.get_doc("qp_md_Endpoint", "create_multipatient_document")

    url = enviroment.get_url_ws_protocol(endpoint.url)

    #url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/WS/DAVITA/Codeunit/RegistrarFacturasVentaWS"

    #send_request(documents, setup, send_document, token, url)
    
    range_total = math.ceil(len(payloads) / setup.invoices_group)

    response_list = []

    for n in range(range_total):
        
        response, response_json, error = send_document(payloads, url)
        
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

    payload_xml = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope  xmlns:nav="urn:microsoft-dynamics-schemas/codeunit/SWCrearFacturasVenta" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><nav:SWCrearFacturasVenta><nav:factura>{}</nav:factura></nav:SWCrearFacturasVenta></soap:Body></soap:Envelope>""".format(json.dumps(payload))
    
    payload_xml = payload_xml.replace("'","")
        
    add_header = {
        "SOAPAction": "#POST"
    }

    response, response_json, error = send_petition(token, url, payload_xml, add_header = add_header, is_json= False)
    
    return response, response_json, error


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
        "dimensionSetLines": get_dimensions_payload(document),
        "SalesInvoiceLine": get_sales_invoices_payload(document),
        "Paciente": get_patients_payload(document)
        

    }

def get_sales_invoices_payload(document):

    requests = []
    
    for key, sale_invoice in enumerate(sorted(document.sales_invoices, key=lambda x: x.line_no)):
    
        request = {
            "Line_No": sale_invoice.line_no,
            "Type": sale_invoice.type,
            "No": sale_invoice.no,
            "Quantity": int(sale_invoice.quantity),            
            "Unit_of_Measure_Code": sale_invoice.unit_of_measure_code,
            "Unit_Price": float(sale_invoice.unit_price),
            "CantidadPBI": sale_invoice.cantidadpbi,
            "Modalidad": sale_invoice.modality or ""
        }

        requests.append(request)
        
    return requests

def get_dimensions_payload(document):

    requests = []
    
    for key, dimension in enumerate(document.dimensions):
    
        request = {
            "code": dimension.code,
            "valueCode": dimension.value_code            
        }

        requests.append(request)
        
    return requests

def get_patients_payload(document):

    requests = []
    
    for key, patient in enumerate(document.patients):
    
        request = {
            "NoIdentificacion": patient.no_identification,
            "TipoIdentificacion": patient.tipo_identification,
            "NoAutorizacion": patient.no_authorization or "",
            "LHCMIPRES": patient.lhc_mipres or "",
            "LHCIDMIPRES": patient.lhc_id_mipres or "",
            "LHCNoPoliza": patient.lhc_no_poliza or "",
            "SedePaciente": patient.patient_headquarter or "",
            "ModalidadPaciente": patient.patient_modality or "",
            "Producto": patient.item_code,
            "Cantidad": patient.quantity
        }

        requests.append(request)
        
    return requests