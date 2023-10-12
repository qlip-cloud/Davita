import frappe
import json
import requests

from qp_authorization.use_case.oauth2.authorize import get_token

URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/ItemList"

payload = ""

@frappe.whitelist()
def handler():
    
    token = get_token()
    
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    response = requests.get(URL, headers=headers, data=payload)

    response_json = json.loads(response.text)

    item_code = tuple([ item["No"] for item in response_json["value"]])

    result = frappe.get_list(doctype = "Item",  filters = {"item_code": ["in", item_code]}, pluck = 'item_code')

    new_items = list(filter(lambda x: x["No"] not in result and x['Description'], response_json["value"]))
    
    for iter in new_items:
        
        item = frappe.new_doc('Item')
        item.item_code = iter['No']
        item.qp_item_code_2 = iter.get('No_2', None)
        item.qp_type = iter['Type']
        item.item_name = iter['Description']
        #item.item_group = frappe._(iter['Type'])
        item.item_group = "Servicios"
        #item.stock_uom = iter['Base_Unit_of_Measure']
        item.stock_uom = "Nos"
        item.insert()
    #HAY Q AGREGAR LA UNIDAD DE MEDIDA!!!!!!!
    #HAY Q AGREGAR lOS GRUPOS DE PRODUSTOS!!!!!!!
    if new_items:

        frappe.db.commit()

    return new_items