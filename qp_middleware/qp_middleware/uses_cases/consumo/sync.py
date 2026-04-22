import json
import frappe
from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import send_petition
from qp_middleware.qp_middleware.uses_cases.dimension_patient.sync import handler as sync_dimension
import math
from datetime import datetime
import traceback
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
                #queue='long',                
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
        consumos = frappe.get_list("qp_md_Consumo", filters = {"upload_id": upload_id, "is_valid": True, "is_sync": ["!=", True]}, fields = ["name", "request", "dimension_code", 'nombre'])

        send_consumos(consumos)

        set_consumoUploadStadistic(upload_id)


    except Exception as error:
        
        set_consumoUploadStadistic(upload_id, True)

        frappe.log_error(message=frappe.get_traceback(), title = "Sincronizacion de consumo: {}".format(upload_id))

    frappe.db.commit()

def set_consumoUploadStadistic(upload_id, error = False):

    sql = """
            select sum(is_sync) as count_sync, sum(is_error_sync)  as count_error, sum(is_error_connection) as count_error_connection from tabqp_md_Consumo where upload_id = '{}'
        """.format(upload_id)
    
    result = frappe.db.sql(sql,as_dict = True)

    if not error:

        error = result[0].get("count_error") > 0
    
        frappe.db.set_value('qp_md_ConsumoUpload', upload_id, 
                        {
                            'is_background': False,
                            'send_success': result[0].get("count_sync"),
                            'send_error': result[0].get("count_error"),
                            "is_error_sync": error,
                            "is_error_connection": result[0].get("count_error_connection") > 0,
                            "end_date": now()
                         })

def send_consumos(consumos):

    for consumo in consumos:

        dimension = sync_dimension(consumo.dimension_code, consumo.nombre)
        
        return_value = ""
        
        try:
            if dimension.is_sync:
            
                response, response_json, return_value, error = send_document([consumo.get("request")])

                error_response =  True if error or (return_value not in ("Registro exitosamente: -;", "Registro con exito;")) else False

                frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                        'response': response,
                        'return_value': return_value,
                        'is_sync': not error_response,
                        'is_error_sync': error_response,
                        'is_error_connection': False
                        
                })

            else: 
                frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                        'error': dimension.response,
                        'is_sync': False,
                        'is_error_sync': True,
                        'return_value': return_value,
                        'is_error_connection': False


                })

            frappe.db.commit()

        except Exception as error:
            traceback.print_exc()
            frappe.db.set_value('qp_md_Consumo', consumo.get("name"), {
                        'response': str(error),
                        'return_value': "",
                        'is_sync': False,
                        'is_error_sync': False,
                        'is_error_connection': True
                })


def send_document(payloads):

    #payloads = list(map(lambda consumo: consumo.get("request"), consumos))

    payload_xml = """<soap:Envelope xmlns:nav="urn:microsoft-dynamics-schemas/codeunit/registroDiarioProducto" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"> <soap:Body> <nav:registroDiarioProducto> <nav:diario>{}</nav:diario> </nav:registroDiarioProducto> </soap:Body> </soap:Envelope>""".format(payloads)
    
    payload_xml = payload_xml.replace("'","")

    endpoint_code = "create_consumo"
    
    response, response_json, error = send_petition(endpoint_code, payload_xml, add_header = True, is_json= False)
    
    response_value  = None
    
    is_error = True
          
    try:
        
        if not error:
            
            response_value = response_json.get("Soap:Envelope").get("Soap:Body").get("registroDiarioProducto_Result").get("return_value")
        
            is_error = False
        
    finally:
            
        return response, response_json, response_value, is_error
