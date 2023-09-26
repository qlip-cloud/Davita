import frappe
import json
@frappe.whitelist()
def handler():

    item_import = get_item_import()

    item_code = get_item_code(item_import)

    count = save_item_import(item_import, item_code)

    return {
        "status": "success",
        "count": count
    }

def save_item_import(item_import, item_code):

    count = 0

    for iter in item_import:

        if iter['item_code'] not in item_code:
            count += 1
            item = frappe.new_doc('Item')
            item.item_code = iter['item_code'] + '_' + iter['item_name']
            item.item_name = iter['item_name']
            item.item_group = "Servicios"
            item.stock_uom = "Nos"
            item.insert()

    if count:
        
        frappe.db.commit()

    return count

def get_item_code(item_import):

    codes = tuple(map(lambda x: x['item_code'] , item_import))
    
    return frappe.db.get_list('Item', filters = {'item_code': ['in', codes]}, pluck='item_code')

def get_item_import():

    sql = """
        select              
            SUBSTRING_INDEX(codigo_procedimiento_facturacion, '_' , 1) as item_code, 
            nombre_codigo_descripcion  as  item_name        
        from              
            tabqp_md_invoice_sync
        where             
            codigo_procedimiento_facturacion NOT IN ('NULL', '#N/A', '0', 'NIT')   and 
            nombre_codigo_descripcion not in ('NULL', '0') 
        group by              
            item_code, item_name;
    """

    return frappe.db.sql(sql, as_dict = 1)