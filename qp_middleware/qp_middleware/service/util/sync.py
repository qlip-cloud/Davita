import frappe
import json
from qp_authorization.use_case.oauth2.authorize import get_token
import requests

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