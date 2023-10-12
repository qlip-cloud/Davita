import frappe
import time
from datetime import datetime
import json
from frappe.utils import today
import requests

from dateutil.relativedelta import relativedelta


@frappe.whitelist()
def handler(upload_id):
        
    lines = frappe.get_list("qp_md_invoice_sync", filters = {"upload_id": upload_id}, fields = ["*"])
    #lines = frappe.get_list("qp_md_invoice_test", filters = {"upload_id": upload_id}, fields = ["*"])
    
    documents_code = set(map(lambda x: x["group_code"], lines))

    group_lines = [[y for y in lines if y["group_code"]==x] for x in documents_code]
    
    response = []
    
    is_valid = True
    
    document_success = 0

    send_success = 0

    for lines_iter in group_lines:
        
        document = setup_document(lines_iter, upload_id)
        
        line_no = 1000

        document.items = []

        for line in lines_iter:

            item_code = frappe.get_list("Item", filters = {"qp_item_code_2": line["codigo_procedimiento_facturacion"] }, fields = ["item_code"])

            if not item_code:

                if document.is_valid:
                    
                    document.is_valid = False
                
                document.error += "Producto {} no existe".format(line["codigo_procedimiento_facturacion"])

            item_code = item_code[0]["item_code"] if item_code else ""

            item_type = "Item"

            item = frappe.new_doc("qp_md_DocumentItem")

            setup_item(item,item_code, line["codigo_procedimiento_facturacion"], line["cantidad_a_facturar"], 
                    line_no, item_type, document, document.patient_code, line["paquete_o_sesion"])
            
            document.items.append(item)

            if line["cuota_moderadora"] > 0:

                line_no += 1000

                item = frappe.new_doc("qp_md_DocumentItem")

                setup_item(item, "28050501", "28050501", line["cantidad_a_facturar"],
                           line_no, "G/L Account", document, document.patient_code, line["paquete_o_sesion"], cuota_moderadora = line["cuota_moderadora"])

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

def setup_document(lines_iter, upload_id):

    code_customer, error_customer, msg_error_customer = get_nit_customer(lines_iter)
        
    code_dimension, error_dimension, msg_error_dimension = get_code_dimension(lines_iter)

    code_patient, error_patient, msg_error_patient = get_nit_patient(lines_iter)

    code_contrat_patient, error_contrat_patient, msg_error_contrat_patient = get_contract_patient(code_patient)


    code_cuota_moderadora, error_cuota_moderadora, msg_error_cuota_moderadora = get_cuota_moderadora(lines_iter)

    code_numero_autorizacion, error_numero_autorizacion, msg_error_numero_autorizacion = get_numero_autorizacion(lines_iter)

    document = frappe.new_doc("qp_md_Document")

    document.customer_code = code_customer

    document.document_type = "Invoice"

    document.headquarter_code = code_dimension

    document.posting_date = today()

    document.lhc_contrato = code_contrat_patient

    document.lhc_cuota_moderadora = code_cuota_moderadora if code_cuota_moderadora and code_cuota_moderadora != '0' else 0

    document.lhc_numero_autorizacion = code_numero_autorizacion

    document.lhc_consecutivo_interno = lines_iter[0]["id_unico_ingreso_fuente_no_cargo"]

    document.lhc_documento = lines_iter[0]["id_unico_ingreso_fuente_no_cargo"]

    document.lhc_tipo_operacion_davita = "SS-CUFE" if code_cuota_moderadora else "SS-SinAporte"

    document.lhc_tipo_factura_doc = "Estándar"

    document.vat_registration_no = code_customer

    document.patient_code = code_patient

    document.upload_id = upload_id

    set_fecha_periodo(document)

    error = error_customer or error_dimension or error_cuota_moderadora or error_numero_autorizacion or error_patient or error_contrat_patient

    msg = msg_error_customer + msg_error_dimension + msg_error_numero_autorizacion + msg_error_cuota_moderadora + msg_error_patient + msg_error_contrat_patient

    document.is_valid = not error

    document.error = msg

    return document

def get_contract_patient(code_patient):
    
    
    contract = frappe.get_list("qp_md_Contract", filters = {"id_cliente": code_patient, "estado_contrato": "Activo"}, pluck = "id_contrato")

    if not contract:

        return "", True, "Paciente {} No posee un contrato activo\n".format(code_patient)
    
    return contract[0], False, ""

def get_nit_patient(lines_iter):
    
    patient_code = list(set(map(lambda x: x["no_identificacion"], lines_iter)))

    if len(patient_code) > 1:

        return patient_code[0], True, "Paciente {} diferentes para la misma factura\n".format(patient_code)
    
    patient = frappe.get_list("qp_md_Patient", filters = {"numero_identificacion": patient_code[0] }, fields = ["*"])
    
    if not patient:

        return lines_iter[0]["no_identificacion"], True, "Paciente {} No existe\n".format(lines_iter[0]["no_identificacion"])

    
    return patient[0].numero_identificacion, False, ""

def get_cuota_moderadora(lines_iter):

    cuota_moderadora = list(set(map(lambda x: x["cuota_moderadora"] , lines_iter)))

    if len(cuota_moderadora) > 1:

        return cuota_moderadora[0], True, "Cuota moderadora diferentes para la misma factura: {}\n".format(cuota_moderadora)

    return cuota_moderadora[0], False, ""

def get_numero_autorizacion(lines_iter):

    numero_autorizacion = list(set(map(lambda x: x["autorizacion_final"] , lines_iter)))

    if len(numero_autorizacion) > 1:

        return numero_autorizacion[0], True, "Numero Autorizacion diferentes para la misma factura: {}\n".format(numero_autorizacion)

    return numero_autorizacion[0], False, ""

def set_fecha_periodo(document):

    date_format = datetime.strptime(document.posting_date, '%Y-%m-%d')

    document.lhc_periodo_inicio_fecha_fact =  datetime.strftime(date_format + relativedelta(day=1), '%Y-%m-%d')

    document.lhc_periodo_fin_fecha_fact =datetime.strftime( date_format + relativedelta(day=31), '%Y-%m-%d')
    

def setup_item(item,item_code, item_code_2, quantity, line, type_code, document, patient_code, paquete_o_sesion
               ,document_type = "Invoice", modality_code = "HD", cuota_moderadora = 0):

    #item_code = "C4110" if item_code_2 == "399501" and paquete_o_sesion == "PAQUETE" else item_code_2

    item.item_code  = item_code
    item.item_code2  = item_code_2
    item.quantity = quantity
    item.line = line
    item.type_code = type_code
    item.filtered_type_field = type_code
    item.customer_code = document.customer_code
    item.headquarter_code = document.headquarter_code
    item.patient_code = patient_code
    item.document_type = document_type
    item.modality_code = modality_code
    item.parentfield = "items"
    
    if type_code == "G/L Account":
        
        item.unit_price =  cuota_moderadora
        
        item.line_amount = cuota_moderadora

        item.quantity = 1

    #item.document_code = None



def get_nit_customer(lines_iter):

    #document_code = list(set(map(lambda x: "{}-{}".format(x["nit"],x["regimen"][0]) , lines_iter)))
    document_code = list(set(map(lambda x: x["nit"] , lines_iter)))

    if len(document_code) > 1:

        return document_code[0], True, "Clientes diferentes para la misma factura: {}\n".format(document_code)
    
    if not frappe.db.exists("Customer", {"tax_id": document_code[0] }):

        return document_code[0], True, "Clientes {} No existe \n".format(document_code[0])

    return document_code[0], False, ""

def get_code_dimension(lines_iter):

    dimension_code = list(set(map(lambda x: x["sede_de_origne"], lines_iter)))

    if len(dimension_code) > 1:

        return dimension_code[0], True, "Sede {} diferentes para la misma factura\n".format(dimension_code)
    
    headquarter = frappe.get_list("qp_md_headquarter", {"title": dimension_code[0] })
    
    if not headquarter:

        return lines_iter[0]["sede_de_origne"], True, "Sede {} No existe\n".format(lines_iter[0]["sede_de_origne"])

    
    return headquarter[0].name, False, ""