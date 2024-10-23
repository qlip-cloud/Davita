import frappe
import time
from datetime import datetime
import json
from frappe.utils import today
import requests

from dateutil.relativedelta import relativedelta
from qp_middleware.qp_middleware.service.document.init import init_document, get_from_tax_id, get_items_codes,get_contract_customer,set_document_error,get_code_modality,get_code_dimension

COD = ["JF-", "EJC", "PL1"]

LIMIT = {
    "JF-": 3,
    "EJC": 3,
    "PL1": 2
}

@frappe.whitelist()
def handler(upload_xlsx):
    
    group_nit = frappe.get_list("qp_md_invoice_sync", filters = {"upload_id": upload_xlsx.name, }, pluck='nit',group_by='nit')
    
    response = []
    
    is_valid = True
    
    document_success = 0

    send_success = 0

    for nit in group_nit:
        
        lines = frappe.get_list("qp_md_invoice_sync", filters = {"upload_id": upload_xlsx.name, "nit": nit}, fields = ["*"])
        
        document = setup_document(nit, [lines[0]], upload_xlsx)
        
        set_dimensions(document, upload_xlsx)
        
        unit_price, qty = set_patients_and_get_unit_price(document, lines)
        
        set_sales_invoice(document, unit_price, qty)

        document.insert()  

        #response.append(document)
        if document.is_valid:
            
            document_success += 1

        elif is_valid:

            is_valid = False


    frappe.db.commit()  

    return {
        'invoice_total': len(response),
        'invoice_success': document_success,
        'invoice_error': len(response) - document_success,
        'customer_count': 0,
        'item_count': 0,
        'send_success': send_success,
        'send_error': len(response) - send_success,
        'is_valid': is_valid,
    }

def setup_document(nit, lines_iter, upload_xlsx):

    code_customer, error_customer, msg_error_customer = get_from_tax_id(nit, lines_iter)
    
    code_contrat_patient, error_contrat_patient, msg_error_contrat_patient = get_contract_customer(code_customer)
    
    
        
    document = init_document(upload_xlsx, lines_iter[0], code_customer, lines_iter[0]["cuota_moderadora"], code_contrat_patient, "", "", "","","", tipo_operacion = "multiusuario")
    
    set_document_error(document, error_customer , error_contrat_patient, msg_error_customer = msg_error_customer, msg_error_contrat_patient = msg_error_contrat_patient)

    return document



def set_dimensions(document, upload_xlsx):
        
    customer_nit = document.customer_code.split("-")
    
    document.append("dimensions",{
                        "code": "TERCERO",
                        "value_code": customer_nit[0]
                    }
    )

    document.append("dimensions",{
                        "code": "LIBRO",
                        "value_code": "NCIF"
                    })
    
    document.append("dimensions",{
                        "code": "SEDE",
                        "value_code": upload_xlsx.headquarter
                    })
    document.append("dimensions",{
                        "code": "MODALIDAD",
                        "value_code": upload_xlsx.cod_modality
                    })
    
def set_sales_invoice(document, unit_price, qty):
    
    item = frappe.get_value("qp_md_Contract", { "id_cliente": document.customer_code}, ["item_code", "item_code_2"], as_dict=1 )
    
    document.append("sales_invoices", {
                "line_no": 1000,
                "type": "Item",
                "no": item["item_code"],
                "quantity": qty,
                "unit_of_measure_code": "UND",
                "unit_price": unit_price,
                "cantidadPBI": 0,
                "Modalidad": ""#modalidad del product
            }
        )
def set_patients_and_get_unit_price(document, lines):
    
    unit_price = 0
    qty = 0
    
    for line in lines:
        
        item_code, item_code_2, quantity, unit_price = get_items_codes(line, document)
        

        code_dimension, error_dimension, msg_error_dimension = get_code_dimension(line["sede_de_origne"])
        
        document.is_valid = not error_dimension or document.is_valid
        
        document.error += msg_error_dimension

        document.append("patients",
                    {
                        "no_identification": line["no_identificacion"],
                        "tipo_identification": line["tipo_documento"],
                        "no_authorization": line["autorizacion_final"],
                        "lhc_mipres": "",
                        "lhc_id_mipres": "",
                        "lhc_no_poliza": "",
                        "patient_headquarter": code_dimension,
                        "patient_modality": get_code_modality(line["codigo_centro_de_costo"], document),
                        "item_code": item_code,
                        "quantity": quantity
                    }
                )
        unit_price += float(line["vr_a_facturar"])
        qty += int(quantity)
        
    return unit_price, qty