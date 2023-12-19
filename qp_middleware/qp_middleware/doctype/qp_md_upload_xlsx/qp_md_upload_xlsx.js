// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_upload_xlsx', {
	refresh: function(frm) {
		if (frm.doc.is_background) {
			frm.set_intro('Se esta ejecutando una tarea en segundo plano', 'yellow');
		}
		if (frm.doc.error) {
			frm.set_intro('Error al procesar el excel', 'red');
		}
		if (!(frm.is_new())){

			if (!frm.doc.is_background) {
				frm.add_custom_button(__('Confirmar'), function(){
					if (!frm.is_dirty()){
						confirm_doc(frm, frm.doc.name)
						frm.refresh()
					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}
					
				});
			}
			frm.add_custom_button(__('Descargar'), function(){
				if (!frm.is_dirty()){
					download_doc(frm, frm.doc.name)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
		}
	}
});

function download_doc(frm, upload_id){
	
	
	
	let method = `/api/method/qp_middleware.qp_middleware.service.invoice_sync.export.xlsx.handler?upload_id=${upload_id}`;
	window.open(method, '_blank');
	
}

function confirm_doc(frm, upload_id){
	
	let method = 'qp_middleware.qp_middleware.service.document.confirm.handler'
	let args = {
		'upload_id': upload_id
	}

	let return_callback = (response)=>{
		frm.refresh()

	}

	let callback = callback_master(return_callback, frm)

	ajax_request(method, args, callback)
}