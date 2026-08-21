# -*- coding: utf-8 -*-
"""
test_purchase_invoice_sync.py
=============================
Pruebas unitarias para service/purchase_invoice/sync.py y el render del
template SOAP (service/util/sync.py).

Frappe se inyecta en sys.modules como mock (sin base de datos).
Ejecutar con (desde apps/qp_middleware):
  python -m unittest qp_middleware.qp_middleware.tests.test_purchase_invoice_sync -v
"""
import sys
import unittest
from unittest.mock import MagicMock

sys.modules["frappe"] = MagicMock()
sys.modules["frappe.utils"] = MagicMock()
sys.modules["frappe.model"] = MagicMock()
sys.modules["frappe.model.document"] = MagicMock()

from qp_middleware.qp_middleware.service.purchase_invoice.sync import (  # noqa: E402
    _search_key,
    parse_purchase_invoice_response,
    validate_purchase_invoice_payload,
)
from qp_middleware.qp_middleware.service.util.sync import (  # noqa: E402
    render_soap_payload,
)


def _result_element(return_value):
    return {
        "Soap:Envelope": {
            "Soap:Body": {
                "FacturasCompraWS_Result": {
                    "return_value": return_value,
                }
            }
        }
    }


class TestValidatePurchaseInvoicePayload(unittest.TestCase):

    def _factura(self, **overrides):
        factura = {
            "invoiceDate": "2026-07-09",
            "postingDate": "2026-07-09",
            "vendorNumber": "050633410",
            "NoFacturaProveedor": "YD0907202121126562",
            "vendorInvoiceLine": [
                {"NoProducto": "M000455", "cantidad": 10, "Precio": 5000.0,
                 "NoLineaRecepcion": "20000", "NoRecepcion": "R108349",
                 "NoPedido": "45238"},
            ],
        }
        factura.update(overrides)
        return factura

    def test_payload_valido(self):
        self.assertEqual(validate_purchase_invoice_payload([self._factura()]), [])

    def test_no_es_lista(self):
        self.assertNotEqual(validate_purchase_invoice_payload({}), [])

    def test_lista_vacia(self):
        self.assertNotEqual(validate_purchase_invoice_payload([]), [])

    def test_falta_campo_de_factura(self):
        errors = validate_purchase_invoice_payload([
            self._factura(NoFacturaProveedor="")
        ])
        self.assertEqual(len(errors), 1)
        self.assertIn("NoFacturaProveedor", errors[0])

    def test_sin_lineas(self):
        errors = validate_purchase_invoice_payload([
            self._factura(vendorInvoiceLine=[])
        ])
        self.assertEqual(len(errors), 1)
        self.assertIn("vendorInvoiceLine", errors[0])

    def test_falta_campo_de_linea(self):
        errors = validate_purchase_invoice_payload([
            self._factura(vendorInvoiceLine=[{"NoProducto": "M000455"}])
        ])
        self.assertIn("cantidad", ";".join(errors))

    def test_falta_campo_en_otra_factura(self):
        errors = validate_purchase_invoice_payload([
            self._factura(),
            self._factura(vendorNumber=""),
        ])
        self.assertEqual(len(errors), 1)


class TestSearchKey(unittest.TestCase):

    def test_encuentra_llave_con_prefijo(self):
        node = {"s:Envelope": {"s:Body": {"s:Fault": {"faultstring": "boom"}}}}
        self.assertEqual(_search_key(node, "faultstring"), "boom")

    def test_encuentra_return_value_anidado(self):
        node = _result_element("0025548;")
        self.assertEqual(_search_key(node, "return_value"), "0025548;")

    def test_encuentra_fault(self):
        node = {"s:Envelope": {"s:Body": {"s:Fault": "x"}}}
        self.assertEqual(_search_key(node, "Fault"), "x")

    def test_no_encuentra_retorna_none(self):
        self.assertIsNone(_search_key({"a": {"b": 1}}, "return_value"))


class TestParsePurchaseInvoiceResponse(unittest.TestCase):

    def test_exito(self):
        result = parse_purchase_invoice_response(
            _result_element("0025548;"), "<resp>", 1
        )
        self.assertEqual(result["Result"], 0)
        self.assertEqual(result["invoices"], [{"doc_number": "0025548", "error": ""}])

    def test_ya_existe(self):
        result = parse_purchase_invoice_response(
            _result_element("Error Ya existe la factura de compra YD0907202121126562 para este proveedor.;"),
            "<resp>", 1,
        )
        self.assertEqual(result["Result"], 0)
        self.assertEqual(result["invoices"][0]["doc_number"], "")
        self.assertIn("Ya existe", result["invoices"][0]["error"])

    def test_mixta_error_y_ok(self):
        result = parse_purchase_invoice_response(
            _result_element("Error Ya existe la factura de compra YD0907202121126562 para este proveedor.;0025558;"),
            "<resp>", 2,
        )
        self.assertEqual(result["Result"], 0)
        self.assertEqual(result["invoices"], [
            {"doc_number": "", "error": "Error Ya existe la factura de compra YD0907202121126562 para este proveedor."},
            {"doc_number": "0025558", "error": ""},
        ])

    def test_mixta_vacio_y_ok(self):
        result = parse_purchase_invoice_response(
            _result_element(";0025560;"), "<resp>", 2
        )
        self.assertEqual(result["Result"], 0)
        self.assertEqual(result["invoices"][0]["doc_number"], "")
        self.assertIn("no devolvio", result["invoices"][0]["error"])
        self.assertEqual(result["invoices"][1]["doc_number"], "0025560")

    def test_proveedor_inexistente(self):
        result = parse_purchase_invoice_response(_result_element(";"), "<resp>", 1)
        self.assertEqual(result["Result"], 0)
        self.assertEqual(result["invoices"][0]["doc_number"], "")
        self.assertNotEqual(result["invoices"][0]["error"], "")

    def test_error_formato_campo(self):
        result = parse_purchase_invoice_response(
            _result_element("Error Posting Date must have a value in Purchase Header: Document Type=Invoice, No.=0025550. It cannot be zero or empty.;"),
            "<resp>", 1,
        )
        self.assertEqual(result["invoices"][0]["doc_number"], "")
        self.assertIn("Posting Date", result["invoices"][0]["error"])

    def test_fault_campo_faltante_global(self):
        response_json = {
            "s:Envelope": {
                "s:Body": {
                    "s:Fault": {
                        "faultcode": "a:NavNCLJsonPropertyNotFoundException",
                        "faultstring": "There is no property with the 'NoFacturaProveedor' key on the JSON object.",
                        "detail": {"string": "There is no property with the 'NoFacturaProveedor' key on the JSON object."},
                    }
                }
            }
        }
        result = parse_purchase_invoice_response(response_json, "<resp>", 2)
        self.assertEqual(result["Result"], 1)
        self.assertEqual(result["invoices"], [])
        self.assertIn("NoFacturaProveedor", result["Description"])

    def test_fault_con_factura_valida_igualmente_global(self):
        response_json = {
            "s:Envelope": {
                "s:Body": {
                    "s:Fault": {"faultstring": "boom"}
                }
            }
        }
        result = parse_purchase_invoice_response(response_json, "<resp>", 2)
        self.assertEqual(result["Result"], 1)
        self.assertEqual(result["invoices"], [])

    def test_respuesta_no_dict(self):
        result = parse_purchase_invoice_response(None, "texto", 1)
        self.assertEqual(result["Result"], 1)

    def test_sin_return_value(self):
        result = parse_purchase_invoice_response(
            {"Soap:Envelope": {"Soap:Body": {}}}, "<resp>", 1
        )
        self.assertEqual(result["Result"], 1)

    def test_menos_resultados_que_facturas(self):
        result = parse_purchase_invoice_response(
            _result_element("0025548;"), "<resp>", 3
        )
        self.assertEqual(result["invoices"][0]["doc_number"], "0025548")
        self.assertEqual(result["invoices"][1]["doc_number"], "")
        self.assertEqual(result["invoices"][2]["doc_number"], "")


class TestRenderSoapPayload(unittest.TestCase):

    TEMPLATE = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:nav="urn:x">'
        '<soap:Body><nav:FacturasCompraWS><nav:factura>__PAYLOAD__</nav:factura>'
        '</nav:FacturasCompraWS></soap:Body></soap:Envelope>'
    )

    def test_reemplaza_placeholder_con_json(self):
        rendered = render_soap_payload(self.TEMPLATE, [{"NoFacturaProveedor": "X"}])
        self.assertIn('"NoFacturaProveedor": "X"', rendered)
        self.assertNotIn("__PAYLOAD__", rendered)

    def test_strip_single_quotes_activo(self):
        rendered = render_soap_payload(self.TEMPLATE, [{"desc": "L'electricite"}])
        self.assertIn("Lelectricite", rendered)

    def test_strip_single_quotes_inactivo(self):
        rendered = render_soap_payload(
            self.TEMPLATE, [{"desc": "L'electricite"}], strip_single_quotes=False
        )
        self.assertIn("L'electricite", rendered)

    def test_template_escapado_se_unescape_a_xml_plano(self):
        escaped = (
            '&lt;?xml version=&quot;1.0&quot; encoding=&quot;utf-8&quot;?&gt;'
            '&lt;soap:Envelope xmlns:nav=&quot;urn:x&quot;&gt;'
            '&lt;nav:factura&gt;__PAYLOAD__&lt;/nav:factura&gt;'
            '&lt;/soap:Envelope&gt;'
        )
        rendered = render_soap_payload(escaped, [{"NoFacturaProveedor": "X"}])
        self.assertNotIn("&lt;", rendered)
        self.assertNotIn("&gt;", rendered)
        self.assertIn("<nav:factura>", rendered)
        self.assertIn('"NoFacturaProveedor": "X"', rendered)


if __name__ == "__main__":
    unittest.main()
