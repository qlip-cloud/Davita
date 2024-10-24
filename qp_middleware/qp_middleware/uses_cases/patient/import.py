import frappe
import json
from qp_middleware.qp_middleware.service.document.save import handler as document_save
from qp_middleware.qp_middleware.service.document.sync import handler as document_sync
from frappe.utils import now, getdate
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
from qp_middleware.qp_middleware.service.util.sync import get_response, persist
from datetime import date
from datetime import datetime

def handler(upload_patient, method):

    rows = read_xlsx_file_from_attached_file(file_url = upload_patient.file)

    tuple_list,total, total_created, total_repeat, errors, total_error = save_row(rows, upload_patient.name)

    insert_data(tuple_list)

    upload_patient.total = total

    upload_patient.total_created = total_created

    upload_patient.total_repeat = total_repeat
    
    upload_patient.errors = errors

    upload_patient.total_error = total_error

    frappe.db.commit()

def insert_data(tuple_list):

    if tuple_list:

        table = "tabqp_md_Patient"

        fields = """(name, nombre_identificacion, tipo_identificacion,numero_identificacion,primer_apellido,segundo_apellido,primer_nombre,segundo_nombre,
        numero_telefonico,celular,direccion,tipo_usuario,nombre_usuario,cod_responsable, tipo_atencion, fecha_mov,upload_id,group_code,dimension,origin, request,creation, 
        modified, modified_by, owner)"""

        persist(table, fields, tuple_list)

def save_row(rows, upload_id):

    list_group_code = []

    row_valid = False

    list_group_code = frappe.db.get_list('qp_md_Patient', pluck='group_code')

    tuple_list = []

    total = 0

    format_tipos_Identificaciones = get_format("qp_md_TipoIdentificacion", "code", "description")

    format_tipos_usuarios = get_format("qp_md_TipoUsuario", "description", "code")

    format_tipos_atencion = get_format("qp_md_TipoAtencion", 'code', "title")

    format_cod_responsable = get_format("qp_md_Responsable", 'code', "title")

    new_group_code = []
    
    repeat = 0

    error = ''

    count_error = 0

    for row in rows:

        if row_valid and row[0]:

            nombre_identificacion = format_tipos_Identificaciones.get(row[0]) or ""

            codigo_usuario = format_tipos_usuarios.get(row[10]) or ""

            code_responsable = format_cod_responsable.get(row[11]) or False
            
            if not code_responsable:

                error += f'Cod Responsabilidad {row[11]} del Paciente {row[1]} No configurado\n'
                
                count_error += 1

            tipo_atencion = format_tipos_atencion.get(row[12]) or False

            if not tipo_atencion:

                count_error += 1

                error += f'Tipo de Atencion {row[12]} del Paciente {row[1]} No configurado\n'
            
                
            if not code_responsable or not tipo_atencion:

                continue

            fecha_mov = ""

            try:
                 
                fecha_mov = getdate(row[13]) if not isinstance(row[13], datetime) else row[13]

            except:

                pass
        
            if nombre_identificacion and fecha_mov:

                total += 1

                dimension = str(row[0] + str(row[1])).upper()
                
                group_code = str(dimension + '_' + row[9]).upper()

                if (not group_code in list_group_code) and (not group_code in new_group_code):
                
                    tuple_list.append(
                        (
                            group_code, 
                            nombre_identificacion,
                            row[0] or "",
                            row[1] or "",
                            row[2] or "",
                            row[3] or "",
                            row[4] or "",
                            row[5] or "",
                            row[6] or "",
                            row[7] or "",
                            row[8] or "",
                            row[9] or "",
                            codigo_usuario,
                            code_responsable,
                            tipo_atencion,
                            str(fecha_mov),
                            upload_id, group_code, dimension, "Excel", 
                            set_request(row, nombre_identificacion, codigo_usuario, tipo_atencion, code_responsable) ,
                            now(),now(), "Administrator", "Administrator" 
                        )
                    )

                    new_group_code.append(group_code)

                else:
                    repeat += 1

        if row[0] == "TIPO_IDENT":

            row_valid = True

    if tuple_list:
        
        return tuple_list, total, len(tuple_list), repeat, error, count_error

    return [],total,0, repeat, error, count_error

def get_format_tipos_Identificaciones(format_tipos_Identificaciones):

    tipos_identificaciones = frappe.get_list("qp_md_TipoIdentificacion", fields = ["description", "code"])

    for tipo_identificaciones  in tipos_identificaciones:

        format_tipos_Identificaciones.update({tipo_identificaciones.get("code"): tipo_identificaciones.get("description")})

def get_format_tipos_usuarios(format_tipos_usuarios):

    tipos_usuarios = frappe.get_list("qp_md_TipoUsuario", fields = ["description", "code"])

    for tipo_usuario  in tipos_usuarios:

        format_tipos_usuarios.update({tipo_usuario.get("description"): tipo_usuario.get("code")})

def get_format(doctype, key, value):

    results = frappe.get_list(doctype, fields = [key, value])

    dic_result = {}

    for result  in results:

        dic_result.update({result.get(key): result.get(value)})

    return dic_result

def set_request(row, nombre_identificacion, codigo_usuario, tipo_atencion, code_responsable):

    return json.dumps({
            "tipoIdentificacion": nombre_identificacion,
            "numeroIdentificacion": str(row[1]),
            "primerNombre": row[4] or "",
            "segundoNombre": row[5] or "",
            "primerApellido": row[2] or "",
            "segundoApellido": row[3] or "",
            "numeroTelefonico": str(row[6] or ""),
            "correoElectronico": "",
            "idPlan": "",
            "tipoUsuario": codigo_usuario,
            "Eps": code_responsable,
            "Modalidad": tipo_atencion
        })