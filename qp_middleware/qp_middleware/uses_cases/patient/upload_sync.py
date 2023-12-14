import frappe
from qp_middleware.qp_middleware.service.util.sync import send_petition
from qp_authorization.use_case.oauth2.authorize import get_token
from frappe.utils import now

@frappe.whitelist()
def handler():

    
    patients = frappe.get_list("qp_md_Patient", {"is_sync": False,"origin": ["!=","Import"]})
    
    sync_log = frappe.new_doc("qp_md_PatientSyncLog")
    
    sync_log.total = len(patients)
        
    sync_log.is_background = True

    sync_log.insert()

    frappe.enqueue(
        sync,
        queue='long',                
        is_async=True,
        job_name="send patient",
        timeout=5400000,
        sync_log=sync_log,
        patients = patients
    )
    
    
    frappe.db.commit()

    return {
        "status": 202,
        "msg": "Esta actividad se ejecutara en segundo plano, para informacion del proceso consulte el qp_md_PatientSyncLog: {}".format(sync_log.name)
    }
    
def sync(sync_log, patients):

    sync_log.start_date = now()

    try:

        patient_url, dimension_url=  get_urls()

        for patient_iter in patients:

            try:
                
                token = get_token()
                
                patient = frappe.get_doc("qp_md_Patient", patient_iter.name)

                sync_patient(patient, token, sync_log, patient_url)

                sync_dimension(patient, token, sync_log, dimension_url)

            except:
                
                pass
            
            sync_log.save()

            patient.save()

            frappe.db.commit()
    
    except:

        sync_log.error = frappe.get_traceback()

    sync_log.is_background = False
        
    sync_log.end_date = now()

    sync_log.save()

    frappe.db.commit()

def get_urls():

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    enpoint = frappe.get_doc("qp_md_Endpoint", "patient_create")

    patient_url = enviroment.get_url_with_company(enpoint.url)

    enpoint = frappe.get_doc("qp_md_Endpoint", "dimension_create")

    dimension_url = enviroment.get_url_with_company(enpoint.url)

    return patient_url, dimension_url

def sync_dimension(patient, token, sync_log, url):

    response, response_json, error = send_petition(token, url, patient.request_dimension)

    patient.response_dimension = response

    if error:
        
        if response_json.get("error").get("code") != 'Internal_EntityWithSameKeyExists':

            sync_log.dimension_error += 1
        
            patient.is_sync = False

            raise Exception("Error creando dimension")
        
        sync_log.dimension_repeated += 1

    else:
        
        sync_log.dimension_created += 1
    
def sync_patient(patient, token, sync_log, url):

    if not patient.created_sync:
            
        response, response_json, error = send_petition(token, url, patient.request)

        patient.response = response

        if error: 
            
            if response_json.get("error").get("code") != 'Internal_EntityWithSameKeyExists'  :

                sync_log.patient_error += 1

                raise Exception("Error creando paciente")
            
            sync_log.patient_repeated += 1

        else:
            
            sync_log.patient_created += 1
        
        patient.is_sync = True

        patient.created_sync = True