function ajax_request(method, args, callback = null){
	frappe.call({
		method,
		args,
		callback,
		freeze:true

	});
	
}

function callback_master(retur_callback, frm){
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
			frm.reload_doc();
		}
	}
}