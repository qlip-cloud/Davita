// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_ConsumoUpload', {
	refresh: function(frm) {
		if (frm.doc.is_background){
			frm.set_intro('Se esta ejecutando una tarea en segundo plano', 'yellow');
		}
		if (frm.doc.is_error_sync) {
			frm.set_intro('Error al procesar el excel', 'red');
		}

		
		if (!(frm.is_new())){
			if (!frm.doc.start_date || frm.doc.is_error_connection || frm.doc.is_error_sync) {
				frm.add_custom_button(__('Sincronizar'), function(){
					if (!frm.is_dirty()){
						frappe.confirm(__('Seguro desea volver a sincronizar los consumos?'),
						function() {
							consumo_sync(frm, frm.doc.name)
							frm.refresh()
						}
						);
					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}
					
				});

				
			}
			if (frappe.user.has_role(['Devoluciones', 'Administrator'])) {
				frm.add_custom_button(__('Devolver'), function(){

					frappe.confirm(__('Seguro desea devolver los consumos?'),
					function() {
							consumo_return(frm, frm.doc.name)
							frm.refresh()
							}
					);						
					
				});
			}		
		}
	}
});

function consumo_sync(frm, upload_id){
	
	let method = 'qp_middleware.qp_middleware.uses_cases.consumo.sync.handler'
	let args = {
		'upload_id': upload_id
	}

	let return_callback = (response)=>{

		frm.refresh()

	}

	let callback = callback_master(return_callback, frm)

	ajax_request(method, args, callback)
}

function consumo_return(frm, upload_id){
	
	let method = 'qp_middleware.qp_middleware.uses_cases.consumo.return.handler'
	let args = {
		'upload_id': upload_id
	}

	let return_callback = (response)=>{
		frm.refresh()

	}

	let callback = callback_master(return_callback, frm)

	ajax_request(method, args, callback)
}