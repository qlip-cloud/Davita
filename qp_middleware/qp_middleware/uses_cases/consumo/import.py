import frappe
import json
from qp_middleware.qp_middleware.service.document.save import handler as document_save
from qp_middleware.qp_middleware.service.document.sync import handler as document_sync
from frappe.utils import now
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
from qp_middleware.qp_middleware.service.util.sync import get_response, persist
from uuid import uuid1
def handler(upload_consumo, method):

    rows = read_xlsx_file_from_attached_file(file_url = upload_consumo.file)

    tuple_list,total, total_created = save_row(rows, upload_consumo.name)

    insert_data(tuple_list)

    #setup = frappe.get_doc("qp_md_Setup")

    #enviroment = frappe.get_doc("qp_md_Enviroment", setup.enviroment)

    upload_consumo.total = total

    upload_consumo.total_created = total_created

    upload_consumo.total_repeat = total - total_created

    frappe.db.commit()

def insert_data(tuple_list):

    if tuple_list:

        table = "tabqp_md_Consumo"

        fields = """(name,est_adm,id_unico,ingreso,tipo_identificacion,identificacion,nombre,responsable_eps,
        fecha_ordenamiento,codigo_medicamento,descripcion_medicamento,justificacion_observaciones,posologia,
        cantidad_solicitada,codigo_unidad, descripcion_unidad, codigo_estado, descripcion_estado, codigo_ubicacion,
        descripcion_ubicacion,upload_id, request, headquarter_dynamic, dimension_code, is_dimension_sync, item_dynamic,
        error, is_valid,
        creation, modified, modified_by, owner)"""

        persist(table, fields, tuple_list)

def save_row(rows, upload_id):

    row_valid = False

    list_headquarter = frappe.db.get_list('qp_md_headquarter', filters = {"code_servinte": ["!=", None]}, fields = ["code", "code_servinte"])

    tuple_list = []

    total = 0


    for row in rows:

        if row_valid and row[0]:            
        
            total += 1

            code_headquarter, error_headquarter = get_code_headquarter(row[0], list_headquarter)

            code_item, error_item = get_code_dynamic(row[8])

            is_valid = True if code_headquarter and code_item else False

            error = error_headquarter + error_item

            dimension_code, is_dimension_sync = get_dimension(row[3],str(row[4]))

            posting_date = str(row[7]) or ""
            
            quantity = row[12] or ""
            
            tuple_list.append(
                (
                    str(uuid1()), 
                    row[0] or "",
                    row[1] or "",
                    row[2] or "",
                    row[3] or "",
                    row[4] or "",
                    row[5] or "",
                    row[6] or "",
                    posting_date,
                    row[8] or "",
                    row[9] or "",
                    row[10] or "",
                    row[11] or "",
                    quantity,
                    row[13] or "",
                    row[14] or "",
                    row[15] or "",
                    row[16] or "",
                    row[17] or "",
                    row[18] or "",
                    upload_id,
                    set_request(code_headquarter, code_item, dimension_code, posting_date, quantity),
                    code_headquarter,
                    dimension_code,
                    is_dimension_sync,
                    code_item,
                    error,
                    is_valid,
                    now(),now(), "Administrator", "Administrator" 
                )
            )

        if row[0] == "EST_ADM":

            row_valid = True

    if tuple_list:
        
        return tuple_list, total, len(tuple_list)

    return [],total,0

def set_request(code_headquarter, code_item, dimension_code, posting_date, quantity):

    return json.dumps( {
            "JournalTemplateName": "INVENTARIO",
            "JournalBatchName": "INVCNS-{}".format(code_headquarter), 
            "PostingDate": posting_date,
            "EntryType": "Negative Adjmt.",
            "ItemNo": code_item, 
            "LocationCode": code_headquarter,
            "BinCode": "SF{}".format(code_headquarter),
            "Quantity": quantity,
            "ShortcutDimension1Code": "1000046632",
            "ShortcutDimension2Code": "NCIF",
            "ShortcutDimension3Code": code_headquarter,
            "ShortcutDimension4Code": dimension_code,
            "ShortcutDimension5Code": "",
            "lotNo": "",
            "GeneralBusinessPostingGroup": "NACIONAL"
        })


def get_code_headquarter(code_servinte, list_headquarter):

    code_dynamic =  [ headquarter["code"] for headquarter in list_headquarter if int(code_servinte) == int(headquarter["code_servinte"])]

    if code_dynamic:

        return code_dynamic[0],""
    
    return "", "Codigo de sede {} no encontrado\n".format(code_servinte)

def get_code_dynamic(item_servinte):
        

        items = frappe.get_list("Item", filters = {"item_code": item_servinte}, pluck = "qp_item_code_2")

        if items:
        
            return items[0], ""

        return "", "Producto {} no encontrado".format(item_servinte)

def get_dimension(identifiaction_type,identification):

    dimension = identifiaction_type+identification
        
    return dimension, True if frappe.db.exists("qp_md_Patient", {"dimension": dimension, "is_sync": True}) else False