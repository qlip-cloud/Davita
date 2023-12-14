import frappe
import json
from qp_middleware.qp_middleware.service.document.save import handler as document_save
from qp_middleware.qp_middleware.service.document.sync import handler as document_sync
from frappe.utils import now
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

def handler(upload_patient, method):

    rows = read_xlsx_file_from_attached_file(file_url = upload_patient.file)

    tuple_list,total, total_created = save_row(rows, upload_patient.name)

    insert_data(tuple_list)

    #setup = frappe.get_doc("qp_md_Setup")

    #enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    upload_patient.total = total

    upload_patient.total_created = total_created

    upload_patient.total_repeat = total - total_created

    frappe.db.commit()

def insert_data(tuple_list):

    if tuple_list:

        table = "tabqp_md_Patient"

        fields = """(name, nombre_identificacion, tipo_identificacion,numero_identificacion,primer_apellido,segundo_apellido,primer_nombre,segundo_nombre,
        numero_telefonico,celular,direccion,tipo_usuario,nombre_usuario,fecha_mov,upload_id,group_code,dimension,origin, request, request_dimension,creation, 
        modified, modified_by, owner)"""

        persist(table, fields, tuple_list)

def save_row(rows, upload_id):

    list_group_code = []

    row_valid = False

    list_group_code = frappe.db.get_list('qp_md_Patient', pluck='group_code')

    tuple_list = []

    total = 0

    format_tipos_Identificaciones = {}

    format_tipos_usuarios = {}

    get_format_tipos_Identificaciones(format_tipos_Identificaciones)

    get_format_tipos_usuarios(format_tipos_usuarios)

    for row in rows:

        if row_valid and row[0]:

            nombre_identificacion = format_tipos_Identificaciones.get(row[0]) or ""

            codigo_usuario = format_tipos_usuarios.get(row[10]) or ""
        
            if nombre_identificacion:

                total += 1

                dimension = str(row[0] + str(row[1])).upper()
                
                group_code = str(dimension + '_' + row[9]).upper()

                if not group_code in list_group_code:
                
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
                            str(row[11])  or "",
                            upload_id, group_code, dimension, "Excel", 
                            set_request(row, nombre_identificacion, codigo_usuario) ,
                            set_request_dimension(row, dimension),
                            now(),now(), "Administrator", "Administrator" 
                        )
                    )

        if row[0] == "TIPO_IDENT":

            row_valid = True

    if tuple_list:
        
        return tuple_list, total, len(tuple_list)

    return [],total,0


def get_format_tipos_Identificaciones(format_tipos_Identificaciones):

    tipos_identificaciones = frappe.get_list("qp_md_TipoIdentificacion", fields = ["description", "code"])


    for tipo_identificaciones  in tipos_identificaciones:

        format_tipos_Identificaciones.update({tipo_identificaciones.get("code"): tipo_identificaciones.get("description")})

def get_format_tipos_usuarios(format_tipos_usuarios):

    tipos_usuarios = frappe.get_list("qp_md_TipoUsuario", fields = ["description", "code"])

    for tipo_usuario  in tipos_usuarios:

        format_tipos_usuarios.update({tipo_usuario.get("description"): tipo_usuario.get("code")})

def set_request(row, nombre_identificacion, codigo_usuario):

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
            "tipoUsuario": codigo_usuario
        })

def set_request_dimension(row, dimension):

    name = row[4] or ""
    second_name = row[5] or ""
    lastname = row[2] or ""
    second_lastname = row[3] or ""
    return json.dumps({
            "Dimension_Code": "PACIENTE",
            "Code": dimension,
            "Name": name + " " + second_name + " " +lastname + " " +second_lastname,
            "Dimension_Value_Type": "Standard",
            "Blocked": False
        })