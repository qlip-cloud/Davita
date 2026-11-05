import frappe
from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist
from datetime import datetime
from dateutil.relativedelta import relativedelta
from frappe.utils.background_jobs import get_redis_conn
from rq import Queue
from frappe.utils.background_jobs import get_redis_conn
from frappe.core.page.background_jobs.background_jobs import get_info

@frappe.whitelist()
def handler(setup_list_code = None):

    job_name = "sync_customer"
    
    check_job_status(job_name)
    
    frappe.enqueue(
        sync,
        queue='long',                
        is_async=True,
        #now=True,
        job_name = job_name,
        timeout=5400000,
        setup_list_code = setup_list_code
    )
    
    return {
        "status": 202,
        "msg": "Esta actividad se ejecutara en segundo plano."
    }
    
def sync(setup_list_code):

    select = "No,Name,CustomerSince"
    
    date_ago = get_date_two_months_ago()
    
    #filters = f"CustomerSince gt {date_ago}"
    filters = None
    
    response_json = get_response("list_customers", filters, include_prefer = True, select = select, setup_list_code = setup_list_code)

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

def check_job_status(job_name):
        
    jobs = get_info()
    
    jobs_filter = list(filter(lambda x: x['job_name'] == job_name, jobs))
    
    if jobs_filter:
        
        frappe.throw("Existe una sincronizacion de clientes en curso, por favor espere.")