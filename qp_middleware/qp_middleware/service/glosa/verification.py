import frappe
from qp_middleware.qp_middleware.service.glosa.exceptions import InvoiceNotFoundError, ResponseStatusError

@frappe.whitelist()
def handler():
    
    glosas_name = get_glosas_name()
    
    nit_emisor = get_company_nit()
    
    setup_glosas(glosas_name, nit_emisor)
    
def get_company_nit():
    
    company = frappe.defaults.get_defaults().company
    
    return frappe.get_value("Company", company, "tax_id")    
    
def get_glosas_name():
    # Buscar las facturas de las glosas nuevas post sincronizacion. tiene q haber otro estatus por si hay q actualizar
    
    glosas_name = frappe.get_list("qp_md_GlosaLine", or_filters = {"is_verified": False, "is_sync": False}, pluck = "parent")
    
    return list(set(glosas_name))
    
def setup_glosas(glosas_name, nit_emisor):
    
    if glosas_name:
        
        glosa_error_control = frappe.new_doc("qp_md_GlosaError")
        
        for glosa_name in glosas_name:
        
            try:
            
                glosa_error_control.count_invoice_total()
                
                glosa = frappe.get_doc("qp_md_Glosa", glosa_name)
                
                glosa.execute_setup_glosa(nit_emisor, glosa_error_control)
                
                glosa.save()
        
            except InvoiceNotFoundError as error:
                
                traceback = frappe.get_traceback()
                
                glosa_error_control.add_invoice_not_found_error(error, traceback)
                
            except ResponseStatusError as error:
                
                traceback = frappe.get_traceback()
                
                glosa_error_control.add_invoice_response_error(error, traceback)
                
            except Exception as error:
                
                traceback = frappe.get_traceback()
                
                glosa_error_control.add_invoice_error_unknown(glosa_name, str(error), traceback)
                
            finally:
                    
                glosa_error_control.save()
                    
                frappe.db.commit()