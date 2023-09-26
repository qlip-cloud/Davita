import frappe
import json
import requests

from qp_authorization.use_case.oauth2.authorize import get_token

URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/Customers"

payload = ""

@frappe.whitelist()
def handler():
    
    token = get_token()

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    response = requests.get(URL, headers=headers, data=payload)

    response_json = json.loads(response.text)

    customer_nit = tuple([ customer["No"] for customer in response_json["value"]])

    result = frappe.get_list(doctype = "Customer",  filters = {"tax_id": ["in", customer_nit]}, pluck = 'tax_id')

    new_customers = list(filter(lambda x: x["No"] not in result and x['Name'], response_json["value"]))
    
    for iter in new_customers:
        
        customer = frappe.new_doc('Customer')
        customer.customer_name = iter['Name']
        customer.tax_id = iter['No']
        customer.insert()

    if new_customers:

        frappe.db.commit()

    return new_customers