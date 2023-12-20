import frappe 
import json
from qp_middleware.qp_middleware.service.util.sync import send_petition
from qp_authorization.use_case.oauth2.authorize import get_token

def handler(dimension_code, name = "", second_name = "", lastname = "", second_lastname = ""):

    dimension = None
    
    if not frappe.db.exists("qp_md_DimensionPatient", {"code": dimension_code}):

        try:

            dimension = frappe.new_doc("qp_md_DimensionPatient")
            
            dimension.code = dimension_code

            dimension.request = set_request_dimension(dimension_code, name, second_name, lastname, second_lastname)

            sync(dimension)

            dimension.insert()

        except Exception as error:

            pass

    else:

        dimension = frappe.get_doc("qp_md_DimensionPatient", dimension_code)

        if not dimension.is_sync:

            try:

                sync(dimension)

                dimension.save()
                
                frappe.db.commit()

            except:
                 
                pass
    
    
    return dimension


def sync(dimension):

    token = get_token()

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    enpoint = frappe.get_doc("qp_md_Endpoint", "dimension_create")

    dimension_url = enviroment.get_url_with_company(enpoint.url)

    response, response_json, error_response = send_petition(token, dimension_url, dimension.request)

    dimension.response = response
    
    if error_response:
        
        if response_json.get("error").get("code") != 'Internal_EntityWithSameKeyExists':

            dimension.status = "Error"

            raise Exception(response_json.get("error").get("code"))

        dimension.status = "Repeated"

    dimension.is_sync = True
    

def set_request_dimension(dimension_code, name, second_name, lastname, second_lastname):

    return json.dumps({
            "Dimension_Code": "PACIENTE",
            "Code": dimension_code,
            "Name": name + " " + second_name + " " +lastname + " " +second_lastname,
            "Dimension_Value_Type": "Standard",
            "Blocked": False
        })