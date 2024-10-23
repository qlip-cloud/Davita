import frappe
from datetime import datetime
from dateutil.relativedelta import relativedelta

def init_document(upload_xlsx, line, code_customer, code_cuota_moderadora, code_contrat_patient, code_numero_autorizacion, code_dimension, code_patient, numero_orden_compra, group_code, tipo_operacion = None):

        
    document = frappe.new_doc("qp_md_Document")

    document.customer_code = code_customer

    document.document_type = "Invoice"

    document.headquarter_code = code_dimension

    document.posting_date = upload_xlsx.invoice_date

    document.lhc_contrato = code_contrat_patient
    
    document.invoice_value = line["vr_a_facturar"] 

    document.cod_empresa = line["cod_empresa"]

    document.lhc_cuota_moderadora = code_cuota_moderadora if code_cuota_moderadora and code_cuota_moderadora != '0' else 0

    document.lhc_numero_autorizacion = code_numero_autorizacion

    document.lhc_consecutivo_interno = line["id_unico_ingreso_fuente_no_cargo"]

    document.lhc_documento = line["id_unico_ingreso_fuente_no_cargo"]
    
    lhc_tipo_operacion_davita = "SS-CUFE" if code_cuota_moderadora else "SS-SinAporte"

    document.lhc_tipo_operacion_davita = lhc_tipo_operacion_davita if not tipo_operacion else lhc_tipo_operacion_davita + " " + tipo_operacion

    document.lhc_tipo_factura_doc = "Estándar"

    document.lhc_mipres = ""

    document.lhc_id_mipres = ""

    document.lhc_no_poliza = ""

    document.currency_code = ""
    
    document.responsibility_center = code_dimension

    document.lhc_numero_orden_compra = numero_orden_compra 

    document.work_description = ""

    document.vat_registration_no = code_customer

    document.patient_code = code_patient

    document.upload_id = upload_xlsx.name
    
    document.group_code = group_code

    document.lhc_periodo_inicio_fecha_fact =  upload_xlsx.invoice_start

    document.lhc_periodo_fin_fecha_fact = upload_xlsx.invoice_end
    
    return document

def set_fecha_periodo(document):

    date_format = datetime.strptime(document.posting_date, '%Y-%m-%d')

    document.lhc_periodo_inicio_fecha_fact =  datetime.strftime(date_format + relativedelta(day=1), '%Y-%m-%d')

    document.lhc_periodo_fin_fecha_fact =datetime.strftime( date_format + relativedelta(day=31), '%Y-%m-%d')
    
def get_nit_customer_no_repeat(lines_iter):

    document_set = list(set(map(lambda x: x["nit"] , lines_iter)))

    if len(document_set) > 1:

        return document_set[0], True, "Clientes diferentes para la misma factura: {}\n".format(document_set)
    
    return get_from_tax_id(document_set[0], lines_iter)

def get_cuota_moderadora_no_repeat(lines_iter):

    cuota_moderadora = list(set(map(lambda x: x["cuota_moderadora"] , lines_iter)))

    if len(cuota_moderadora) > 1:

        return cuota_moderadora[0], True, "Cuota moderadora diferentes para la misma factura: {}\n".format(cuota_moderadora)
    
    return cuota_moderadora[0], False, ""

def get_from_tax_id(document_set, lines_iter):
     
    document_code = document_set.split("_")
    
    line = list(filter(lambda x: x["nit"] == document_set, lines_iter))
    
    document_code_complete = "{}-{}".format(document_code[0],line[0]["regimen"][0])

    tax_id = frappe.db.get_list("Customer", {"tax_id": ["in", (document_code[0], document_code_complete)]}, 'tax_id')

    if not tax_id:

        return document_code[0], True, "Clientes {} No existe \n".format(document_code[0])

    return tax_id[0]['tax_id'], False, ""

def get_items_codes(line, document):
    
    invoice_value = 0 if document.lhc_contrato else float(document.invoice_value)
    
    quantity = float(line["cantidad_a_facturar"])
    
    unit_price = invoice_value / quantity

    item_code = ""
    
    item_code_2 = line["codigo_procedimiento_facturacion"]
    
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

        item_code = frappe.get_value("Item",  {"qp_item_code_2": item_code_2 }, ["item_code"])

        item_code = item_code or ""

    if not item_code:

        if document.is_valid:
            
            document.is_valid = False
        
        document.error += "Producto {} no existe".format(item_code_2)
        
    return item_code, item_code_2, quantity, unit_price

def get_contract_customer(code_customer):
    
    contract = frappe.get_value("qp_md_Contract", {"id_cliente": code_customer, "estado_contrato": "Activo"}, ["id_contrato"])

    if not contract:

        return "", False, "Cliente {} No posee un contrato activo\n".format(code_customer)
    
    return contract, False, ""

def get_code_modality(codes_servinte, document):

    code_dynamics = frappe.db.get_value("qp_md_Modality", {"code_servinte": codes_servinte}, ["code_dynamics"])
    
    if not code_dynamics:
       
        document.is_valid = False

        document.error += "Modalidad {} No existe\n".format(codes_servinte)

        return codes_servinte
        
    return code_dynamics

def set_document_error(document, error_customer = "", error_contrat_patient = "", error_dimension = "", error_cuota_moderadora = "", error_numero_autorizacion = "", error_patient = "", msg_error_customer = "", msg_error_dimension = "", msg_error_numero_autorizacion = "", msg_error_cuota_moderadora = "", msg_error_patient = "", msg_error_contrat_patient= ""):
    
    error = error_customer or error_dimension or error_cuota_moderadora or error_numero_autorizacion or error_patient or error_contrat_patient

    msg = msg_error_customer + msg_error_dimension + msg_error_numero_autorizacion + msg_error_cuota_moderadora + msg_error_patient + msg_error_contrat_patient

    document.is_valid = not error

    document.error = msg
    
    
def get_code_dimension_not_repeat(lines_iter):

    dimension_code = list(set(map(lambda x: x["sede_de_origne"], lines_iter)))

    if len(dimension_code) > 1:

        return dimension_code[0], True, "Sede {} diferentes para la misma factura\n".format(dimension_code)
    
    return get_code_dimension(dimension_code[0])
    
def get_code_dimension(dimension_code):
    
    headquarter = frappe.get_value("qp_md_headquarter", {"title": dimension_code}, ["name"])
    
    if not headquarter:

        return dimension_code, True, "Sede {} No existe\n".format(dimension_code)

    
    return headquarter, False, ""