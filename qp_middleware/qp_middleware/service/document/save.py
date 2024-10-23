import frappe
import time
import json
import requests
from datetime import datetime
from frappe.utils import today
from dateutil.relativedelta import relativedelta
from qp_middleware.qp_middleware.service.document.init import init_document, get_nit_customer_no_repeat, get_items_codes, get_code_modality, get_contract_customer, set_document_error, get_cuota_moderadora_no_repeat,get_code_dimension_not_repeat

COD = ["JF-", "EJC", "PL1"]

LIMIT = {
    "JF-": 3,
    "EJC": 3,
    "PL1": 2
}

@frappe.whitelist()
def handler(upload_xlsx):
    
    lines = frappe.get_list("qp_md_invoice_sync", filters = {"upload_id": upload_xlsx.name}, fields = ["*"])

    #lines = frappe.get_list("qp_md_invoice_test", filters = {"upload_id": upload_id}, fields = ["*"])
    
    documents_code = set(map(lambda x: x["group_code"], lines))

    group_lines = [[y for y in lines if y["group_code"]==x] for x in documents_code]
    
    response = []
    
    is_valid = True
    
    document_success = 0

    send_success = 0

    for lines_iter in group_lines:
        
        document = setup_document(lines_iter, upload_xlsx)
        
        line_no = 1000

        document.items = []

        for line in lines_iter:
                        
            quantity_invoice = float(line["cantidad_a_facturar"])

            item_type = "Item"

            code_modality = get_code_modality(line["codigo_centro_de_costo"], document)
            
            item_code, item_code_2, quantity, unit_price = get_items_codes(line, document)
            
            item = frappe.new_doc("qp_md_DocumentItem")

            setup_item(item, item_code, item_code_2, quantity_invoice,  quantity, line_no,
                    unit_price, item_type, document, document.patient_code, modality_code=code_modality)
            
            document.items.append(item)

            if line["empty_2"] and int(line["empty_2"]) > 0:

                line_no += 1000

                item = frappe.new_doc("qp_md_DocumentItem")

                setup_item(item, "IG01001", "IG01001", quantity_invoice, int(line["empty_2"]), line_no,
                           0, item_type, document, document.patient_code, modality_code=code_modality)
                
                document.items.append(item)

            if line["cuota_moderadora"] > 0:

                line_no += 1000

                item = frappe.new_doc("qp_md_DocumentItem")

                unit_price =  line["cuota_moderadora"] * -1
        
                quantity = 1

                setup_item(item, "28050501", "28050501", quantity_invoice, quantity, line_no,
                           unit_price, "G/L Account", document, document.patient_code, modality_code=code_modality)

                document.items.append(item)

            line_no += 1000
        
        document.insert()  

        response.append(document)
        
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
        'is_valid': is_valid
    }

def setup_document(lines_iter, upload_xlsx):

    code_customer, error_customer, msg_error_customer = get_nit_customer_no_repeat(lines_iter)
        
    code_dimension, error_dimension, msg_error_dimension = get_code_dimension_not_repeat(lines_iter)

    code_patient, error_patient, msg_error_patient = get_nit_patient(lines_iter)

    code_contrat_patient, error_contrat_patient, msg_error_contrat_patient = get_contract_customer(code_customer)

    code_cuota_moderadora, error_cuota_moderadora, msg_error_cuota_moderadora = get_cuota_moderadora_no_repeat(lines_iter)

    code_numero_autorizacion, error_numero_autorizacion, msg_error_numero_autorizacion = get_numero_autorizacion(lines_iter)
    
    numero_orden_compra =  get_orden_compra(lines_iter[0]["cod_empresa"], lines_iter[0]["nit"])
    
    document = init_document(upload_xlsx, lines_iter[0], code_customer, code_cuota_moderadora, code_contrat_patient, code_numero_autorizacion, 
                            code_dimension, code_patient, numero_orden_compra, lines_iter[0]["group_code"])

    set_document_error(document, error_customer , error_contrat_patient , error_dimension , error_cuota_moderadora , error_numero_autorizacion , error_patient , msg_error_customer , msg_error_dimension , msg_error_numero_autorizacion , msg_error_cuota_moderadora , msg_error_patient , msg_error_contrat_patient)

    return document

def get_orden_compra(cod_empresa, nit):

    if nit == "901543761_2":
        
        return "NO DIABETICO"

    if nit == "901543761_1":

        return "DIABETICO"
        
    if not cod_empresa:

        return ""
    
    cod_base = cod_empresa[0:3]

    if cod_base not in COD:
        
        return ""
    
    cod_part = cod_empresa[LIMIT[cod_base]:]

    cod_split = cod_part.split("-")

    return cod_split[0]




def get_nit_patient(lines_iter):
    
    patient_code = list(set(map(lambda x: x["no_identificacion"], lines_iter)))

    if len(patient_code) > 1:

        return patient_code[0], True, "Paciente {} diferentes para la misma factura\n".format(patient_code)
    
    patient = frappe.get_list("qp_md_Patient", filters = {"numero_identificacion": patient_code[0] }, fields = ["*"])
    
    if not patient:

        return lines_iter[0]["no_identificacion"], True, "Paciente {} No existe\n".format(lines_iter[0]["no_identificacion"])

    patient_nit = lines_iter[0]["tipo_documento"] + str(lines_iter[0]["no_identificacion"])

    return patient_nit, False, ""



def get_numero_autorizacion(lines_iter):

    numero_autorizacion = list(set(map(lambda x: x["autorizacion_final"] , lines_iter)))

    if len(numero_autorizacion) > 1:

        return numero_autorizacion[0], True, "Numero Autorizacion diferentes para la misma factura: {}\n".format(numero_autorizacion)

    return numero_autorizacion[0], False, ""

def set_fecha_periodo(document):

    date_format = datetime.strptime(document.posting_date, '%Y-%m-%d')

    document.lhc_periodo_inicio_fecha_fact =  datetime.strftime(date_format + relativedelta(day=1), '%Y-%m-%d')

    document.lhc_periodo_fin_fecha_fact =datetime.strftime( date_format + relativedelta(day=31), '%Y-%m-%d')
    

def setup_item(item,item_code, item_code_2, quantity_invoice, quantity, line_no, unit_price, type_code, document, patient_code
               ,document_type = "Invoice", modality_code = ""):

    item.item_code  = item_code
    item.item_code2  = item_code_2
    item.quantity = quantity
    item.line = line_no
    item.type_code = type_code
    item.filtered_type_field = type_code
    item.customer_code = document.customer_code
    item.headquarter_code = document.headquarter_code
    item.patient_code = patient_code
    item.document_type = document_type
    item.modality_code = modality_code
    item.parentfield = "items"
    item.unit_price =  unit_price
    item.quantity_invoice = quantity_invoice
    
    if type_code == "G/L Account":
        
        item.line_amount = unit_price