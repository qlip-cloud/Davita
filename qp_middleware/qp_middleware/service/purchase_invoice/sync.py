"""
purchase_invoice/sync.py
========================
Servicio para crear facturas de compra en BC (FacturasCompraWS).

El servicio:
1. Valida que el payload cumpla las condiciones minimas para enviar a BC
   (campos requeridos por factura) y devuelve errores limpios sin llamar a BC.
2. Arma el SOAP con el template configurado en qp_md_Endpoint.soap_template
   y lo envia via send_soap.
3. Parsea la respuesta SOAP, que devuelve un resultado por factura separado
   por ';' en el mismo orden del payload.

Formas de respuesta reales de FacturasCompraWS:
- Exito:                  return_value = "0025548;"
- Ya existe:              return_value = "Error Ya existe la factura...;"
- Proveedor inexistente:  return_value = ";"
- Mixta (error + ok):     return_value = "Error Ya existe...;0025558;"
- Mixta (vacio + ok):     return_value = ";0025560;"
- Campo faltante:         SOAP Fault (s:Envelope/s:Body/s:Fault) global.
"""

import frappe


def _send_soap(endpoint_code, payload):
    from qp_middleware.qp_middleware.service.util.sync import send_soap
    return send_soap(endpoint_code, payload)


REQUIRED_INVOICE_FIELDS = (
    "invoiceDate",
    "postingDate",
    "vendorNumber",
    "NoFacturaProveedor",
)

REQUIRED_LINE_FIELDS = (
    "NoProducto",
    "cantidad",
    "Precio",
    "NoPedido",
    "NoRecepcion",
)


def validate_purchase_invoice_payload(payload):
    """Valida las condiciones minimas para enviar a BC.

    Retorna una lista de errores (vacia si el payload es valido).
    """
    errors = []

    if not isinstance(payload, list) or not payload:
        return ["El payload debe ser una lista de facturas"]

    for idx, factura in enumerate(payload):
        if not isinstance(factura, dict):
            errors.append("Factura {}: debe ser un objeto".format(idx))
            continue

        for field in REQUIRED_INVOICE_FIELDS:
            if not factura.get(field):
                errors.append(
                    "Factura {}: falta el campo {}".format(idx, field)
                )

        lines = factura.get("vendorInvoiceLine")
        if not isinstance(lines, list) or not lines:
            errors.append(
                "Factura {}: vendorInvoiceLine no puede estar vacio".format(idx)
            )
            continue

        for line_idx, line in enumerate(lines):
            if not isinstance(line, dict):
                errors.append(
                    "Factura {} linea {}: debe ser un objeto".format(idx, line_idx)
                )
                continue
            for field in REQUIRED_LINE_FIELDS:
                if line.get(field) in (None, ""):
                    errors.append(
                        "Factura {} linea {}: falta el campo {}".format(
                            idx, line_idx, field
                        )
                    )

    return errors


def _search_key(node, key):
    """Busca recursivamente una llave cuyo nombre contenga `key`.

    Es tolerante a prefijos de namespace (s:, Soap:, soap:).
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if key.lower() in k.lower():
                return v
            found = _search_key(v, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _search_key(item, key)
            if found is not None:
                return found
    return None


def parse_purchase_invoice_response(response_json, response_text, num_invoices):
    """Convierte la respuesta SOAP en resultados por factura.

    Retorna {"Result": 0, "invoices": [...]} para resultados por factura o
    {"Result": 1, "Description": ..., "invoices": []} para errores globales
    (Fault, respuesta invalida o sin return_value).
    """
    if not isinstance(response_json, dict):
        return {
            "Result": 1,
            "Description": response_text or "Respuesta SOAP invalida",
            "invoices": [],
        }

    fault = _search_key(response_json, "faultstring")
    if fault is None:
        fault = _search_key(response_json, "Fault")
    if fault:
        return {
            "Result": 1,
            "Description": str(fault).strip() or response_text,
            "invoices": [],
        }

    return_value = _search_key(response_json, "return_value")
    if return_value is None:
        return {
            "Result": 1,
            "Description": response_text or "BC no devolvio return_value",
            "invoices": [],
        }

    raw = str(return_value)
    parts = raw.split(";")
    if raw.endswith(";"):
        parts = parts[:-1]

    invoices = []
    for idx in range(num_invoices):
        part = parts[idx].strip() if idx < len(parts) else ""
        if not part:
            invoices.append({
                "doc_number": "",
                "error": "BC no devolvio documento para la factura",
            })
        elif part.lower().startswith("error"):
            invoices.append({"doc_number": "", "error": part})
        else:
            invoices.append({"doc_number": part, "error": ""})

    return {"Result": 0, "invoices": invoices}


@frappe.whitelist()
def create_purchase_invoices(payload, endpoint_code="create_purchase_order"):
    errors = validate_purchase_invoice_payload(payload)
    if errors:
        return {
            "Result": 1,
            "Description": "; ".join(errors),
            "invoices": [],
        }

    num_invoices = len(payload)

    try:
        response_text, response_json, error = _send_soap(endpoint_code, payload)
    except Exception as e:
        return {
            "Result": 1,
            "Description": str(e),
            "invoices": [],
        }

    if error:
        return {
            "Result": 1,
            "Description": response_text or "Error en la peticion a BC",
            "invoices": [],
        }

    return parse_purchase_invoice_response(response_json, response_text, num_invoices)
