# Copyright (c) 2023, Rafael Licett and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class qp_md_Enviroment(Document):
	

	def get_url_with_company(self, endpoint):

		basic = self.get_url_basic()

		url = basic + "/Company('{}')".format(self.company) + "/" + endpoint

		return url
	
	def get_url_without_company(self, endpoint):

		basic = self.get_url_basic()

		url = basic + "/" + endpoint

		return url
	
	def get_url_with_company_and_filters(self, endpoint, filters):

		basic = self.get_url_with_company(endpoint)

		url = basic + "?$filter=" + filters

		return url
	
	def get_url_ws_protocol(self, endpoint):

		basic = self.get_url_basic("WS")

		url = basic + "/{}/".format(self.company) + endpoint

		return url
	
	def get_url_basic(self, protocol = None):

		return self.url + "/" + self.version + "/" + self.id + "/" + self.proyect + "/" + (self.protocol if not protocol else protocol)