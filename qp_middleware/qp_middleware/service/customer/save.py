import frappe
import json
@frappe.whitelist()
def handler():

    customer_import = get_customer_import()

    customer_tax_id = get_customer_tax_id(customer_import)

    count = save_customer_import(customer_import, customer_tax_id)

    return {
        "status": "success",
        "count": count
    }

def save_customer_import(customer_import, customer_tax_id):

    count = 0

    for iter in customer_import:

        if iter['nit_format'] not in customer_tax_id:
            count += 1
            customer = frappe.new_doc('Customer')
            customer.name = "{}_{}".format(iter['nit_format'], iter['nombre_eps'])
            customer.customer_name = iter['nombre_eps']
            customer.tax_id = iter['nit_format']
            customer.insert()

    if count:
        
        frappe.db.commit()

    return count

def get_customer_tax_id(customer_import):

    codes = tuple(map(lambda x: x['nit_format'] , customer_import))
    
    return frappe.db.get_list('Customer', filters = {'tax_id': ['in', codes]}, pluck='tax_id')

def get_customer_import():

    sql = """

    select              
        SUBSTRING_INDEX(nit, '_' , 1) as nit_format, 
        nombre_eps          
    from              
        tabqp_md_invoice_sync
    where             
        nit NOT IN ('NULL', '#N/A', '0', 'NIT')   and 
        nombre_eps not in ('NULL')      
    group by              
        nit_format, nombre_eps
    """

    return frappe.db.sql(sql, as_dict = 1)