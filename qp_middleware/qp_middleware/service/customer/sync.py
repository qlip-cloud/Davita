import frappe
from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist
from datetime import datetime
from dateutil.relativedelta import relativedelta

@frappe.whitelist()
def handler():

    
    select = "No,Name,CustomerSince"
    
    date_ago = get_date_two_months_ago()
    
    filters = f"CustomerSince gt {date_ago}"
    
    response_json = get_response("list_customers", filters, include_prefer = True, select = select)

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

def get_date_two_months_ago():

    current_date = datetime.now()
    
    two_months_ago = current_date - relativedelta(months=2)
    
    formatted_date = two_months_ago.strftime('%Y-%m-01T00:00:00Z')
    
    return formatted_date
