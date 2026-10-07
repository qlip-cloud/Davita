import frappe
import json
import threading
import requests
from qp_authorization.use_case.bearer.authorize import get_enviroment, get_token
from qp_middleware.qp_middleware.service.glosa.exceptions import InvoiceNotFoundError, ResponseStatusError, GlosaTimeoutError, is_timeout_response

@frappe.whitelist()
def handler():
    
    purge_invoice_log()
    
    setup = get_setup()
    
    glosas_name, new_cursor = get_glosas_batch(setup)
    
    nit_emisor = get_company_nit()
    
    if glosas_name:
        
        setup_glosas(glosas_name, nit_emisor, setup)
    
    if new_cursor and setup:
        
        frappe.db.set_value("qp_md_Setup", setup.get("name"), "glosa_cursor", new_cursor)
        
        frappe.db.commit()

def purge_invoice_log():
    
    frappe.db.sql("delete from `tabqp_md_InvoiceRequestLog` where creation < (now() - interval 7 day)")
    
    frappe.db.commit()
        
def get_setup():
    
    rows = frappe.get_all("qp_md_Setup", fields = ["name", "glosa_timeout", "glosa_threads", "glosa_batch_size", "glosa_cursor", "glosa_last_sync"], limit = 1)
    
    return rows[0] if rows else None
    
def get_company_nit():
    
    company = frappe.defaults.get_defaults().company
    
    return frappe.get_value("Company", company, "tax_id")    

def get_glosas_batch(setup):
    
    batch_size = int((setup or {}).get("glosa_batch_size") or 800)
    
    cursor = (setup or {}).get("glosa_cursor") or ""
    
    names = [row[0] for row in frappe.db.sql("""
        select distinct parent
        from `tabqp_md_GlosaLine`
        where (is_verified = 0 or is_sync = 0) and parent > %s
        order by parent
        limit %s
    """, (cursor, batch_size))]
    
    if names:
        
        return names, names[-1]
    
    names = [row[0] for row in frappe.db.sql("""
        select distinct parent
        from `tabqp_md_GlosaLine`
        where (is_verified = 0 or is_sync = 0)
        order by parent
        limit %s
    """, (batch_size,))]
    
    return names, (names[-1] if names else cursor)
    
def get_invoice_context():
    
    enviroment, endpoint, setup = get_enviroment("get_invoice")
    
    url_base = enviroment.url + endpoint.url
    
    token = get_token(enviroment, setup.name)
    
    return url_base, token

def fetch_invoice_http(glosa_name, nit_emisor, url_base, token, timeout):
    
    url = url_base + "?NumeroFactura={}&NitEmisor={}".format(glosa_name, nit_emisor)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }
    
    try:
        
        response = requests.get(url, headers = headers, timeout = timeout)
        
    except requests.exceptions.Timeout:
        
        return glosa_name, {"errorInterno": "timeout en peticion", "Message": "timeout en peticion"}, 500
        
    except Exception as error:
        
        return glosa_name, {"errorInterno": str(error), "Message": "error en peticion"}, 500
        
    try:
        
        return glosa_name, json.loads(response.text), response.status_code
        
    except Exception:
        
        return glosa_name, {"errorInterno": "respuesta no valida", "Message": response.text[:500]}, response.status_code

def prefetch_invoices(glosas_name, nit_emisor, timeout, threads):
    
    url_base, token = get_invoice_context()
    
    results = {}
    
    lock = threading.Lock()
    
    limit = max(int(threads or 8), 1)
    
    def run_worker(glosa_name):
        
        _, response, status_code = fetch_invoice_http(glosa_name, nit_emisor, url_base, token, timeout)
        
        with lock:
            
            results[glosa_name] = (response, status_code)
    
    for index in range(0, len(glosas_name), limit):
        
        chunk = glosas_name[index:index + limit]
        
        workers = [threading.Thread(target = run_worker, args = (name,)) for name in chunk]
        
        for worker in workers:
            
            worker.start()
        
        for worker in workers:
            
            worker.join()
    
    unauthorized = [name for name in results if results[name][1] == 401]
    
    if unauthorized:
        
        url_base, new_token = get_invoice_context()
        
        for name in unauthorized:
            
            _, response, status_code = fetch_invoice_http(name, nit_emisor, url_base, new_token, timeout)
            
            results[name] = (response, status_code)
    
    return results

def setup_glosas(glosas_name, nit_emisor, setup):
    
    timeout = int((setup or {}).get("glosa_timeout") or 30)
    
    threads = int((setup or {}).get("glosa_threads") or 8)
    
    invoice_map = prefetch_invoices(glosas_name, nit_emisor, timeout, threads)
    
    glosa_error_control = frappe.new_doc("qp_md_GlosaError")
    
    for glosa_name in glosas_name:
        
        glosa_error_control.count_invoice_total()
        
        response, status_code = invoice_map.get(glosa_name, ({}, None))
        
        persist_invoice_audit(glosa_name, response, status_code)
        
        try:
            
            if is_timeout_response(response):
                
                raise GlosaTimeoutError(glosa_name, str(response), "get_invoice")
        
            if status_code != 200:
                
                raise ResponseStatusError(glosa_name, "Error en consulta get_invoice", str(response), "get_invoice")
        
            id_invoice = get_id_invoice_from_response(response, glosa_name)
        
        except InvoiceNotFoundError as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_invoice_not_found_error(error, traceback)
            
            glosa_error_control.save()
            
            frappe.db.commit()
            
            continue
            
        except ResponseStatusError as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_invoice_response_error(error, traceback)
            
            glosa_error_control.save()
            
            frappe.db.commit()
            
            continue
            
        except GlosaTimeoutError as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_timeout_error(error, traceback)
            
            glosa_error_control.save()
            
            frappe.db.commit()
            
            continue
        
        try:
            
            glosa = frappe.get_doc("qp_md_Glosa", glosa_name)
            
            glosa.execute_setup_glosa(nit_emisor, glosa_error_control, id_invoice = id_invoice)
            
            glosa.save()
        
        except InvoiceNotFoundError as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_invoice_not_found_error(error, traceback)
        
        except ResponseStatusError as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_invoice_response_error(error, traceback)
            
        except GlosaTimeoutError as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_timeout_error(error, traceback)
        
        except Exception as error:
            
            traceback = frappe.get_traceback()
            
            glosa_error_control.add_invoice_error_unknown(glosa_name, str(error), traceback)
        
        finally:
            
            glosa_error_control.save()
            
            frappe.db.commit()

def get_id_invoice_from_response(response, glosa_name):
    
    if "resultado" not in response or not response.get("resultado"):
        
        raise InvoiceNotFoundError(invoice_id = glosa_name)
    
    result = response.get("resultado")
    
    first = result[0] if isinstance(result, list) else result
    
    return first.get("idFactura")

def persist_invoice_audit(invoice_prefix, response, status_code):
    
    try:
        
        existing = frappe.db.exists("qp_md_InvoiceRequest", {"invoice_prefix": invoice_prefix})
        
        if existing:
            
            request = frappe.get_doc("qp_md_InvoiceRequest", existing)
            
        else:
            
            request = frappe.new_doc("qp_md_InvoiceRequest")
        
        request.invoice_prefix = invoice_prefix
        
        request.append("response_log", {
            "endpoint": "get_invoice",
            "status_code": status_code,
            "status": get_audit_status(status_code, response),
            "id_invoice": get_audit_id_invoice(response),
            "response": json.dumps(response, ensure_ascii = False) if response else ""
        })
        
        request.save(ignore_permissions = True)
        
    except Exception:
        
        frappe.log_error(
            message = frappe.get_traceback(),
            title = "Auditoría MINSALUD get_invoice {}".format(invoice_prefix)
        )

def get_audit_status(status_code, response):
    
    if response and response.get("errorInterno") == "timeout en peticion":
        
        return "Timeout MINSALUD"
    
    if status_code == 200:
        
        if not response or not response.get("resultado"):
            
            return "Factura No Encontrada"
        
        return "OK"
    
    return {400: "Parámetros inválidos", 401: "No autorizado", 500: "Error interno MINSALUD"}.get(status_code, "Status {}".format(status_code))

def get_audit_id_invoice(response):
    
    try:
        
        result = (response or {}).get("resultado") or []
        
        first = result[0] if isinstance(result, list) and result else result
        
        return (first or {}).get("idFactura")
        
    except Exception:
        
        return None