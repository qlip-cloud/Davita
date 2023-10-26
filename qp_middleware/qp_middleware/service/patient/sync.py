import frappe
import json
import requests

from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/ListadoPacientesDavita"

@frappe.whitelist()
def handler():

    response_json = get_response("list_patient")

    patient_nit = tuple([ patient["numeroIdentificacion"] for patient in response_json["value"]])

    result = frappe.get_list(doctype = "qp_md_Patient",  filters = {"numero_identificacion": ["in", patient_nit]}, pluck = 'numero_identificacion')

    new_patients = list(filter(lambda x: x["numeroIdentificacion"] not in result, response_json["value"]))
    
    values = []  

    for iter in new_patients:
        
        values.append((iter['numeroIdentificacion'], iter['tipoIdentificacion'], iter['numeroIdentificacion'],iter['primerNombre'], iter['segundoNombre'], iter['primerApellido'],
                       iter['segundoApellido'], iter['numeroTelefonico'], iter['correoElectronico'],iter['idPlan'], iter['tipoUsuario'], now(), 'Administrator'))

    if new_patients:

        table = "tabqp_md_Patient"

        fields = "(name, tipo_identificacion, numero_identificacion, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, numero_telefonico \
                    ,correo_electronico, id_plan, tipo_usuario, creation, owner)"
        
        persist(table, fields, values)

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(new_patients)
    }




    for iter in new_patients:
        
        patient = frappe.new_doc('qp_md_Patient')
        patient.tipo_identificacion = iter['tipoIdentificacion']
        patient.numero_identificacion = iter['numeroIdentificacion']
        patient.primer_nombre = iter['primerNombre']
        patient.segundo_nombre = iter['segundoNombre']
        patient.primer_apellido = iter['primerApellido']
        patient.segundo_apellido = iter['segundoApellido']
        patient.numero_telefonico = iter['numeroTelefonico']
        patient.correo_electronico = iter['correoElectronico']
        patient.id_plan = iter['idPlan']
        patient.tipo_usuario = iter['tipoUsuario']

        patient.insert()

    if new_patients:

        frappe.db.commit()

    return new_patients