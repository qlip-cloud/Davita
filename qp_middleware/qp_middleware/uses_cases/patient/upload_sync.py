import frappe
from qp_middleware.qp_middleware.service.util.sync import send_petition
from qp_authorization.use_case.oauth2.authorize import get_token

@frappe.whitelist()
def handler():
    frappe.enqueue(
                sync,
                queue='long',                
                is_async=True,
                job_name="send patient",
                timeout=5400000,
                )
    
    return {
        "status": 202
    }
    
def sync():
    patients = frappe.get_list("qp_md_Patient", {"is_sync": False})
    
    url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/DavitaCrearPaciente"

    for patient_iter in patients:

        token = get_token()

        patient = frappe.get_doc("qp_md_Patient", patient_iter.name)
        
        response, response_json, error = send_petition(token, url, patient.request)

        patient.response = response

        if not error:

            patient.is_sync = True

        patient.save()

        frappe.db.commit()

    
