import frappe
from qp_middleware.qp_middleware.service.document.save import handler as document_save
from qp_middleware.qp_middleware.service.document.sync import handler as document_sync

from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

def handler(upload_xlsx, method):

    if upload_xlsx.is_background:

        return {
            "status": 500,
            "msg": "Ya existe una confirmacion en proceso"
        }
    
    upload_xlsx.is_background = True

    upload_xlsx.save()

    frappe.enqueue(
                import_xlsx,
                queue='long',                
                #is_async=True,
                now = True,
                job_name="send invoice: "+ upload_xlsx.name,
                timeout=5400000,
                upload_xlsx = upload_xlsx
                )

def import_xlsx(upload_xlsx):
    
    try:

        list_repeat,list_group_code = import_excel(upload_xlsx)

        result = document_save(upload_xlsx)

        set_stadistic(upload_xlsx, list_group_code, list_repeat, result)
        
        sync_invoices(upload_xlsx)

    except Exception as error:

        frappe.log_error(message=frappe.get_traceback(), title="Error importando xlsx: "+ upload_xlsx.name)

        upload_xlsx.error = True

    upload_xlsx.is_background = False

    upload_xlsx.save()

def sync_invoices(upload_xlsx):

    if upload_xlsx.is_valid:
        
        setup = frappe.get_doc("qp_md_Setup")

        enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)
        
        result = document_sync(upload_xlsx, setup, enviroment)
        
        upload_xlsx.send_success = result["send_success"]
    
        upload_xlsx.send_error = result["send_error"]

def set_stadistic(upload_xlsx, list_group_code, list_repeat, result):

    upload_xlsx.invoice_total = len(list_group_code)
    upload_xlsx.total_repeat = len(list_repeat)
    upload_xlsx.invoice_repeat = str(list_repeat).replace(",","\n")
    upload_xlsx.invoice_success = result["invoice_success"]
    upload_xlsx.invoice_error = result["invoice_error"]
    upload_xlsx.customer_count = result["customer_count"]
    upload_xlsx.item_count = result["item_count"]
    upload_xlsx.is_valid = result["is_valid"]

def import_excel(upload_xlsx):

    rows = read_xlsx_file_from_attached_file(file_url = upload_xlsx.file)

    return save_row(rows, upload_xlsx.name)

def save_row(rows, upload_id):

    list_group_code = []

    list_doc = []

    for row in rows:

        if row[0] and row[8] and row[14] and row[37] and row[51]:

            group_code = str(row[2])+'-'+str(row[14])

            doc = frappe.get_doc({
                'doctype': 'qp_md_invoice_sync',
                "proveedor": row[0],
                "numero": row[1],
                "sede_de_origne": row[2],
                "transitorio": row[3],
                "responsable": row[4],
                "unidad_renal": row[5],
                "eps": row[6],
                "tipo_documento": row[7],
                "no_identificacion": row[8],
                "nombre_paciente": row[9],
                "primer_apellido_del_paciente": row[10],
                "segundo_apellido__del_paciente": row[11],
                "nombre_tercero": row[12],
                "segundo_nombre": row[13],
                "id_unico_ingreso_fuente_no_cargo": row[14],
                "genero": row[15],
                "edad": row[16],
                "tipo_de_servicio": row[17],
                "cantidad_a_facturar": row[18],
                "facturable": row[19],
                "no_factura": row[20],
                "valor": row[21],
                "cuota_moderadora": row[22],
                "autorizacion_final": row[23],
                "cod_empresa": row[24],
                "codigo_admon": row[25],
                "regimen": row[26],
                "rips": row[27],
                "fecha_de_servicio": row[28],
                "meses_anteriores__referencia_cateter": row[29],
                "observaciones": row[30],
                "empty_1": row[31],
                "sede_servinte": row[32],
                "eps_servinte": row[33],
                "tipo_servicio_servinte": row[34],
                "cantidad_servinte": row[35],
                "cantidad_corregida": row[36],
                "nit": row[37],
                "rango_de": row[38],
                "rango_hasta": row[39],
                "paquete_o_sesion": row[40],
                "vr_a_facturar": row[41],
                "diferencias": row[42],
                "nombre_eps": row[43],
                "tipo_servicio": row[44],
                "cant_censo": row[45],
                "codigo_centro_de_costo": row[46],
                "nombre_centro_de_costo": row[47],
                "admision_sin_admision": row[48],
                "concepto_facturacion": row[49],
                "nombre_concepto": row[50],
                "codigo_procedimiento_facturacion": row[51],
                "nombre_codigo_descripcion": row[52],
                "empty_2": row[53],
                "sede_fuente_cargo": row[54],
                "aut_formula": row[55],
                "estado": row[56],
                "eps_resumida_aut": row[57],
                "no_autorizacion_posterior_al_guion": row[58],
                "largo": row[59],
                "autorizacion_con_letras": row[60],
                "longitud_aut": row[61],
                "autorizacion_diferente_a_la_cedula": row[62],
                "autorizacion_no_duplicada": row[63],
                "auto_iguales": row[64],
                "empty_3": row[65],
                "consecutivo": row[66],
                "empty_4": row[67],
                "vr_paquete_en_cargos_por_usuario": row[68],
                "vr_paquete_facturacion": row[69],
                "vs": row[70],
                "observaciones_1": row[71],
                "upload_id": upload_id,
                "group_code": group_code
            })

            list_group_code.append(group_code)

            list_doc.append(doc)

    if list_doc:
        
        return search_repeat(list_doc, set(list_group_code))

    frappe.throw("No hay lineas validas en el excel")

def search_repeat(list_doc, list_group_code):

    list_repeat = frappe.db.get_list('qp_md_Document',filters = {"group_code": ["in", list_group_code], "document_confirm": ["!=", ""]}, pluck='group_code')

    list_repeat = set(list_repeat)

    for doc in list_doc:

        if doc.group_code in list_repeat:

            doc.is_repeat = True

        doc.insert()

    return list_repeat,list_group_code


