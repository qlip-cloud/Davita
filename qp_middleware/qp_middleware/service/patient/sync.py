import frappe
import json
import requests

from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/ListadoPacientesDavita"

@frappe.whitelist()
def handler():

    response_json = get_response("list_patient")

    patient_nit = []

    for patient in response_json["value"]:

        patient["group_code"] = str(patient['tipoIdentificacion']+'-'+patient['numeroIdentificacion']).lower()

        patient_nit.append(patient["group_code"])

    result = frappe.get_list(doctype = "qp_md_Patient",  filters = {"group_code": ["in", patient_nit]}, pluck = 'group_code')

    new_patients = list(filter(lambda x: x['group_code'] not in result, response_json["value"]))
    
    values = []  

    for iter in new_patients:

        values.append((iter['group_code'], iter['tipoIdentificacion'], iter['numeroIdentificacion'],iter['primerNombre'], iter['segundoNombre'], iter['primerApellido'],
                       iter['segundoApellido'], iter['numeroTelefonico'], iter['correoElectronico'],iter['idPlan'], iter['tipoUsuario'], "Import", True, iter['group_code'], now(), 'Administrator'))

    if new_patients:

        table = "tabqp_md_Patient"

        fields = "(name, tipo_identificacion, numero_identificacion, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, numero_telefonico \
                    ,correo_electronico, id_plan, tipo_usuario,origin, is_sync, group_code,creation, owner)"
        
        persist(table, fields, values)

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(new_patients)
    }