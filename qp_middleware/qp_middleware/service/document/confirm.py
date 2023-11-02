from qp_authorization.use_case.oauth2.authorize import get_token
from qp_middleware.qp_middleware.service.util.sync import send_petition, send_request

import json
import frappe

@frappe.whitelist()
def handler(upload_id):

    document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_id, "is_complete": True, 'is_confirm': False})

    documents = []

    for document_name in document_names:

        document = frappe.get_doc("qp_md_Document", document_name)

        document.confirm_request = get_confirm_payload(document)

        documents.append(document)
    
    setup = frappe.get_doc("qp_md_Setup")

    token = get_token()
    url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/DavitaRegistrarFacturasVentasSW_RegistrarFacturaVenta"

    send_request(documents, setup, send_confirm, token, url)

    success = 0

    for document in documents:

        if document.is_confirm:

            success += 1    

        document.save()
    
    frappe.db.commit()

    return {
        'status': 200,
        "total": len(documents),
        "success": success,
        'error': len(documents) - success
    }
def get_confirm_payload(document):

    return json.dumps({
        "no": document.document_code
    })

def send_confirm(document, token, url):

    #url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/DavitaRegistroDocumentoWS_RegistrarFacturaVenta"

    
    add_header = {
            'If-Match': '*',
            'company': '798ec2fe-ddfe-ed11-8f6e-6045bd3980fd'
    }
        
    response, response_json, error = send_petition(token, url, document.confirm_request, add_header = add_header)

    document.confirm_response = response

    if not error:
        
        document.document_confirm = response_json["value"]

        document.is_confirm = True