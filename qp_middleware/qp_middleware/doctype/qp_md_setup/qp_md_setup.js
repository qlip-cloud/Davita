// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_Setup', {
	refresh: function(frm) {
		if (!(frm.is_new())){


			frm.add_custom_button(__('Clientes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_customer()
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Contratos'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_contract()
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Importar Pacientes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_patient()
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});

			frm.add_custom_button(__('Exportar Pacientes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_export_patient()
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Productos'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_item()
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			frm.add_custom_button(__('Sedes'), function(){
				if (!frm.is_dirty()){
					//sync_customer(frm, frm.doc.name)
					sync_headquarter()
				}
				else{
					show_alert (__("Unable to sync, <br> There are unsaved changes"))
				}
				
			});
			
		}
	}
});

function sync_customer(){

	let method = 'qp_middleware.qp_middleware.service.customer.sync.handler';
	send_request(method)
}

function sync_headquarter(){

	let method = 'qp_middleware.qp_middleware.service.headquarter.sync.handler';
	send_request(method)
}

function sync_contract(){

	let method = 'qp_middleware.qp_middleware.service.contract.sync.handler';
	send_request(method)
}

function sync_patient(){

	let method = 'qp_middleware.qp_middleware.service.patient.sync.handler';
	send_request(method)
}

function sync_export_patient(){

	let method = 'qp_middleware.qp_middleware.uses_cases.patient.upload_sync.handler';
	send_request(method)
}

function sync_item(){

	let method = 'qp_middleware.qp_middleware.service.item.sync.handler';
	send_request(method)
}

function send_request(method){

	frappe.call({
		method: method,
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
						</ul>`
				}
				if (response.status == 202){
					message = "Esta actividad se realizara en segundo plano"
				}

				frappe.msgprint({
					message: message,
					indicator: 'green',
					title: __('Success')
				});

			}
		},
		freeze:true

	});
}
