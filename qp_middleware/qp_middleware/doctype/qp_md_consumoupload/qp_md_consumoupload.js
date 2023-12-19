// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_ConsumoUpload', {
	refresh: function(frm) {

		if (frm.doc.is_error_sync) {
			frm.set_intro('Error al procesar el excel', 'red');
		}
		if (true){

			if (true) {
				frm.add_custom_button(__('Sincronizar'), function(){
					if (!frm.is_dirty()){
						consumo_sync(frm, frm.doc.name)
						frm.refresh()
					}
					else{
						show_alert (__("Unable to sync, <br> There are unsaved changes"))
					}
					
				});
			}
			else{
				frm.set_intro('Se esta ejecutando una tarea en segundo plano', 'yellow');

			}
			/*frm.add_custom_button(__('Descargar'), function(){
				if (!frm.is_dirty()){
					download_doc(frm, frm.doc.name)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});*/
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