import frappe
import json
import requests

from qp_authorization.use_case.oauth2.authorize import get_token

URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/ListadoPacientesDavita"

payload = ""

@frappe.whitelist()
def handler():
    
    token = get_token()
    
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    response = requests.get(URL, headers=headers, data=payload)

    response_json = json.loads(response.text)

    patient_nit = tuple([ patient["numeroIdentificacion"] for patient in response_json["value"]])

    result = frappe.get_list(doctype = "qp_md_Patient",  filters = {"numero_identificacion": ["in", patient_nit]}, pluck = 'numero_identificacion')

    new_patients = list(filter(lambda x: x["numeroIdentificacion"] not in result, response_json["value"]))
    
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