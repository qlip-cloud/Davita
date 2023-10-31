import frappe
from frappe.utils.xlsxutils import build_xlsx_response

@frappe.whitelist()
def handler(upload_id):

    rows = get_data(upload_id)

    data = [
        get_header(),
        *rows
    ]

    build_xlsx_response(data, "Upload xlsx {}".format(upload_id))

def get_data(upload_id):

    sql = """
        SELECT
            document.document_code,
            invoice_sync.proveedor,
            invoice_sync.numero,
            invoice_sync.sede_de_origne,
            invoice_sync.transitorio,
            invoice_sync.responsable,
            invoice_sync.unidad_renal,
            invoice_sync.eps,
            invoice_sync.tipo_documento,
            invoice_sync.no_identificacion,
            invoice_sync.nombre_paciente,
            invoice_sync.primer_apellido_del_paciente,
            invoice_sync.segundo_apellido__del_paciente,
            invoice_sync.nombre_tercero,
            invoice_sync.segundo_nombre,
            invoice_sync.id_unico_ingreso_fuente_no_cargo,
            invoice_sync.genero,
            invoice_sync.edad,
            invoice_sync.tipo_de_servicio,
            invoice_sync.cantidad_a_facturar,
            invoice_sync.facturable,
            invoice_sync.no_factura,
            invoice_sync.valor,
            invoice_sync.cuota_moderadora,
            invoice_sync.autorizacion_final,
            invoice_sync.cod_empresa,
            invoice_sync.codigo_admon,
            invoice_sync.regimen,
            invoice_sync.rips,
            invoice_sync.fecha_de_servicio,
            invoice_sync.meses_anteriores__referencia_cateter,
            invoice_sync.observaciones,
            invoice_sync.empty_1,
            invoice_sync.sede_servinte,
            invoice_sync.eps_servinte,
            invoice_sync.tipo_servicio_servinte,
            invoice_sync.cantidad_servinte,
            invoice_sync.cantidad_corregida,
            invoice_sync.nit,
            invoice_sync.rango_de,
            invoice_sync.rango_hasta,
            invoice_sync.paquete_o_sesion,
            invoice_sync.vr_a_facturar,
            invoice_sync.diferencias,
            invoice_sync.nombre_eps,
            invoice_sync.tipo_servicio,
            invoice_sync.cant_censo,
            invoice_sync.codigo_centro_de_costo,
            invoice_sync.nombre_centro_de_costo,
            invoice_sync.admision_sin_admision,
            invoice_sync.concepto_facturacion,
            invoice_sync.nombre_concepto,
            invoice_sync.codigo_procedimiento_facturacion,
            invoice_sync.nombre_codigo_descripcion,
            invoice_sync.empty_2,
            invoice_sync.sede_fuente_cargo,
            invoice_sync.aut_formula,
            invoice_sync.estado,
            invoice_sync.eps_resumida_aut,
            invoice_sync.no_autorizacion_posterior_al_guion,
            invoice_sync.largo,
            invoice_sync.autorizacion_con_letras,
            invoice_sync.longitud_aut,
            invoice_sync.autorizacion_diferente_a_la_cedula,
            invoice_sync.autorizacion_no_duplicada,
            invoice_sync.auto_iguales,
            invoice_sync.empty_3,
            invoice_sync.consecutivo,
            invoice_sync.empty_4,
            invoice_sync.vr_paquete_en_cargos_por_usuario,
            invoice_sync.vr_paquete_facturacion,
            invoice_sync.vs,
            invoice_sync.observaciones_1
            
        FROM
            tabqp_md_invoice_sync  as invoice_sync
        inner join
            tabqp_md_Document as document
            ON(
                document.group_code = invoice_sync.group_code and
                document.upload_id = invoice_sync.upload_id)
        where
            invoice_sync.upload_id = '{upload_id}'
    """.format(upload_id = upload_id)

    response = frappe.db.sql(sql)

    print(response)

    return response

def get_header():

    return [   
            "Codigo documento",
            "",
            "",
            "SEDE DE ORIGNE",
            "TRANSITORIO",
            "RESPONSABLE",
            "UNIDAD RENAL (DONDE SE REALIZO EL CARGO)",
            "EPS",
            "TIPO DOCUMENTO",
            "NO. IDENTIFICACION",
            "Nombre paciente",
            "Primer apellido del paciente",
            "Segundo apellido  del paciente",
            "Nombre Tercero",
            "Segundo Nombre",
            "ID UNICO + INGRESO / FUENTE + NO. CARGO",
            "GENERO",
            "edad",
            "9 - TIPO DE SERVICIO",
            "CANTIDAD A FACTURAR",
            "FACTURABLE",
            "# FACTURA",
            "VALOR",
            "CUOTA MODERADORA",
            "AUTORIZACION FINAL",
            "COD EMPRESA",
            "CODIGO ADMON",
            "REGIMEN",
            "RIPS",
            "FECHA DE SERVICIO",
            "MESES ANTERIORES / REFERENCIA CATETER",
            "OBSERVACIONES",
            "",
            "SEDE SERVINTE",
            "EPS SERVINTE",
            "9 - TIPO DE SERVICIO SERVINTE",
            "CANTIDAD SERVINTE",
            "CANTIDAD CORREGIDA",
            "NIT",
            "RANGO DE",
            "RANGO HASTA",
            "PAQUETE O SESION",
            "VR A FACTURAR",
            "DIFERENCIAS",
            "NOMBRE EPS",
            "TIPO SERVICIO",
            "CANT CENSO",
            "CODIGO CENTRO DE COSTO",
            "NOMBRE CENTRO DE COSTO",
            "ADMISION / SIN ADMISION",
            "CONCEPTO FACTURACION",
            "NOMBRE CONCEPTO",
            "CODIGO PROCEDIMIENTO FACTURACION",
            "NOMBRE CODIGO DESCRIPCION",
            "",
            "SEDE + FUENTE Y CARGO",
            "AUT (FORMULA",
            "ESTADO",
            "EPS RESUMIDA AUT",
            "No. Autorización posterior al Guion",
            "largo",
            "AUTORIZACION CON LETRAS",
            "LONGITUD AUT",
            "AUTORIZACION DIFERENTE A LA CEDULA",
            "AUTORIZACION NO DUPLICADA",
            "AUTO IGUALES?",
            "",
            "consecutivo",
            "",
            "VR PAQUETE EN CARGOS POR USUARIO",
            "VR PAQUETE FACTURACION",
            "VS",
            "observaciones",
        ]


    
