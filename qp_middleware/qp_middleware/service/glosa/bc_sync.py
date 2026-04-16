import frappe
from frappe.utils import now, get_datetime, get_datetime_str
from qp_middleware.qp_middleware.service.util.sync import get_response, persist

@frappe.whitelist()
def handler():
    
    filters = ""

    response_json = get_response("list_glosas", filters)

    sync_glosa_fast(response_json)

    move_to_glosa()
    
    move_to_glosa_line()
    
    move_to_glosa_detail()
    
    frappe.db.commit()

def sync_glosa_fast(json_data):
    
    value_list = json_data.get("value", [])
    
    if not value_list:
    
        return 0
    
    frappe.db.sql(f"DELETE FROM `tabqp_md_GlosaSync` ")

    now_date = now()
    
    rows = []
    
    for value in value_list:
        
        modified_timestamp = get_datetime(value.get("FechaModificación"))
        modified_timestamp_str = get_datetime_str(modified_timestamp)
        
        row = str((
            frappe.generate_hash(length=10),
            value.get("No", ""),
            value.get("Responsable_Cartera", ""),
            value.get("Responsable_Radicacion", ""),
            value.get("Responsable_Comercial", ""),
            value.get("Sede", ""),
            value.get("Nit", ""),
            value.get("Cliente", ""),
            value.get("Tipo_Cliente", ""),
            value.get("Regimen", ""),
            value.get("Prefijo_Factura", ""),
            value.get("Fecha_Factura", ""),
            value.get("Valor_Factura", ""),
            value.get("Fecha_Radicado_Fact", ""),
            value.get("CC_Paciente", ""),
            value.get("Nombre_Paciente", ""),
            value.get("Servicio_Facturado", ""),
            value.get("Mes_Prestacion", ""),
            value.get("Tipo_Objecion", ""),
            value.get("Fecha_Notificacion", ""),
            value.get("Valor_Glosa_Devolucion", ""),
            value.get("Numero_Resolucion", ""),
            value.get("Codigo_Glosa_Devolucion", ""),
            value.get("Causal_Glosa_Devolucion", ""),
            value.get("Descripcion", ""),
            value.get("Valor_Soportado_Contestado", ""),
            value.get("Valor_Aceptado", ""),
            value.get("Codigo_Respuesta", ""),
            value.get("Causal_Respuesta", ""),
            value.get("Respuesta", ""),
            value.get("Fecha_Respuesta_ERP", ""),
            value.get("Dias_Notif_Vs_Respuesta", ""),
            value.get("Numero_Radicado", ""),
            value.get("Valor_Nota_Credito", ""),
            value.get("Numero_Nota_Credito", ""),
            value.get("Factura_Nueva_Refacturacion", ""),
            value.get("Valor_Nueva_Factura", ""),
            value.get("Fecha_Nueva_Factura", ""),
            value.get("Valor_Conciliado", ""),
            value.get("Valor_Levantado_Conciliacion", ""),
            value.get("Valor_Aceptado_Conciliacion", ""),
            value.get("Valor_Sostenido_Conciliacion", ""),
            value.get("Numero_Acta_Conciliacion", ""),
            value.get("Fecha_Conciliacion", ""),
            value.get("Responsable_Glosa", ""),
            value.get("Usuario", ""),
            value.get("FechaRegistro", ""),
            value.get("Usuario_Modificacion", ""),
            modified_timestamp_str,
            now_date,
            now_date,
            'Administrator',
            'Administrator',
            0
        ))
        rows.append(row)
    
    values_query = ", ".join(rows)
    
    sql = f"""
        INSERT INTO `tabqp_md_GlosaSync` (
            name,
            index_number,
            portfolio_manager,
            filing_manager,
            sales_manager,
            headquarter,
            tax_id,
            customer_name,
            customer_type,
            tax_regime,
            invoice_prefix,
            invoice_date,
            invoice_amount,
            filing_date,
            patient_id,
            patient_name,
            billed_service,
            service_month,
            objection_type,
            notification_date,
            claim_amount,
            resolution_number,
            claim_code,
            claim_reason,
            description,
            supported_amount,
            accepted_amount,
            response_code,
            response_reason,
            response_details,
            erp_response_date,
            response_days_lapse,
            filing_number,
            credit_note_amount,
            credit_note_number,
            new_invoice_reference,
            new_invoice_amount,
            new_invoice_date,
            conciliated_amount,
            reinstated_amount,
            conciliation_accepted_amount,
            sustained_amount,
            conciliation_record_number,
            conciliation_date,
            claim_manager,
            entry_user,
            registration_date,
            modified_by_user,
            modified_timestamp ,
            creation,
            modified,
            modified_by,
            owner,
            docstatus
        ) VALUES 
        {values_query}"""

    frappe.db.sql(sql)

    frappe.db.commit()
    
def move_to_glosa():
    
    sql = f"""
        INSERT INTO `tabqp_md_Glosa` (
            name, 
            headquarter,
            tax_id,
            customer_name,
            customer_type,
            tax_regime,
            invoice_prefix,
            invoice_date,
            filing_date,
            patient_id,
            patient_name,
            billed_service,
            service_month,
            creation, 
            modified, 
            modified_by, 
            owner, 
            docstatus
        )
        SELECT 
            sync.invoice_prefix,
            sync.headquarter,
            sync.tax_id,
            sync.customer_name,
            sync.customer_type,
            sync.tax_regime,
            sync.invoice_prefix,
            sync.invoice_date,
            sync.filing_date,
            sync.patient_id,
            sync.patient_name,
            sync.billed_service,
            sync.service_month,
            sync.creation,
            sync.modified,
            sync.modified_by,
            sync.owner,
            0
        FROM `tabqp_md_GlosaSync` AS sync
        LEFT JOIN `tabqp_md_Glosa` AS final 
            ON sync.invoice_prefix = final.invoice_prefix
        WHERE 
            final.invoice_prefix IS NULL and sync.invoice_prefix is not null 
        group by 
            sync.headquarter,
            sync.tax_id,
            sync.customer_name,
            sync.customer_type,
            sync.tax_regime,
            sync.invoice_prefix,
            sync.invoice_date,
            sync.filing_date,
            sync.patient_id,
            sync.patient_name,
            sync.billed_service,
            sync.service_month,
            sync.creation,
            sync.modified,
            sync.modified_by,
            sync.owner
    """
    
    frappe.db.sql(sql)
    
def move_to_glosa_line():
    
    sql = f"""
        INSERT INTO `tabqp_md_GlosaLine` (
            name, 
            index_number,
            objection_type,
            notification_date,
            claim_amount,
            resolution_number,
            claim_code,
            claim_reason,
            description,
            supported_amount,
            accepted_amount,
            response_code,
            response_reason,
            response_details,
            erp_response_date,
            response_days_lapse,
            filing_number,
            credit_note_amount,
            credit_note_number,
            new_invoice_reference,
            new_invoice_amount,
            new_invoice_date,
            conciliated_amount,
            reinstated_amount,
            conciliation_accepted_amount,
            sustained_amount,
            conciliation_record_number,
            conciliation_date,
            claim_manager,
            entry_user,
            registration_date,
            modified_by_user,
            modified_timestamp,
            parent,
            parentfield,
            parenttype,
            creation, 
            modified, 
            modified_by, 
            owner
        )
        SELECT 
            sync.name,
            sync.index_number,
            sync.objection_type,
            sync.notification_date,
            sync.claim_amount,
            sync.resolution_number,
            sync.claim_code,
            sync.claim_reason,
            sync.description,
            sync.supported_amount,
            sync.accepted_amount,
            sync.response_code,
            sync.response_reason,
            sync.response_details,
            sync.erp_response_date,
            sync.response_days_lapse,
            sync.filing_number,
            sync.credit_note_amount,
            sync.credit_note_number,
            sync.new_invoice_reference,
            sync.new_invoice_amount,
            sync.new_invoice_date,
            sync.conciliated_amount,
            sync.reinstated_amount,
            sync.conciliation_accepted_amount,
            sync.sustained_amount,
            sync.conciliation_record_number,
            sync.conciliation_date,
            sync.claim_manager,
            sync.entry_user,
            sync.registration_date,
            sync.modified_by_user,
            sync.modified_timestamp ,
            sync.invoice_prefix,
            'glosas' as parentfield,
            'qp_md_Glosa' as parenttype,
            sync.creation,
            sync.modified,
            sync.modified_by,
            sync.owner
        FROM `tabqp_md_GlosaSync` AS sync
        
        LEFT JOIN `tabqp_md_GlosaLine` AS final ON sync.index_number = final.index_number
        WHERE final.index_number IS NULL
        order by sync.index_number asc
        
    """
    
    frappe.db.sql(sql)
    
def move_to_glosa_detail():
    
    sql = f"""
        INSERT INTO `tabqp_md_GlosaDetail` (
            name, 
            index_number,
            portfolio_manager,
            filing_manager,
            sales_manager,
            invoice_amount,
            parent,
            parentfield,
            parenttype,
            creation, 
            modified, 
            modified_by, 
            owner
        )
        SELECT 
            sync.name,
            sync.index_number,
            sync.portfolio_manager,
            sync.filing_manager,
            sync.sales_manager,
            sync.invoice_amount,
            sync.invoice_prefix,
            'details' as parentfield,
            'qp_md_Glosa' as parenttype,
            sync.creation,
            sync.modified,
            sync.modified_by,
            sync.owner
        FROM `tabqp_md_GlosaSync` AS sync
        LEFT JOIN `tabqp_md_GlosaDetail` AS final ON sync.index_number = final.index_number
        WHERE final.index_number IS NULL
        order by sync.index_number asc
    """
    
    frappe.db.sql(sql)