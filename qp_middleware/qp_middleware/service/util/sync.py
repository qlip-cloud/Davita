import frappe
import html
import json
import requests
import threading
import xmltodict
import time
import traceback
from qp_authorization.use_case.oauth2.authorize import get_token

def get_list(enviroment, enpoint, maxpagesize = 0, filters = None, select = None):
    
    url = enviroment.get_url(enpoint, filters, select)  

    response_values = {
        "value" : []
    }

    callback_get_list(url, response_values, enviroment.name, int(maxpagesize))

    return response_values

def callback_get_list(url, response_values, enviroment_code, maxpagesize = 0):

    token = get_token(enviroment_code)

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }
    
    if maxpagesize and maxpagesize > 0:
        
        headers.update({
            "Prefer": f"odata.maxpagesize={maxpagesize}"
        })
        
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        
        frappe.throw(f"Error en solicitud: {response.reason} status {response.status_code}")
        
    response_json = json.loads(response.text)
    
    if "error" in response_json:

        frappe.throw(response_json["error"])

    response_values["value"] += response_json['value']

    if "@odata.nextLink" in response_json and response_json["@odata.nextLink"]:

        callback_get_list(response_json["@odata.nextLink"], response_values, enviroment_code, maxpagesize)

def get_response(endpoint_code, filters = None, include_prefer = False, select = None, setup_list_code = None):
    
    maxpagesize = 0

    enviroment, endpoint, setup = get_enviroment(endpoint_code, setup_list_code)
    
    if include_prefer:
        
        maxpagesize = setup.invoices_group
    
    return get_list(enviroment, endpoint, maxpagesize, filters, select)

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

def send_petition(endpoint_code, payload, method = "POST", add_header = False, is_json = True):
    
    enviroment, endpoint, setup = get_enviroment(endpoint_code)
    
    url = enviroment.get_url(endpoint)
    
    token = get_token(enviroment.name)  
    
    headers = {
        'Content-Type': 'application/json' if is_json else "application/xml",
        'Authorization': 'Bearer {}'.format(token)
    }

    if add_header:
        
        header = enviroment.get_header(endpoint)
        
        headers.update(header)
        
    response = None
    
    response_json = None
    
    is_error = True
    
    try:
        
        response = requests.request(endpoint.request, url, headers=headers, data=payload)
        
    except Exception as error:
        
        return f"Error en peticion: {error}", response_json, is_error       
    
    response_text = response.text
    
    #response_text = """s:Soap:Envelope xmlns:Soap="http://schemas.xmlsoap.org/soap/envelope/"><12s:adsSoap:Body><s:RegistrarFacturasVentaWS_Result xmlns="urn:microsoft-dynamics-schemas/codeunit/RegistrarFacturasVentaWS"><s:return_value>690815;690816;690817;<s:/return_value><s:/RegistrarFacturasVentaWS_Result><s:/Soap:Body><s:/Soap:Envelope>"""
        
    try:
        
        response_json = json.loads(response_text) if is_json else xmltodict.parse(response_text)
    
        is_error = "error" in response_json

    except Exception as error:
        trace = traceback.format_exc()
        msg = f"""Recibido {response_text} error {error} is_json {is_json} \n\n {trace} """
        frappe.log_error(message=msg, title="Error en conversión respuesta recibida")
        
    finally:

        return response_text, response_json, is_error


SOAP_PAYLOAD_PLACEHOLDER = "__PAYLOAD__"


def render_soap_payload(template, payload, strip_single_quotes=True):
    """Inserta el payload JSON en el template SOAP (funcion pura)."""
    template = html.unescape(template)
    payload_xml = template.replace(SOAP_PAYLOAD_PLACEHOLDER, json.dumps(payload))
    if strip_single_quotes:
        payload_xml = payload_xml.replace("'", "")
    return payload_xml


def send_soap(endpoint_code, payload):
    """Arma y envia una peticion SOAP a partir del template configurado
    en el qp_md_Endpoint (soap_template). El payload JSON se inserta en el
    placeholder SOAP_PAYLOAD_PLACEHOLDER."""
    enviroment, endpoint, setup = get_enviroment(endpoint_code)

    template = getattr(endpoint, "soap_template", None) or ""
    if not template:
        frappe.throw(
            "Endpoint {} sin soap_template configurado".format(endpoint_code)
        )

    payload_xml = render_soap_payload(
        template,
        payload,
        bool(getattr(endpoint, "strip_single_quotes", 1)),
    )

    return send_petition(endpoint_code, payload_xml, add_header=True, is_json=False)


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

def get_enviroment(endpoint_code, setup_list_code = None):

    endpoint = frappe.get_doc("qp_md_Endpoint", endpoint_code)
    
    if not setup_list_code:
        
        setup_list_code = endpoint.setup
        
    setup = frappe.get_doc("qp_md_Setup", setup_list_code)
    
    enviroment_code = setup.enviroment
        
    enviroment = frappe.get_doc("qp_md_Enviroment", enviroment_code)

    return enviroment, endpoint, setup