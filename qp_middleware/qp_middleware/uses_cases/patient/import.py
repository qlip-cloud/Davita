import frappe
import json
from qp_middleware.qp_middleware.service.document.save import handler as document_save
from qp_middleware.qp_middleware.service.document.sync import handler as document_sync

from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

def handler(upload_patient, method):

    rows = read_xlsx_file_from_attached_file(file_url = upload_patient.file)

    list_repeat,list_group_code = save_row(rows, upload_patient.name)

    setup = frappe.get_doc("qp_md_Setup")

    enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    upload_patient.total = len(list_group_code)

    upload_patient.total_created = len(list_group_code) - len(list_repeat)

    upload_patient.total_repeat = len(list_repeat)

    frappe.db.commit()

def save_row(rows, upload_id):

    list_group_code = []

    list_doc = []

    row_valid = False

    for row in rows:

        if row_valid and row[0]:
        
            group_code = str(row[0]+'-'+str(row[1])).lower()

            doc = frappe.get_doc({
                'doctype': 'qp_md_Patient',
                "tipo_identificacion": row[0],
                "numero_identificacion": row[1],
                "primer_nombre": row[2],
                "segundo_nombre": row[3],
                "primer_apellido": row[4],
                "segundo_apellido": row[5],
                "numero_telefonico": row[6],
                "correo_electronico": row[7],
                "id_plan": row[8],
                "tipo_usuario": row[9],
                "upload_id": upload_id,
                "group_code": group_code,
                "origin": "Excel"
            })

            set_request(doc)

            list_group_code.append(group_code)

            list_doc.append(doc)
        
        if row[0] == "Tipo de identificación":

            row_valid = True

    if list_doc:
        
        return search_repeat(list_doc, set(list_group_code))

    return 0,0

def set_request(doc):

    doc.request = json.dumps({
            "tipoIdentificacion": doc.tipo_identificacion,
            "numeroIdentificacion": str(doc.numero_identificacion),
            "primerNombre": doc.primer_nombre,
            "segundoNombre": doc.segundo_nombre,
            "primerApellido": doc.primer_apellido,
            "segundoApellido": doc.segundo_apellido,
            "numeroTelefonico": str(doc.numero_telefonico),
            "correoElectronico": doc.correo_electronico,
            "idPlan": str(doc.id_plan) if doc.id_plan else "",
            "tipoUsuario": doc.tipo_usuario
        })

def search_repeat(list_doc, list_group_code):

    list_repeat = frappe.db.get_list('qp_md_Patient',filters = {"group_code": ["in", list_group_code]}, pluck='group_code')

    for doc in list_doc:

        if  doc.group_code not in list_repeat:

            doc.insert()

    return list_repeat, list_group_code