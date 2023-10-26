import frappe
from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist



#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/Customers"

#payload = ""

@frappe.whitelist()
def handler():

    response_json = get_response("list_customers")

    customer_nit = tuple([ customer["No"] for customer in response_json["value"]])

    result = frappe.get_list(doctype = "Customer",  filters = {"tax_id": ["in", customer_nit]}, pluck = 'tax_id')

    new_customers = list(filter(lambda x: x["No"] not in result and x['Name'], response_json["value"]))
    
    values = []  

    for iter in new_customers:
        
        values.append((iter['No'], iter['Name'], iter['No'], now(), 'Administrator', 'Todas las categorías de clientes', 'Todos los territorios'))

    if new_customers:

        table = "tabCustomer"

        fields = "(name, customer_name, tax_id, creation, owner, customer_group, territory)"
        
        persist(table, fields, values)
        

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(new_customers)
    }

