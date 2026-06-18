import frappe
import json
import requests
import requests
import threading
import xmltodict
import time
import traceback
from qp_authorization.use_case.oauth2.authorize import get_token

def get_list(enviroment, code, filters = None, include_prefer = False, select = None):
    
    enpoint = frappe.get_doc("qp_md_Endpoint", code)

    url = enviroment.get_url_with_company_and_filters(enpoint.url, filters, select) if filters else enviroment.get_url_with_company(enpoint.url)

    response_values = {
        "value" : []
    }

    callback_get_list(url, response_values, include_prefer)

    return response_values

def callback_get_list(url, response_values, include_prefer = False):

    token = get_token()

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }
    
    if include_prefer:
        
        headers.update({
            "Prefer": "odata.maxpagesize=100"
        })
        

    response = requests.get(url, headers=headers)


    if response.status_code != 200:
        
        frappe.throw(f"Error en solicitud: {response.reason} status {response.status_code}")
        
    response_json = json.loads(response.text)
    
    if "error" in response_json:

        frappe.throw(response_json["error"])

    response_values["value"] += response_json['value']

    if "@odata.nextLink" in response_json and response_json["@odata.nextLink"]:

        callback_get_list(response_json["@odata.nextLink"], response_values, include_prefer)

def get_response(code, filters = None, include_prefer = False, select = None):

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)
    
    return get_list(enviroment, code, filters, include_prefer, select)

def persist(table, fields, values):

    value_tuple = str(values).replace("[", "").replace("]", "")

    sql = """
        INSERT INTO {table}
        {fields}
        values
        {value_tuple}
    """.format(table = table, fields = fields, value_tuple = value_tuple)

    frappe.db.sql(sql)

    frappe.db.commit()

def send_petition(token, url, payload, method = "POST", add_header = None, is_json = True):
    
    headers = {
        'Content-Type': 'application/json' if is_json else "application/xml",
        'Authorization': 'Bearer {}'.format(token)
    }

    if add_header:

        headers.update(add_header)
        
    response = None
    
    response_json = None
    
    is_error = True

    try:
        
        response = requests.request(method, url, headers=headers, data=payload)
    
    except Exception as error:
        
        return f"Error en peticion: {error}", response_json, True       
    
    response_text = response.text
    
    try:
        
        response_json = json.loads(response_text) if is_json else xmltodict.parse(response_text)

        is_error = "error" in response_json  

    except Exception as error:
        trace = traceback.format_exc()
        msg = f"""Recibido {response_text} error {error} is_json {is_json} \n\n {trace} """
        frappe.log_error(message=msg, title="Error en conversión respuesta recibida")

    finally:

        return response_text, response_json, is_error


def send_request(documents, setup, target, token, url):

    #setup = frappe.get_doc("qp_md_Setup")

    threads = list()

    for document in documents:
        
        callback(document,threads, setup, target, token, url)
    
    for t in threads:
        
        t.join()

def callback(document,threads, setup, target, token, url):

    if threading.active_count() <= setup.number_request:
        
        t = threading.Thread(target=target, args=(document, token, url))

        threads.append(t)

        t.start()
    
    else:
        
        time.sleep(setup.wait_time)

        callback(document,threads, setup, target, token, url)

def get_enviroment(endpoint_code):

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)
    
    endpoint = frappe.get_doc("qp_md_Endpoint", endpoint_code)

    return enviroment, endpoint