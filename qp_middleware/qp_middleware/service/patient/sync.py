import frappe
import json
import requests

from frappe.utils import now
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

#URL = "https://api.businesscentral.dynamics.com/v2.0/a1af66a5-d7b4-43a1-9663-3f02fecf8060/MIDDLEWARE/ODataV4/Company(%27DAVITA%27)/ListadoPacientesDavita"

@frappe.whitelist()
def handler():

    response_json = get_response("list_patient")

    values = []

    tipos_identificaciones = frappe.get_list("qp_md_TipoIdentificacion", fields = ["description", "code"])

    format_tipos_Identificaciones = {}

    for tipo_identificaciones  in tipos_identificaciones:

        format_tipos_Identificaciones.update({tipo_identificaciones.get("description"): tipo_identificaciones.get("code")})
    
    list_group_code = frappe.db.get_list('qp_md_Patient', pluck='group_code')


    error_group = []

    for iter in response_json["value"]:

        tipo_identificacion = format_tipos_Identificaciones.get(iter['tipoIdentificacion'])
        
        if tipo_identificacion:
            

            dimension = str(tipo_identificacion + str(iter.get("numeroIdentificacion"))).upper()
                
            group_code = str(dimension + '_' + iter['tipoUsuario'][0]).upper()
            
            if not group_code in list_group_code:

                values.append((group_code, tipo_identificacion, iter['tipoIdentificacion'], iter['numeroIdentificacion'],iter['primerNombre'], iter['segundoNombre'], iter['primerApellido'],
                        iter['segundoApellido'], iter['numeroTelefonico'], iter['correoElectronico'],iter['idPlan'], iter['tipoUsuario'][0], iter['tipoUsuario'], "Import", True, group_code, dimension, now(), now(), 'Administrator', 'Administrator'))
        
        else:

            error_group.append(iter['tipoIdentificacion'])


    if values:

        table = "tabqp_md_Patient"

        fields = "(name, tipo_identificacion, nombre_identificacion, numero_identificacion, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, numero_telefonico \
                    ,correo_electronico, id_plan, tipo_usuario, nombre_usuario,origin, is_sync, group_code, dimension, creation, modified, modified_by, owner)"
        
        persist(table, fields, values)

    if error_group:

        error_group = list(set(error_group))

        error = "Estos tipos de identificacion no esta configurado: {}".format(str(error_group).replace("[", "").replace("]", ""))

    return {
        "status": 200,
        "total": len(response_json["value"]),
        "total_sync": len(values),
        "error": error if error_group else ""
    }