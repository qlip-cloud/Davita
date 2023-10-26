import frappe
from frappe.utils import now

from qp_middleware.qp_middleware.service.util.sync import get_response, persist

#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/DimensionValues?$filter=Dimension_Code eq 'SEDE'"

#payload = ""

@frappe.whitelist()
def handler():
    
    filters = "Dimension_Code eq 'SEDE'"

    response_json = get_response("list_headquarter", filters)

    headquarter_code = tuple([headquarter["Code"] for headquarter in response_json["value"]])

    result = frappe.get_list(doctype = "qp_md_headquarter",  filters = {"code": ["in", headquarter_code]}, pluck = 'code')

    new_headquarters = list(filter(lambda x: x["Code"] not in result and x['Name'], response_json["value"]))

    values = []  

    for iter in new_headquarters:
        
        values.append((iter['Code'], iter['Code'], iter['Name'], now(), 'Administrator'))

    if new_headquarters:

        table = "tabqp_md_headquarter"

        fields = "(name, code, title, creation, owner)"
        
        persist(table, fields, values)

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(new_headquarters)
    }