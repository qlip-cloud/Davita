import frappe
import json
import requests

from qp_authorization.use_case.oauth2.authorize import get_token

URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/DimensionValues?$filter=Dimension_Code eq 'SEDE'"

payload = ""

@frappe.whitelist()
def handler():
    
    token = get_token()
    
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    response = requests.get(URL, headers=headers, data=payload)

    response_json = json.loads(response.text)

    headquarter_code = tuple([ headquarter["Code"] for headquarter in response_json["value"]])

    result = frappe.get_list(doctype = "qp_md_headquarter",  filters = {"code": ["in", headquarter_code]}, pluck = 'code')

    new_headquarters = list(filter(lambda x: x["Code"] not in result and x['Name'], response_json["value"]))
    
    for iter in new_headquarters:
        
        headquarter = frappe.new_doc('qp_md_headquarter')
        headquarter.code = iter['Code']
        headquarter.title = iter['Name']
        headquarter.insert()
    
    if new_headquarters:

        frappe.db.commit()

    return new_headquarters