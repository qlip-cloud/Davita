// Copyright (c) 2026, Rafael Licett and contributors
// For license information, please see license.txt
// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_Setup', {
	refresh: function(frm) {
		if (!(frm.is_new())){


			frm.add_custom_button(__('Clientes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_customer(frm)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Contratos'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_contract(frm)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Importar Pacientes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_patient(frm)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});

			frm.add_custom_button(__('Exportar Pacientes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_export_patient(frm)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Productos'), function(){
				if (!frm.is_dirty(frm)){
					//sync_customer(frm, frm.doc.name)
					sync_item(frm)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Sedes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_headquarter(frm)
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			
		}
	}
});

function sync_customer(frm){

	let method = 'qp_middleware.qp_middleware.service.customer.sync.handler';
	send_request(method, frm)
}

function sync_headquarter(frm){

	let method = 'qp_middleware.qp_middleware.service.headquarter.sync.handler';
	send_request(method, frm)
}

function sync_contract(frm){

	let method = 'qp_middleware.qp_middleware.service.contract.sync.handler';
	send_request(method, frm)
}

function sync_patient(frm){

	let method = 'qp_middleware.qp_middleware.service.patient.sync.handler';
	send_request(method, frm)
}

function sync_export_patient(frm){

	let method = 'qp_middleware.qp_middleware.uses_cases.patient.upload_sync.handler';
	send_request(method, frm)
}

function sync_item(frm){

	let method = 'qp_middleware.qp_middleware.service.item.sync.handler';
	send_request(method, frm)
}

function send_request(method, frm){

	frappe.call({
		method: method,
		args: {
			'setup_list_code': frm.doc.name
		},
		callback: function(r) {
			if (!r.exc) {

				const response = r.message

				let message = ""

				if (response.status == 200) {
				
					message = `
						<ul>
							<li> Confirmacion</li>
							<li> Total Recibido: ${response.total}</li>
							<li> Total Confirmados: ${response.total_sync}</li>
							<li> Errores: ${"error" in response  ? response.error : 0}</li>
						</ul>`
				}
				
				if (response.status == 202){
					message = response.msg
				}

				frappe.msgprint({
					title: __('Success'),
					indicator: 'green',
					message: message
				});

			}
		},
		freeze:true

	});
}
