from qp_middleware.qp_middleware.service.glosa.bc_sync import handler as bc_sync
from qp_middleware.qp_middleware.service.glosa.verification import handler as verification
import frappe

@frappe.whitelist()
def handler():
    
    bc_sync()
    
    verification()