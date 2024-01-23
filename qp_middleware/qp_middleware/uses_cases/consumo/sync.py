import json
import frappe
from frappe.utils import now
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
    frappe.db.set_value('qp_md_ConsumoUpload', upload_id, 
                        {
                            'is_background': True, 
                            'start_date': now() 
                        })
    
    frappe.enqueue(
                sync,
                queue='long',                
                is_async=True,
                #now=True,
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
        consumos = frappe.get_list("qp_md_Consumo", filters = {"upload_id": upload_id, "is_valid": True}, fields = ["name", "request", "dimension_code", 'nombre'])

        send_consumos(consumos)

        set_consumoUploadStadistic(upload_id)


    except Exception as error:
        
        set_consumoUploadStadistic(upload_id, True)


    frappe.db.commit()

def set_consumoUploadStadistic(upload_id, error = False):

    sql = """
            select sum(is_sync) as count_sync, sum(is_error_sync)  as count_error from tabqp_md_Consumo where upload_id = '{}'
        """.format(upload_id)
    
    result = frappe.db.sql(sql,as_dict = True)

    frappe.db.set_value('qp_md_ConsumoUpload', upload_id, 
                        {
                            'is_background': False,
                            'send_success': result[0].get("count_sync"),
                            'send_error': result[0].get("count_error"),
                            "is_error_sync": error,
                            "end_date": now()
                         })


def send_consumos(consumos):

    consumo_url = get_urls()

    for consumo in consumos:

        dimension = sync_dimension(consumo.dimension_code, consumo.nombre)
        
        return_value = ""
        
        if dimension.is_sync:
            
            response, response_json, return_value, error = send_document([consumo.get("request")], consumo_url)

            error_response =  True if error or (return_value not in ("Registro exitosamente: -;", "Registro con exito;"))else False

            frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                    'response': response,
                    'return_value': return_value,
                    'is_sync': not error_response,
                    'is_error_sync': error_response
            })

        else: 
            frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                    'error': dimension.response,
                    'is_sync': False,
                    'is_error_sync': True,
                    'return_value': return_value

            })

        frappe.db.commit()

def get_urls():

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    enpoint = frappe.get_doc("qp_md_Endpoint", "create_consumo")

    return enviroment.get_url_ws_protocol(enpoint.url)



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
                
            return response, response_json, "",True

    return response, response_json, response_value, False
