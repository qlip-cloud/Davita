import frappe
import json
import requests

from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/ItemList"

@frappe.whitelist()
def handler():

    response_json = get_response("list_product")

    item_code = tuple([ item["No"] for item in response_json["value"]])

    result = frappe.get_list(doctype = "Item",  filters = {"item_code": ["in", item_code]}, pluck = 'item_code')

    new_items = list(filter(lambda x: x["No"] not in result and x['Description'], response_json["value"]))
    
    values = []  

    for iter in new_items:
        
        values.append((iter['No'], iter['No'], iter.get('No_2', None) ,iter['Type'], iter['Description'], "Servicios", "Nos",  now(), 'Administrator'))

    if new_items:

        table = "tabItem"

        fields = "(name, item_code, qp_item_code_2, qp_type, item_name, item_group, stock_uom, creation, owner)"
        
        persist(table, fields, values)

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(new_items)
    }