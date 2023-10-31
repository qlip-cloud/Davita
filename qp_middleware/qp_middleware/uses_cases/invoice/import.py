import frappe
from qp_middleware.qp_middleware.service.document.save import handler as document_save
from qp_middleware.qp_middleware.service.document.sync import handler as document_sync

from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

def handler(upload_xlsx, method):

    rows = read_xlsx_file_from_attached_file(file_url = upload_xlsx.file)

    save_row(rows, upload_xlsx.name)

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    result = document_save(upload_xlsx)

    upload_xlsx.invoice_total = result["invoice_total"]
    upload_xlsx.invoice_success = result["invoice_success"]
    upload_xlsx.invoice_error = result["invoice_error"]
    upload_xlsx.customer_count = result["customer_count"]
    upload_xlsx.item_count = result["item_count"]
    upload_xlsx.is_valid = result["is_valid"]

    if upload_xlsx.is_valid:
    
        result = document_sync(upload_xlsx, setup, enviroment)
        
        upload_xlsx.send_success = result["send_success"]
    
        upload_xlsx.send_error = result["send_error"]

    frappe.db.commit()

def save_row(rows, upload_id):

    for row in rows:
        if row[0] and row[8] and row[14] and row[37] and row[51]:
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
                "group_code": row[2]+'-'+row[14]
            })

            doc.insert()