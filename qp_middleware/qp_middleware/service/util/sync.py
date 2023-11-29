import frappe
import json
import requests
import requests
import threading
import xmltodict
import time
from qp_authorization.use_case.oauth2.authorize import get_token

def get_list(enviroment, code, filters = None):
    
    token = get_token()

    enpoint = frappe.get_doc("qp_md_Endpoint", code)

    url = enviroment.get_url_with_company_and_filters(enpoint.url, filters) if filters else enviroment.get_url_with_company(enpoint.url)
    
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    response = requests.get(url, headers=headers)

    response_json = json.loads(response.text)

    if "error" in response_json:

        frappe.throw(response_json["error"])

    return response_json

def get_response(code, filters = None):

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)
    
    return get_list(enviroment, code, filters)

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

    response = requests.request(method, url, headers=headers, data=payload)
        
    try:
        
        response_json = json.loads(response.text) if is_json else xmltodict.parse(response.text)

    except:

        return response.text, None, True

    return response.text, response_json, "error" in response_json

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