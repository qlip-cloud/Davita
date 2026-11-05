import frappe

def execute():
    frappe.reload_doctype("qp_md_Consumo")
    frappe.db.add_index("qp_md_Consumo", ["upload_id"], index_name="upload_id")
