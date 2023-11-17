// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_upload_xlsx', {
	refresh: function(frm) {
		if (frm.doc.is_background) {
			frm.set_intro('Se esta ejecutando una tarea en segundo plano', 'yellow');
			frm.doc.is_background
		}

		if (!(frm.is_new())){

			if (!frm.doc.is_background) {
				frm.add_custom_button(__('Confirmar'), function(){
					if (!frm.is_dirty()){
						confirm_doc(frm, frm.doc.name)
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
		return `
			<ul>
				<li> Confirmacion</li>
				<li> Total: ${response.total}</li>
				<li> Confirmados: ${response.success}</li>
				<li> No Confirmados: ${response.error}</li>
			</ul>`
	}

	let callback = callback_master(return_callback)

	ajax_request(method, args,frm, callback)
}

function ajax_request(method, args, frm, callback = null){
	frappe.call({
		method,
		args,
		callback,
		freeze:true

	});
	frm.refresh()
}

function callback_master(retur_callback){
	return function(r) {
		if (!r.exc) {

			const response = r.message

			let indicator = 'green';
			let title = __('Success');
			if (response.status != 200) {

				indicator = 'red';
				title= __('Error');
			}

			let message = response.msg;

			frappe.msgprint({
				message,
				indicator,
				title
			});
		}
	}
}