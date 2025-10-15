import frappe
import json
import math
from datetime import datetime
from qp_authorization.use_case.oauth2.authorize import get_token
from qp_middleware.qp_middleware.service.util.sync import send_petition

def handler(upload_xlsx, setup, enviroment):
    
    document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_xlsx.name, "is_valid": True})
    
    range_total = math.ceil(len(document_names) / setup.invoices_group)
    
    endpoint = frappe.get_doc("qp_md_Endpoint", "create_document")

    url = enviroment.get_url_ws_protocol(endpoint.url)
    
    count_complete = 0

    for n in range(range_total):

        documents = []
        
        payloads = []
        
        page_start = n * setup.invoices_group
        
        page_end = (n+1) * setup.invoices_group
        
        for document_name in document_names[page_start: page_end]:
            
            document = frappe.get_doc("qp_md_Document", document_name)

            payload = get_payload(document)

            document.request = json.dumps(payload)

            documents.append(document)

            payloads.append(payload)
                    
        try:
            response, response_json, error = send_document(payloads, url)
                        
            return_value = get_return_value(response_json)
            
            list_split = get_list_split(return_value)
                        
            count_complete += update_document_lot(documents, list_split, response, error)
        
        except Exception as e:
            
            frappe.log_error(message = str(e), title = f"Error en sincronizacion: {upload_xlsx.name}")
            message = response + str(e)
            update_document_lot(documents, [], message, True)

    frappe.db.commit()

    return {
        "send_success": count_complete,
        "send_error": len(document_names) - count_complete
    }
    
def get_return_value(response_json):
    
    if  "Soap:Envelope" in response_json:
        if "Soap:Body" in response_json["Soap:Envelope"]:
            if "RegistrarFacturasVentaWS_Result" in response_json["Soap:Envelope"]["Soap:Body"]:
                if "return_value" in response_json["Soap:Envelope"]["Soap:Body"]["RegistrarFacturasVentaWS_Result"]:
                    return response_json["Soap:Envelope"]["Soap:Body"]["RegistrarFacturasVentaWS_Result"]["return_value"]
    
    raise Exception("\n\nError en conversión respuesta recibida")
    
def get_list_split(return_value):
            
    list_split = return_value.split(";")

    del list_split[-1]

    return list(map(lambda x: x.replace(" ", ""), list_split))
            
def update_document_lot(documents_lot, list_split, response, error):
    
    count_complete = 0
        
    for key, document in enumerate(documents_lot):
                
        document.response = response
        
        if  not error and len(documents_lot) == len(list_split):
            
            try:

                int(list_split[key])

                document.document_code = list_split[key]

                document.is_complete = True

                count_complete +=1

            except:
                            
                document.response += f"\n\n Error al asignar codigo, valor asignado:{list_split[key]}"
        else:
            if len(documents_lot) != len(list_split):
                
                document.response += f"\n\n Error en proceso: el numero de respuesta no es igual al esperado. Esperado:{len(documents_lot)} recibidos {len(list_split)}"
                
            else:
                document.response += f"\n\n Error en respuesta recibida"
            
            
            
        document.save()
        
    return count_complete

def send_document(payload, url):

    token = get_token()

    payload_xml = """<?xml version="1.0" encoding="utf-8"?><soap:Envelope  xmlns:nav="urn:microsoft-dynamics-schemas/codeunit/RegistrarFacturasVentaWS" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><nav:RegistrarFacturasVentaWS><nav:factura>{}</nav:factura></nav:RegistrarFacturasVentaWS></soap:Body></soap:Envelope>""".format(json.dumps(payload))
    
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