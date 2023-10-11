// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_upload_xlsx', {
	refresh: function(frm) {
		if (!(frm.is_new())){


			frm.add_custom_button(__('Confirmar'), function(){
				if (!frm.is_dirty()){
					confirm_doc(frm, frm.doc.name)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
		}
	}
});

function confirm_doc(frm, upload_id){

	frappe.call({
		method: 'qp_middleware.qp_middleware.service.document.sync.confirm',
		args: {
			'upload_id': upload_id
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message

				if (response.status == 200) {
				
					const message = `
						<ul>
							<li> Confirmacion</li>
							<li> Total: ${response.total}</li>
							<li> Confirmados: ${response.success}</li>
							<li> No Confirmados: ${response.error}</li>
						</ul>`

					frappe.msgprint({
						message: message,
						indicator: 'green',
						title: __('Success')
					});
				}
			}
		},
		freeze:true

	});

}
