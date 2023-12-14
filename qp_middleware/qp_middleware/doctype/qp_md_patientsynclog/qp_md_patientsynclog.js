// Copyright (c) 2023, Rafael Licett and contributors
// For license information, please see license.txt

frappe.ui.form.on('qp_md_PatientSyncLog', {
	refresh: function(frm) {

		frm.disable_save();

		if (frm.doc.is_background == true) {
			frm.set_intro('Se esta ejecutando una tarea en segundo plano', 'yellow');
		}

	}
});
