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
                            'return_start_date': now() 
                        })
    frappe.enqueue(
                sync,
                #queue='long',                
                is_async=True,
                #now=True,
                job_name="send_sync_consumo_return: "+ upload_id,
                timeout=5400000,
                upload_id = upload_id
                )
    
    return {
            "status": 200,
            "msg": "Se ha iniciado el proceso en segundo plano"
        }
    
def sync(upload_id):

    try:
           
        consumos = get_consumo(upload_id)
        
        send_consumos(consumos)

    except Exception as error:
        
        set_consumoUploadStadistic(upload_id, True)

        frappe.log_error(message=frappe.get_traceback(), title = "Sincronizacion de consumo: {}".format(upload_id))
        
    set_consumoUploadStadistic(upload_id)

    frappe.db.commit()

def get_consumo(upload_id):
    
    fields = ["name", "est_adm","id_unico","ingreso","tipo_identificacion","identificacion","nombre","responsable_eps","fecha_ordenamiento","codigo_medicamento","descripcion_medicamento","justificacion_observaciones","posologia","cantidad_solicitada","codigo_unidad","descripcion_unidad","codigo_estado","descripcion_estado","codigo_ubicacion","descripcion_ubicacion","upload_id","request","headquarter_dynamic","dimension_code","item_dynamic","error","is_valid"]
    
    return frappe.get_list("qp_md_Consumo", filters = {"upload_id": upload_id, "response": ["like", "%Registro con exito;%"], "is_returned": False, "is_return": False}, fields = fields, limit = 100)

def set_consumoUploadStadistic(upload_id, error = False):

    sql = """
            SELECT 
                COALESCE(SUM(is_return), 0) AS total,
                COALESCE(SUM(CASE WHEN is_error_sync = 1 or is_error_connection = 1 THEN 1 ELSE 0 END), 0) AS count_errors_both,
                COALESCE(SUM(CASE WHEN is_error_sync = 0 AND is_error_connection = 0 THEN 1 ELSE 0 END), 0) AS count_success
            FROM `tabqp_md_Consumo`
            WHERE upload_id = '{}' AND is_return = 1;
        """.format(upload_id)
    
    result = frappe.db.sql(sql,as_dict = True)

    frappe.db.set_value('qp_md_ConsumoUpload', upload_id, {
        'is_background': False,
        'return_success': result[0].get("count_success"),
        'return_error': result[0].get("count_errors_both"),
        'return_end_date': now() 
    })
    
    frappe.db.commit()

def send_consumos(consumos):
    
    for consumo_iter in consumos:
        
        consumo_iter = dict(consumo_iter)
        
        consumo_iter.update({"doctype": "qp_md_Consumo", "is_return" : True})
        
        consumo = frappe.get_doc(consumo_iter)
        
        consumo.return_root = consumo.name
                
        consumo.name = None
        
        request = json.loads(consumo.request)

        request.update({"EntryType": "Positive Adjmt."})
        
        consumo.request = json.dumps(request)
                
        control_document(consumo)
        
        consumo.insert()
        
    frappe.db.commit()

def control_document(consumo):

    try:

        response, response_json, return_value, error = send_document([consumo.request])
        
        error_response =  True if error or (return_value not in ("Registro exitosamente: -;", "Registro con exito;")) else False
        
        consumo.response =  response
        consumo.return_value =  return_value
        consumo.is_sync =  not error_response
        consumo.is_error_sync =  error_response
        consumo.is_error_connection =  False
        frappe.db.set_value('qp_md_Consumo', consumo.return_root, 'is_returned', True)
        
    except Exception as error:
        
        consumo.response = str(error)
        consumo.return_value = ""
        consumo.is_sync = False
        consumo.is_error_sync = False
        consumo.is_error_connection = True

def send_document(payloads):

    #payloads = list(map(lambda consumo: consumo.get("request"), consumos))

    payload_xml = """<soap:Envelope xmlns:nav="urn:microsoft-dynamics-schemas/codeunit/registroDiarioProducto" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"> <soap:Body> <nav:registroDiarioProducto> <nav:diario>{}</nav:diario> </nav:registroDiarioProducto> </soap:Body> </soap:Envelope>""".format(payloads)
    
    payload_xml = payload_xml.replace("'","")

    endpoint_code = "create_consumo"
    
    response, response_json, error = send_petition(endpoint_code, payload_xml, add_header = True, is_json= False)
    
    response_value = None
    
    is_error = False
    
    try:
        
        if not error:
            
            response_value = response_json.get("Soap:Envelope").get("Soap:Body").get("registroDiarioProducto_Result").get("return_value")
            
            is_error = False
    except Exception as error:
        
        frappe.log_error(message=traceback.format_exc(), title="Error en conversión respuesta recibida")    
        
    finally:
            
        return response, response_json, response_value, is_error
