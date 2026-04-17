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
	
	def get_url_with_company_and_filters(self, endpoint, filters, select = None):

		basic = self.get_url_with_company(endpoint)
		
		concat = "?" if select or filters else ""
		
		url = f"{basic}{concat}"
  
		if select:
			concat = "&" if filters else ""
			url += f"$select={select}{concat}"
   
		if filters:
    		
			url += f"$filter={filters}"

		return url
	
	def get_url_ws_protocol(self, endpoint):

		basic = self.get_url_basic("WS")

		url = basic + "/{}/".format(self.company) + endpoint

		return url
	
	def get_url_basic(self, protocol = None):

		return self.url + "/" + self.version + "/" + self.id + "/" + self.proyect + "/" + (self.protocol if not protocol else protocol)

	def get_url(self, endpoint, filters = None, select = None):

		if endpoint.type_url == "with_company":
      
			return self.get_url_with_company(endpoint.url)
		
		if endpoint.type_url == "without_company":
      
			return self.get_url_without_company(endpoint.url)

		if endpoint.type_url == "ws_protocol":
			
			return self.get_url_ws_protocol(endpoint.url)
		
		if endpoint.type_url == "with_company_and_filters":
			
			if filters:

				return self.get_url_with_company_and_filters(endpoint.url, filters, select)

			return self.get_url_with_company(endpoint.url)

		raise Exception("Endpoint no valido")

	def get_header(self, endpoint):
		
		if endpoint.type_url == "without_company":
		
			return {
				'If-Match': '*',
				'company': self.company_code
			}
   
		if endpoint.type_url == "ws_protocol":
		
			return {
				"SOAPAction": "#POST"
			}
   
		raise Exception("Endpoint no valido")