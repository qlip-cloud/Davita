import json
import frappe
from qp_authorization.use_case.oauth2.authorize import get_token
from qp_middleware.qp_middleware.service.util.sync import send_petition
from qp_middleware.qp_middleware.uses_cases.dimension_patient.sync import handler as sync_dimension

import math


@frappe.whitelist()
def handler(upload_id):

    upload = frappe.get_doc("qp_md_ConsumoUpload",upload_id)

    if upload.is_background:

        return {
            "status": 500,
            "msg": "Ya existe una confirmacion en proceso"
        }
    upload.is_background = True
    
    upload.save()
    
    frappe.enqueue(
                sync,
                queue='long',                
                is_sync=True,
                job_name="send sync consumo: "+ upload_id,
                timeout=5400000,
                upload_id = upload_id
                )
    
    return {
            "status": 200,
            "msg": "Se ha iniciado el proceso en segundo plano"
        }

def sync(upload_id):

    try:                      
        consumos = frappe.get_list("qp_md_Consumo", filters = {"upload_id": upload_id, "is_valid": True}, fields = ["name", "request", "dimension_code"])

        send_consumos(consumos)

        set_consumoUploadStadistic(upload_id)


    except Exception as error:
        pass

    frappe.db.commit()

def set_consumoUploadStadistic(upload_id):

    sql = """
            select sum(is_sync) as count_sync, sum(is_error_sync)  as count_error from tabqp_md_Consumo where upload_id = '{}'
        """.format(upload_id)
    
    result = frappe.db.sql(sql,as_dict = True)

    frappe.db.set_value('qp_md_ConsumoUpload', upload_id, 
                        {
                            'is_background': False,
                            'send_success': result[0].get("count_sync"),
                            'send_error': result[0].get("count_error"),
                         })


def send_consumos(consumos):

    consumo_url = get_urls()

    for consumo in consumos:

        dimension = sync_dimension(consumo.dimension_code)

        if dimension.is_sync:
            
            response, response_json, error = send_document([consumo.get("request")], consumo_url)

            frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                    'response': response,
                    'is_sync': False if error else True,
                    'is_error_sync': True if error else False
            })

        else: 
            frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                    'error': dimension.response,
                    'is_sync': False,
                    'is_error_sync': True
            })

        frappe.db.commit()

def get_urls():

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    enpoint = frappe.get_doc("qp_md_Endpoint", "create_consumo")

    return enviroment.get_url_ws_protocol(enpoint.url)

"""
def send_consumos(consumos, enviroment, endpoint, setup):

    url = enviroment.get_url_ws_protocol(endpoint.url)

    range_total = math.ceil(len(consumos) / setup.invoices_group)

    response_list = []

    for n in range(range_total):
        
        response, response_json, error = send_document(consumos[n * setup.invoices_group : (n+1) * setup.invoices_group], url)
        
        try:
            
            return_value = response_json["Soap:Envelope"]["Soap:Body"]["RegistrarFacturasVentaWS_Result"]["return_value"]
            
            list_split = return_value.split(";")
        
            del list_split[-1]

            list_split = list(map(lambda x: x.replace(" ", ""), list_split))

            response_list += list_split
        
        except:

            pass      

    is_complete = 0

    for key, document in enumerate(consumos):

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
    }"""

def send_document(payloads, url):

    #payloads = list(map(lambda consumo: consumo.get("request"), consumos))

    token = get_token()

    payload_xml = """<soap:Envelope xmlns:nav="urn:microsoft-dynamics-schemas/codeunit/registroDiarioProducto" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"> <soap:Body> <nav:registroDiarioProducto> <nav:diario>{}</nav:diario> </nav:registroDiarioProducto> </soap:Body> </soap:Envelope>""".format(payloads)
    
    payload_xml = payload_xml.replace("'","")
    
    #URL_HEADER = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/api/v2.0/companies(798ec2fe-ddfe-ed11-8f6e-6045bd3980fd)/salesInvoices"
    
    add_header = {
        "SOAPAction": "#POST"
    }

    response, response_json, error = send_petition(token, url, payload_xml, add_header = add_header, is_json= False)
    
    if not error:
        
        try:

            response_value = response_json.get("Soap:Envelope").get("Soap:Body").get("registroDiarioProducto_Result").get("return_value")

        except Exception as error:
                
            return response, response_json, True

    return response, response_json, False
