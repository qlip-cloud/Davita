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
)

# Campos que se envian con la OC/recibo de la factura si los tiene; si la
# factura no tiene orden de compra ni recepcion (p. ej. factura de contado
# sin recibo) se envian como string vacio "" y no bloquean la creacion.
OPTIONAL_LINE_FIELDS = ("NoPedido", "NoRecepcion")


def _validate_factura(factura, idx):
    """Valida las condiciones minimas de UNA factura (con su indice).

    Retorna una lista de errores (vacia si la factura es valida). Permite
    atribuir el resultado por factura en lugar de abortar todo el lote.
    """
    errors = []

    if not isinstance(factura, dict):
        return ["Factura {}: debe ser un objeto".format(idx)]

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
        return errors

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


def validate_purchase_invoice_payload(payload):
    """Valida las condiciones minimas para enviar a BC.

    Retorna una lista de errores (vacia si el payload es valido).
    """
    if not isinstance(payload, list) or not payload:
        return ["El payload debe ser una lista de facturas"]

    errors = []
    for idx, factura in enumerate(payload):
        errors.extend(_validate_factura(factura, idx))
    return errors


def split_invoices(payload):
    """Separa facturas validas e invalidas conservando la posicion original.

    Retorna (valid_invoices, invalid_by_index) donde invalid_by_index mapea
    la posicion original de cada factura invalida a su mensaje de error.
    Permite descontaminar el lote: enviar a BC solo las validas y devolver
    el error solo en la factura erronea, sin que afecte a las demas.
    """
    valid = []
    invalid = {}
    for idx, factura in enumerate(payload or []):
        errors = _validate_factura(factura, idx)
        if errors:
            invalid[idx] = "; ".join(errors)
        else:
            valid.append(factura)
    return valid, invalid


def merge_invoice_results(payload_count, invalid_by_index, bc_invoices):
    """Alinea los resultados de BC con las posiciones originales del payload.

    Los resultados de BC llegan en el orden de las facturas validas enviadas;
    se intercalan los errores locales en las posiciones de las invalidas para
    que el consumidor pueda atribuir cada resultado a su factura. Si BC no
    entrego resultado para alguna factura valida, se devuelve el error por
    defecto de "no devolvio documento".
    """
    results = iter(bc_invoices or [])
    invoices = []
    for idx in range(payload_count):
        if idx in invalid_by_index:
            invoices.append({"doc_number": "", "error": invalid_by_index[idx]})
            continue
        try:
            invoices.append(next(results))
        except StopIteration:
            invoices.append({
                "doc_number": "",
                "error": "BC no devolvio documento para la factura",
            })
    return invoices


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


def _extract_fault_text(fault):
    """Extrae el texto legible de un nodo fault SOAP.

    Un faultstring puede llegar como string plano o como dict con un
    atributo y el texto en la clave '#text' (p. ej. xmltodict produce
    {'@xml:lang': 'en-US', '#text': 'The metadata object CodeUnit 66908...'}).
    """
    if isinstance(fault, dict):
        text = fault.get("#text")
        if text:
            return str(text).strip()
        return str(fault).strip()
    return str(fault).strip()


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
            "Description": _extract_fault_text(fault) or response_text,
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
    if not isinstance(payload, list) or not payload:
        return {
            "Result": 1,
            "Description": "El payload debe ser una lista de facturas",
            "invoices": [],
        }

    # Descontaminacion: una factura invalida no aborta el lote. Las facturas
    # validas se envian a BC y las invalidas devuelven su propio error en su
    # posicion original (BC es quien decide, por ejemplo, sobre campos
    # opcionales como NoPedido/NoRecepcion).
    valid_invoices, invalid_by_index = split_invoices(payload)

    if not valid_invoices:
        return {
            "Result": 1,
            "Description": "; ".join(invalid_by_index.values()),
            "invoices": [],
        }

    try:
        response_text, response_json, error = _send_soap(endpoint_code, valid_invoices)
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
