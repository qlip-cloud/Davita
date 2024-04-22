import frappe
import time
from datetime import datetime
import json
from frappe.utils import today
import requests

from dateutil.relativedelta import relativedelta

COD = ["JF-", "EJC", "PL1"]

LIMIT = {
    "JF-": 3,
    "EJC": 3,
    "PL1": 2
}

@frappe.whitelist()
def handler(upload_xlsx):
    
    lines = frappe.get_list("qp_md_invoice_sync", filters = {"upload_id": upload_xlsx.name, "is_repeat": False}, fields = ["*"])

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
            
            item_code_2 = line["codigo_procedimiento_facturacion"]

            item_code = ""

            invoice_value = 0 if document.lhc_contrato else float(document.invoice_value)
            
            quantity = float(line["cantidad_a_facturar"])

            quantity_invoice = float(line["cantidad_a_facturar"])

            unit_price = invoice_value / quantity

            item_type = "Item"

            code_modality, error_modality, msg_error_modality = get_code_modality(line["codigo_centro_de_costo"])
            
            if error_modality:
                
                document.is_valid = not error_modality

                document.error += msg_error_modality

            if item_code_2 == "399501":

                if line["tipo_servicio"] == "HD PAQUETE":

                    item_code = "IG01002"

                    item_code_2 = "C40111"

                    quantity = 1
                    
                    unit_price = 0

                else:
                    
                    if line["tipo_servicio"] in ("HD SESSION", "HD SESION"):

                        item_code = "IG01001"

            else:

                item_code = frappe.get_list("Item", filters = {"qp_item_code_2": item_code_2 }, fields = ["item_code"])

                item_code = item_code[0]["item_code"] if item_code else ""

            if not item_code:

                if document.is_valid:
                    
                    document.is_valid = False
                
                document.error += "Producto {} no existe".format(item_code_2)

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

    code_customer, error_customer, msg_error_customer = get_nit_customer(lines_iter)
        
    code_dimension, error_dimension, msg_error_dimension = get_code_dimension(lines_iter)

    code_patient, error_patient, msg_error_patient = get_nit_patient(lines_iter)

    code_contrat_patient, error_contrat_patient, msg_error_contrat_patient = get_contract_customer(code_customer)

    code_cuota_moderadora, error_cuota_moderadora, msg_error_cuota_moderadora = get_cuota_moderadora(lines_iter)

    code_numero_autorizacion, error_numero_autorizacion, msg_error_numero_autorizacion = get_numero_autorizacion(lines_iter)

    document = frappe.new_doc("qp_md_Document")

    document.customer_code = code_customer

    document.document_type = "Invoice"

    document.headquarter_code = code_dimension

    document.posting_date = upload_xlsx.invoice_date

    document.lhc_contrato = code_contrat_patient
    
    document.invoice_value = lines_iter[0]["vr_a_facturar"] 

    document.cod_empresa = lines_iter[0]["cod_empresa"]

    document.lhc_cuota_moderadora = code_cuota_moderadora if code_cuota_moderadora and code_cuota_moderadora != '0' else 0

    document.lhc_numero_autorizacion = code_numero_autorizacion

    document.lhc_consecutivo_interno = lines_iter[0]["id_unico_ingreso_fuente_no_cargo"]

    document.lhc_documento = lines_iter[0]["id_unico_ingreso_fuente_no_cargo"]

    document.lhc_tipo_operacion_davita = "SS-CUFE" if code_cuota_moderadora else "SS-SinAporte"

    document.lhc_tipo_factura_doc = "Estándar"

    document.lhc_mipres = ""

    document.lhc_id_mipres = ""

    document.lhc_no_poliza = ""

    document.currency_code = ""
    
    document.responsibility_center = code_dimension

    document.lhc_numero_orden_compra = get_orden_compra(document.cod_empresa, lines_iter[0]["nit"])

    document.work_description = ""

    document.vat_registration_no = code_customer

    document.patient_code = code_patient

    document.upload_id = upload_xlsx.name
    
    document.group_code = lines_iter[0]["group_code"] 

    document.lhc_periodo_inicio_fecha_fact =  upload_xlsx.invoice_start

    document.lhc_periodo_fin_fecha_fact = upload_xlsx.invoice_end

    error = error_customer or error_dimension or error_cuota_moderadora or error_numero_autorizacion or error_patient or error_contrat_patient

    msg = msg_error_customer + msg_error_dimension + msg_error_numero_autorizacion + msg_error_cuota_moderadora + msg_error_patient + msg_error_contrat_patient

    document.is_valid = not error

    document.error = msg

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


def get_contract_customer(code_customer):
    
    contract = frappe.get_list("qp_md_Contract", filters = {"id_cliente": code_customer, "estado_contrato": "Activo"}, pluck = "id_contrato")

    if not contract:

        return "", False, "Cliente {} No posee un contrato activo\n".format(code_customer)
    
    return contract[0], False, ""

def get_nit_patient(lines_iter):
    
    patient_code = list(set(map(lambda x: x["no_identificacion"], lines_iter)))

    if len(patient_code) > 1:

        return patient_code[0], True, "Paciente {} diferentes para la misma factura\n".format(patient_code)
    
    patient = frappe.get_list("qp_md_Patient", filters = {"numero_identificacion": patient_code[0] }, fields = ["*"])
    
    if not patient:

        return lines_iter[0]["no_identificacion"], True, "Paciente {} No existe\n".format(lines_iter[0]["no_identificacion"])

    patient_nit = lines_iter[0]["tipo_documento"] + str(lines_iter[0]["no_identificacion"])

    return patient_nit, False, ""

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


def get_nit_customer(lines_iter):

    document_set = list(set(map(lambda x: x["nit"] , lines_iter)))

    if len(document_set) > 1:

        return document_set[0], True, "Clientes diferentes para la misma factura: {}\n".format(document_set)
    
    document_code = document_set[0].split("_")
    
    line = list(filter(lambda x: x["nit"] == document_set[0], lines_iter))
    
    document_code_complete = "{}-{}".format(document_code[0],line[0]["regimen"][0])

    tax_id = frappe.db.get_list("Customer", {"tax_id": ["in", (document_code[0], document_code_complete)]}, 'tax_id')

    if not tax_id:

        return document_code[0], True, "Clientes {} No existe \n".format(document_code[0])

    return tax_id[0]['tax_id'], False, ""


def get_code_modality(codes_servinte):

    code_dynamics = frappe.db.get_value("qp_md_Modality", {"code_servinte": codes_servinte}, ["code_dynamics"])
    
    if not code_dynamics:

        return codes_servinte, True, "Modalidad {} No existe\n".format(codes_servinte)

    return code_dynamics, False, ""

def get_code_dimension(lines_iter):

    dimension_code = list(set(map(lambda x: x["sede_de_origne"], lines_iter)))

    if len(dimension_code) > 1:

        return dimension_code[0], True, "Sede {} diferentes para la misma factura\n".format(dimension_code)
    
    headquarter = frappe.get_list("qp_md_headquarter", {"title": dimension_code[0] })
    
    if not headquarter:

        return lines_iter[0]["sede_de_origne"], True, "Sede {} No existe\n".format(lines_iter[0]["sede_de_origne"])

    
    return headquarter[0].name, False, ""