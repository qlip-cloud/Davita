from qp_authorization.use_case.oauth2.authorize import get_token
from qp_middleware.qp_middleware.service.util.sync import send_petition, get_enviroment

import json
import frappe

@frappe.whitelist()
def handler(upload_id):

    upload = frappe.get_doc("qp_md_upload_xlsx",upload_id)

    if upload.is_background:

        return {
            "status": 500,
            "msg": "Ya existe una confirmacion en proceso"
        }
    
    frappe.db.set_value('qp_md_upload_xlsx', upload_id, 'is_background', True)
    
    frappe.db.commit()
    
    frappe.enqueue(
                confirm,
                queue='long',                
                now=True,
                #is_async=True,
                job_name="send confirm: "+ upload_id,
                timeout=5400000,
                upload_id = upload_id
                )
    
    return {
            "status": 200,
            "msg": "Se ha iniciado el proceso en segundo plano"
        }

def confirm(upload_id):

    try:
        enviroment, endpoint = get_enviroment("confirm_document")

        url = enviroment.get_url_without_company(endpoint.url)

        document_names = frappe.get_list("qp_md_Document", {"upload_id": upload_id, "is_complete": True, 'is_confirm': False})

        for document_name in document_names:

            document = frappe.get_doc("qp_md_Document", document_name)

            document.confirm_request = get_confirm_payload(document)

            send_confirm(document, url)

    except:

        pass
    
    update_upload_xlsx(upload_id)

def update_upload_xlsx(upload_id):

    success = 0
    
    error = 0

    sql = """
        SELECT 
            count(is_confirm) as total, 
            is_confirm 
        from 
            tabqp_md_Document
        WHERE
            is_complete = 1 and
            upload_id = '{}' 
        group by is_confirm
        order by is_confirm asc""".format(upload_id)
    
    results = frappe.db.sql(sql, as_dict = 1)

    for result in results:

        if result["is_confirm"]:

            success = result["total"]

        else:

            error = result["total"]

    frappe.db.set_value('qp_md_upload_xlsx', upload_id,{
        "is_background": False,
        "confirm_success": success,
        "confirm_error": error
    })

    frappe.db.commit()

def get_confirm_payload(document):

    return json.dumps({
        "no": document.document_code
    })

def send_confirm(document, url):

    #url = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/DavitaRegistroDocumentoWS_RegistrarFacturaVenta"
    
    token = get_token()
    
    add_header = {
            'If-Match': '*',
            'company': '798ec2fe-ddfe-ed11-8f6e-6045bd3980fd'
    }
        
    response, response_json, error = send_petition(token, url, document.confirm_request, add_header = add_header)

    document.confirm_response = response

    if not error:
        
        try:

            if response_json["value"] == "":

                frappe.throw("error: retorno vacio")
            
            document_confirm = response_json["value"].split(";")

            if len(document_confirm) > 1:

                document.confirm_dian = document_confirm[1]

            document.document_confirm = document_confirm[0]

            document.is_confirm = True

            

        except:

            pass

    document.save()

    frappe.db.commit()
    
    
