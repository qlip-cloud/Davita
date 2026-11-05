from qp_middleware.qp_middleware.service.glosa.bc_sync import handler as bc_sync
from qp_middleware.qp_middleware.service.glosa.verification import handler as verification
import frappe

@frappe.whitelist()
def handler():

    frappe.enqueue(
        run,
        queue='background',
        is_async=True,
        job_name='sync_glosa',
        timeout=5400000
    )

def run():
    
    bc_sync()
    
    frappe.enqueue(
        verification,
        queue='long',
        is_async=True,
        job_name='sync_glosa_verification',
        timeout=5400000
    )