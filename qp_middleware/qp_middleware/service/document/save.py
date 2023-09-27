import frappe
from datetime import datetime
import json
from frappe.utils import today
import requests

from dateutil.relativedelta import relativedelta

from qp_authorization.use_case.oauth2.authorize import get_token

URL_LINE = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/SalesInvoiceLine"

URL_HEADER = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/SalesInvoice"


@frappe.whitelist()
def handler(upload_id):
        
    lines = frappe.get_list("qp_md_invoice_sync", filters = {"upload_id": upload_id}, fields = ["*"])
    #lines = frappe.get_list("qp_md_invoice_test", filters = {"upload_id": upload_id}, fields = ["*"])
    
    documents_code = set(map(lambda x: x["id_unico_ingreso_fuente_no_cargo"], lines))

    group_lines = [[y for y in lines if y["id_unico_ingreso_fuente_no_cargo"]==x] for x in documents_code]
    
    response = []
    
    is_valid = True
    
    for lines_iter in group_lines:
        
        document = setup_document(lines_iter)
        
        line_no = 1000

        document.items = []

        for line in lines_iter:

            item_qp_type = frappe.get_list("Item", filters = {"item_code": line["codigo_procedimiento_facturacion"] }, fields = ["qp_type", "item_code"])

            if not item_qp_type:

                if document.is_valid:
                    
                    document.is_valid = False
                
                document.error += "Producto {} no existe".format(line["codigo_procedimiento_facturacion"])

            item_code = item_qp_type[0]["item_code"] if item_qp_type else ""

            item_type = "Item"

            item = frappe.new_doc("qp_md_DocumentItem")

            setup_item(item,item_code, line["codigo_procedimiento_facturacion"], line["cantidad_a_facturar"], 
                    line_no, item_type, document, document.patient_code, line["paquete_o_sesion"])
            
            document.items.append(item)

            if line["cuota_moderadora"] == "0":

                line_no += 1000

                item = frappe.new_doc("qp_md_DocumentItem")

                setup_item(item, item_code, "28050501", line["cantidad_a_facturar"],
                           line_no, "G/L Account", document, document.patient_code, line["paquete_o_sesion"])

                document.items.append(item)

            line_no += 1000
        
        document.insert()  

        response.append(document)

        if is_valid and not document.is_valid:

            is_valid = False

    if is_valid:

        for document in response:

            setup_header_json(document)

            if document.document_code:

                document.is_complete = True

                for item in document.items:

                    item.document_code = document.document_code

                    setup_item_json(item, document)

                            #valida q al terminar todo se mando y completa el documento
            document.save()  
        
    frappe.db.commit()  

    return response

def setup_document(lines_iter):

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

    document.lhc_cuota_moderadora = code_cuota_moderadora or 0

    document.lhc_numero_autorizacion = code_numero_autorizacion

    document.lhc_consecutivo_interno = lines_iter[0]["id_unico_ingreso_fuente_no_cargo"]

    document.lhc_documento = lines_iter[0]["id_unico_ingreso_fuente_no_cargo"]

    document.vat_registration_no = code_customer

    document.patient_code = code_patient


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

    document.lhc_periodo_inicio_fecha_fact =  date_format + relativedelta(day=1)
    document.lhc_periodo_fin_fecha_fact = date_format + relativedelta(day=31)
    

def setup_item(item,item_code, item_code_2, quantity, line, type_code, document, patient_code, paquete_o_sesion, document_type = "Invoice", modality_code = "HD"):

    item_code = "C4110" if item_code_2 == "399501" and paquete_o_sesion == "PAQUETE" else item_code_2

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
        
        item.unit_price = -200000
        
        item.line_amount = -200000

        item.quantity = 1

    #item.document_code = None

def setup_header_json(document):
    
    token = get_token()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }

    document.request = json.dumps({   
                    "Document_Type": document.document_type,
                    "Sell_to_Customer_No": document.customer_code,
                    "Posting_Date": document.posting_date,
                    #"VAT_Registration_No": document.vat_registration_no,
                    "Shortcut_Dimension_1_Code": document.customer_code, 
                    "Shortcut_Dimension_2_Code": document.headquarter_code,
                    #"LHCPuntodefacturacion": document.lhc_punto_de_facturacion,
                    "LHCContrato": document.lhc_contrato or "", 
                    "LHCCuotaModeradora": int(document.lhc_cuota_moderadora),
                    "LHCCopago": int(document.lhc_copago),
                    "LHCCuotaRecuperacion": int(document.lhc_cuota_recuperacion),
                    "LHCPagosCompartidosPVS": int(document.lhc_pagos_compartidos_pvs),
                    "LHCNumeroAutorizacion": document.lhc_numero_autorizacion,
                    "LHCPeriodoInicioFechaFact": datetime.strftime(document.lhc_periodo_inicio_fecha_fact, "%Y-%m-%d"),
                    "LHCPeriodoFinFechaFact": datetime.strftime(document.lhc_periodo_fin_fecha_fact, "%Y-%m-%d"),
                    "LHCNumeroContacto": document.lhc_numero_contacto,
                    "LHCNumeroOrdenCompra": document.lhc_numero_orden_compra,
                    "LHCConsecutivoInterno": document.lhc_consecutivo_interno,
                    "LHCDocumento": document.lhc_documento
            })
    response = requests.post(URL_HEADER, headers=headers, data=document.request)

    document.response = response.text

    response_json = json.loads(response.text)

    if not "error" in response_json:
        
        document.document_code = response_json["No"]

def setup_item_json(item, document):
    
    token = get_token()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(token)
    }

    request = {
        "Document_Type": "Invoice",
        "Document_No": item.document_code,
        "Line_No": item.line,
        "Type": item.type_code,
        "FilteredTypeField": item.type_code,
        "No": item.item_code,
        "Quantity": int(item.quantity),            
        "Shortcut_Dimension_1_Code": item.customer_code,
        "Shortcut_Dimension_2_Code": item.headquarter_code,
        "ShortcutDimCode3": "",
        "ShortcutDimCode4": "",
        "ShortcutDimCode5": item.patient_code,
        "ShortcutDimCode6": item.modality_code,
        "ShortcutDimCode7": "",
        "ShortcutDimCode8": ""
    }

    if item.type_code == "G/L Account":

        request.update({    
            "Unit_Price": item.unit_price,
            "Line_Amount": item.line_amount
        })
    
    item.request = json.dumps(request)
    response = requests.post(URL_LINE, headers=headers, data=item.request)

    item.response = response.text

    if "error" in json.loads(item.response) and document.is_complete:
        
        document.is_complete = False

def get_nit_customer(lines_iter):

    document_code = list(set(map(lambda x: x["nit"] , lines_iter)))
    #document_code = list(set(map(lambda x: "{}-{}".format(x["nit"], x["nit"]) , lines_iter)))

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