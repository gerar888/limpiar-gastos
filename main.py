from flask import Flask, request, jsonify
import re
import sys
import os
import urllib.parse

app = Flask(__name__)

def parse_number_localized(s: str) -> float:
    """
    Convierte un string numérico con posibles separadores de miles/decimal (., ,)
    a float, usando heurísticas seguras:
      - Si hay punto y coma, el último símbolo es el decimal.
      - Si solo hay coma, se asume coma decimal.
      - Si solo hay punto:
          * si calza patrón miles (1.234 o 12.345.678) => quita puntos
          * si el último grupo tiene 1–2 dígitos => punto decimal (600.00, 0.60)
          * otro caso => probable miles => quita puntos
      - Sin separadores => float directo
    """
    s = s.strip().replace(' ', '')
    has_dot = '.' in s
    has_comma = ',' in s

    if has_dot and has_comma:
        last_dot = s.rfind('.')
        last_comma = s.rfind(',')
        # El último símbolo es el separador decimal
        if last_dot > last_comma:
            # '.' decimal => quitar comas (miles)
            s_norm = s.replace(',', '')
        else:
            # ',' decimal => quitar puntos (miles) y cambiar ',' por '.'
            s_norm = s.replace('.', '').replace(',', '.')
        return float(s_norm)

    if has_comma and not has_dot:
        # Coma como decimal
        return float(s.replace(',', '.'))

    if has_dot and not has_comma:
        # ¿Punto miles?
        if re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
            return float(s.replace('.', ''))
        parts = s.split('.')
        if len(parts[-1]) in (1, 2):
            # punto decimal usual (600.00, 0.60)
            return float(s)
        # Caso raro: tratar como miles
        return float(s.replace('.', ''))

    # sin separadores
    return float(s)


@app.route('/', methods=['POST'])
def handle_request():
    try:
        raw_data = request.data.decode('utf-8', errors='ignore')
        sys.stderr.write(f"--- DEBUG RAW DATA RECEIVED ---\n")
        sys.stderr.write(f"Raw Request Data: {raw_data}\n")
        sys.stderr.write(f"--- END RAW DATA ---\n")

        request_json = None
        try:
            request_json = request.get_json(silent=True)
        except Exception as json_error:
            sys.stderr.write(f"ERROR al intentar parsear JSON: {json_error}\n")
            sys.stderr.write(f"Data que causó el error JSON: {request.data}\n")

        if request_json is None:
            sys.stderr.write("ERROR: Body no es JSON válido o viene vacío. Uso texto crudo.\n")
            text_to_parse = raw_data
        else:
            text_field = request_json.get('text')
            if text_field:
                text_to_parse = urllib.parse.unquote(text_field)
                sys.stderr.write(f"DEBUG: 'text' desde JSON (decodificado): {text_to_parse[:500]}...\n")
            else:
                sys.stderr.write("ERROR: JSON parsed, pero falta el campo 'text'.\n")
                return jsonify({"status": "error", "message": "JSON parsed but 'text' field missing"}), 400

        # --- Inicialización ---
        nombre_gasto = "Desconocido"
        moneda = "N/A"
        monto = 0.00
        comercio = "Desconocido"
        fecha_transaccion = "Fecha Desconocida"
        tarjeta = "Desconocida"
        ultimos_4_digitos = "N/A"
        numero_autorizacion = "N/A"
        tipo_transaccion = "Desconocido"
        ciudad_pais_comercio = "Desconocida"

        # --- MONTO Y MONEDA ---
        monto_match = re.search(
            r'(?:Monto:\s*)?'
            r'(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD|[$€£])'
            r'\s*'
            r'([\d\.,\s]+)',
            text_to_parse, re.IGNORECASE
        )

        original_monto_str_raw = ""
        if monto_match:
            moneda_identificada = monto_match.group(1).upper()
            original_monto_str_raw = monto_match.group(2).strip()

            if moneda_identificada == '$':
                moneda = 'USD'
            elif moneda_identificada == '€':
                moneda = 'EUR'
            elif moneda_identificada == 'CRC':
                moneda = 'CRC'
            else:
                moneda = moneda_identificada

            try:
                monto = parse_number_localized(original_monto_str_raw)
            except ValueError:
                sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{original_monto_str_raw}' a float.\n")
                monto = 0.00

        # --- COMERCIO ---
        comercio_match = re.search(
            r'(?:Comercio|Compra en|Movimiento en|Transacción en):\s*([A-Za-z0-9\s\.\-&]+)',
            text_to_parse, re.IGNORECASE
        )
        if comercio_match:
            comercio_raw = comercio_match.group(1).strip()
            ciudad_split_match = re.search(r'(.+?)\s+Ciudad', comercio_raw, re.IGNORECASE)
            if ciudad_split_match:
                comercio = ciudad_split_match.group(1).strip()
            else:
                comercio = comercio_raw
            nombre_gasto = comercio

        # --- FECHA ---
        fecha_transaccion_match = re.search(
            r'Fecha:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:de)?\s+[A-Za-záéíóúÁÉÍÓÚñÑ]+(?:\s+de)?\s*\d{2,4})',
            text_to_parse, re.IGNORECASE
        )
        if fecha_transaccion_match:
            fecha_transaccion = fecha_transaccion_match.group(1).strip()

        # --- TARJETA / 4 DÍGITOS ---
        tarjeta_match = re.search(
            r'(?:Tarjeta|Medio de Pago):\s*([A-Za-z]+)(?:\s*\*+(\d{4}))?',
            text_to_parse, re.IGNORECASE
        )
        if tarjeta_match:
            tarjeta = tarjeta_match.group(1).upper()
            if tarjeta_match.group(2):
                ultimos_4_digitos = tarjeta_match.group(2)
            else:
                ultimos_4_digitos = "N/A"

        # --- AUTORIZACIÓN ---
        autorizacion_match = re.search(
            r'(?:No\.?\s*Autorización|Autorización No?\.?|Código de Autorización|Auth Code):\s*(\w+)',
            text_to_parse, re.IGNORECASE
        )
        if autorizacion_match:
            numero_autorizacion = autorizacion_match.group(1).strip()

        # --- TIPO ---
        tipo_transaccion_match = re.search(
            r'(?:Tipo:\s*)(Compra|Retiro|Débito|Crédito|Pago|Transacción)',
            text_to_parse, re.IGNORECASE
        )
        if tipo_transaccion_match:
            tipo_transaccion = tipo_transaccion_match.group(1).strip()

        # --- Sobrepaso presupuesto (simple) ---
        sobrepaso_ppto = False
        if isinstance(monto, (int, float)):
            if moneda == "USD":
                sobrepaso_ppto = monto > 50.00
            elif moneda == "CRC":
                sobrepaso_ppto = monto > 30000.00
        else:
            sys.stderr.write(f"ADVERTENCIA: Monto no numérico para presupuesto ({monto}).\n")
            sobrepaso_ppto = False

        # --- Comentario ---
        comentario = f"Transacción de {comercio} por {moneda} {monto:.2f}."
        if tarjeta != "Desconocida" and ultimos_4_digitos != "N/A":
            comentario += f" (Tarjeta: {tarjeta} ****{ultimos_4_digitos})."
        if tipo_transaccion != "Desconocido":
            comentario += f" Tipo: {tipo_transaccion}."
        if numero_autorizacion != "N/A":
            comentario += f" Autorización: {numero_autorizacion}."
        if ciudad_pais_comercio != "Desconocida":
            comentario += f" Ubicación: {ciudad_pais_comercio}."

        # --- Respuesta ---
        response_data = {
            "nombre_gasto": nombre_gasto,
            "moneda": moneda,
            "monto": monto,
            "comercio": comercio,
            "fecha_transaccion": fecha_transaccion,
            "sobrepaso_ppto": sobrepaso_ppto,
            "comentario": comentario,
            "tarjeta": tarjeta,
            "ultimos_4_digitos": ultimos_4_digitos,
            "numero_autorizacion": numero_autorizacion,
            "tipo_transaccion": tipo_transaccion,
            "ciudad_pais_comercio": ciudad_pais_comercio
        }

        sys.stderr.write(f"DEBUG: Final response data: {response_data}\n")
        return jsonify(response_data), 200

    except Exception as e:
        sys.stderr.write(f"!!! ERROR FATAL EN LA APLICACIÓN PYTHON: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
