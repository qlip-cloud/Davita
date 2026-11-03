# -*- coding: utf-8 -*-
"""
credit_note/sync.py
===================
Servicio para crear Notas Credito de compra en Business Central
(FacturasNCCompraWS / endpoint ``create_purchase_nc``).

Proceso aislado del flujo de facturas de compra (``purchase_invoice/sync.py``):
no modifica ``create_purchase_invoices`` ni su validacion. Reutiliza el mismo
render SOAP (``qp_md_Endpoint.soap_template``) y el mismo contrato de
respuesta por factura:

    {"Result": 0, "invoices": [{"doc_number": "...", "error": ""}, ...]}

El payload de una NC no lleva ``NoFacturaProveedor`` ni ``NoPedidoProveedor``;
lleva ``NoNotaCreditoProveedor`` (numero de la NC) y ``NoFacturaAfectada``
(numero BC de la factura de compra referenciada).
"""

import frappe

REQUIRED_CREDIT_NOTE_FIELDS = (
    "invoiceDate",
    "postingDate",
    "vendorNumber",
    "NoNotaCreditoProveedor",
    "NoFacturaAfectada",
)

REQUIRED_CREDIT_NOTE_LINE_FIELDS = (
    "NoProducto",
    "cantidad",
    "Precio",
)


def _validate_credit_note(factura, idx):
    """Valida las condiciones minimas de UNA nota credito (con su indice)."""
    errors = []

    if not isinstance(factura, dict):
        return ["Nota credito {}: debe ser un objeto".format(idx)]

    for field in REQUIRED_CREDIT_NOTE_FIELDS:
        if not factura.get(field):
            errors.append(
                "Nota credito {}: falta el campo {}".format(idx, field)
            )

    lines = factura.get("vendorInvoiceLine")
    if not isinstance(lines, list) or not lines:
        errors.append(
            "Nota credito {}: vendorInvoiceLine no puede estar vacio".format(
                idx
            )
        )
        return errors

    for line_idx, line in enumerate(lines):
        if not isinstance(line, dict):
            errors.append(
                "Nota credito {} linea {}: debe ser un objeto".format(
                    idx, line_idx
                )
            )
            continue
        for field in REQUIRED_CREDIT_NOTE_LINE_FIELDS:
            if line.get(field) in (None, ""):
                errors.append(
                    "Nota credito {} linea {}: falta el campo {}".format(
                        idx, line_idx, field
                    )
                )

    return errors


def split_credit_notes(payload):
    """Separa NC validas e invalidas conservando la posicion original.

    Una NC invalida no aborta el lote: se envia a BC solo lo valido y se
    intercala su error en la posicion original al armar los resultados.
    """
    valid = []
    invalid = {}
    for idx, factura in enumerate(payload or []):
        errors = _validate_credit_note(factura, idx)
        if errors:
            invalid[idx] = "; ".join(errors)
        else:
            valid.append(factura)
    return valid, invalid


def _send_soap(endpoint_code, payload):
    from qp_middleware.qp_middleware.service.util.sync import send_soap
    return send_soap(endpoint_code, payload)


@frappe.whitelist()
def create_credit_notes(payload, endpoint_code="create_purchase_nc"):
    """Crea un lote de notas credito en BC y devuelve un resultado por NC."""
    from qp_middleware.qp_middleware.service.purchase_invoice.sync import (
        merge_invoice_results,
        parse_purchase_invoice_response,
    )

    if not isinstance(payload, list) or not payload:
        return {
            "Result": 1,
            "Description": "El payload debe ser una lista de notas credito",
            "invoices": [],
        }

    valid_invoices, invalid_by_index = split_credit_notes(payload)

    if not valid_invoices:
        return {
            "Result": 1,
            "Description": "; ".join(invalid_by_index.values()),
            "invoices": [],
        }

    try:
        response_text, response_json, error = _send_soap(
            endpoint_code, valid_invoices
        )
    except Exception as e:
        return {
            "Result": 1,
            "Description": str(e),
            "invoices": [],
            "raw_response": "",
        }

    if error:
        return {
            "Result": 1,
            "Description": response_text or "Error en la peticion a BC",
            "invoices": [],
            "raw_response": response_text or "",
        }

    parsed = parse_purchase_invoice_response(
        response_json, response_text, len(valid_invoices)
    )
    parsed["raw_response"] = response_text or ""
    if parsed["Result"] == 1:
        return parsed

    parsed["invoices"] = merge_invoice_results(
        len(payload), invalid_by_index, parsed["invoices"]
    )
    return parsed
