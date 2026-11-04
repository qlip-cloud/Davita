# -*- coding: utf-8 -*-
"""
test_credit_note_sync.py
========================
Pruebas del servicio aislado de Notas Credito BC
(service/purchase_invoice/credit_note.py).

Frappe se inyecta como mock (sin base de datos). El envio SOAP se reemplaza
por un double para probar validacion y el contrato de respuesta por NC.

Ejecutar con (desde apps/qp_middleware):
  python -m unittest qp_middleware.qp_middleware.tests.test_credit_note_sync -v
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules["frappe"] = MagicMock()
sys.modules["frappe.utils"] = MagicMock()
sys.modules["frappe.model"] = MagicMock()
sys.modules["frappe.model.document"] = MagicMock()
# El decorador @frappe.whitelist debe devolver la funcion sin envolver.
sys.modules["frappe"].whitelist = lambda *args, **kwargs: (lambda fn: fn)

from qp_middleware.qp_middleware.service.purchase_invoice.credit_note import (  # noqa: E402
    _validate_credit_note,
    create_credit_notes,
    split_credit_notes,
)


def _nc(**overrides):
    nc = {
        "DocumentType": "Credit Memo",
        "invoiceDate": "2026-10-28",
        "postingDate": "2026-10-28",
        "vendorNumber": "900162414",
        "puntofacturacion": "",
        "NoFacturaProveedor": "EjemploYD",
        "tipoFacturaDoc": "",
        "Categoria": "",
        "SubCategoria": "",
        "Cufe": "",
        "Almacen": "",
        "formaPago": "",
        "NoFacturaAfectada": "FC70065",
        "dimensionSetLines": [
            {"code": "TERCERO", "valueCode": "900162414"}
        ],
        "vendorInvoiceLine": [{
            "NoProducto": "OP0080",
            "cantidad": 1,
            "Precio": 200000.0,
            "Type": "Item",
            "Comentarios": "",
        }],
    }
    nc.update(overrides)
    return nc


class TestValidateCreditNote(unittest.TestCase):

    def test_nc_valida(self):
        self.assertEqual(_validate_credit_note(_nc(), 0), [])

    def test_falta_factura_afectada(self):
        errors = _validate_credit_note(_nc(NoFacturaAfectada=""), 0)
        self.assertTrue(any("NoFacturaAfectada" in e for e in errors))

    def test_falta_numero_factura(self):
        errors = _validate_credit_note(_nc(NoFacturaProveedor=""), 0)
        self.assertTrue(any("NoFacturaProveedor" in e for e in errors))

    def test_document_type_invalido(self):
        errors = _validate_credit_note(_nc(DocumentType="Invoice"), 0)
        self.assertTrue(any("DocumentType" in e for e in errors))

    def test_sin_lineas(self):
        errors = _validate_credit_note(_nc(vendorInvoiceLine=[]), 0)
        self.assertTrue(any("vendorInvoiceLine" in e for e in errors))


class TestSplitCreditNotes(unittest.TestCase):

    def test_separa_validas_e_invalidas_conservando_posicion(self):
        valid, invalid = split_credit_notes([
            _nc(),
            _nc(NoFacturaAfectada=""),
            _nc(NoFacturaProveedor="NC-2"),
        ])
        self.assertEqual(len(valid), 2)
        self.assertEqual(list(invalid), [1])


class TestCreateCreditNotes(unittest.TestCase):

    @patch(
        "qp_middleware.qp_middleware.service.purchase_invoice.credit_note."
        "_send_soap"
    )
    def test_respuesta_por_nc(self, send_soap):
        send_soap.return_value = (
            "<xml/>",
            {"Envelope": {"Body": {"FacturasNCCompraWS_Result": {
                "return_value": "NC-BC-1;"
            }}}},
            False,
        )
        result = create_credit_notes([_nc()])
        self.assertEqual(result["Result"], 0)
        self.assertEqual(result["invoices"][0]["doc_number"], "NC-BC-1")
        self.assertEqual(result["invoices"][0]["error"], "")

    @patch(
        "qp_middleware.qp_middleware.service.purchase_invoice.credit_note."
        "_send_soap"
    )
    def test_nc_invalida_no_bloquea_el_lote(self, send_soap):
        send_soap.return_value = (
            "<xml/>",
            {"Envelope": {"Body": {"FacturasNCCompraWS_Result": {
                "return_value": "NC-BC-1;"
            }}}},
            False,
        )
        result = create_credit_notes([
            _nc(NoFacturaAfectada=""),
            _nc(NoFacturaProveedor="NC-2"),
        ])
        self.assertEqual(result["Result"], 0)
        self.assertEqual(len(send_soap.call_args[0][1]), 1)
        self.assertEqual(result["invoices"][0]["doc_number"], "")
        self.assertIn("NoFacturaAfectada", result["invoices"][0]["error"])
        self.assertEqual(result["invoices"][1]["doc_number"], "NC-BC-1")

    def test_payload_vacio(self):
        result = create_credit_notes([])
        self.assertEqual(result["Result"], 1)


if __name__ == "__main__":
    unittest.main()
