import frappe
import time
from frappe.utils import now_datetime

@frappe.whitelist()
def enqueue_job():
    user = frappe.session.user
    job_id = frappe.generate_hash(length=8)
    
    # Encolar la tarea en segundo plano en la cola 'short'
    frappe.enqueue(
        method="qp_middleware.qp_middleware.service.util.test_concurrency.execute_sleep",
        queue='short',
        is_async=True,
        job_name=f"test_concurrency_{job_id}",
        user=user,
        job_id=job_id
    )
    
    return {
        "status": 202,
        "message": "Petición recibida. El trabajo se ejecutará en segundo plano.",
        "user": user,
        "job_id": job_id
    }

def execute_sleep(user, job_id):
    start_time = now_datetime()
    frappe.log_error(
        message=f"Inicio del Job {job_id} solicitado por el usuario '{user}' a las {start_time}",
        title="Test Concurrency Start"
    )
    
    # Simular un trabajo largo con un sleep de un minuto
    time.sleep(60)
    
    end_time = now_datetime()
    frappe.log_error(
        message=f"Fin del Job {job_id} solicitado por el usuario '{user}'. Inicio: {start_time}, Fin: {end_time}",
        title="Test Concurrency End"
    )
