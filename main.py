from flask import Flask, request, jsonify
import re
import sys
import urllib.parse

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        # PRIMER PASO CRÍTICO: Imprimir el body RAW recibido, sin intentar JSON
        raw_data = request.data.decode('utf-8', errors='ignore') # Decodificar como UTF-8, ignorando errores
        sys.stderr.write(f"--- DEBUG RAW DATA RECEIVED ---\n")
        sys.stderr.write(f"Raw Request Data: {raw_data}\n")
        sys.stderr.write(f"--- END RAW DATA ---\n")

        # Intentar parsear como JSON, pero ahora con más control
        request_json = None
        try:
            request_json = request.get_json(silent=True) # silent=True para evitar errores si no es JSON
        except Exception as json_error:
            sys.stderr.write(f"ERROR al intentar parsear JSON: {json_error}\n")
            sys.stderr.write(f"Data that caused JSON parsing error: {request.data}\n")

        if request_json is None:
            sys.stderr.write("ERROR: Request body was not valid JSON or was empty.\n")
            # Si no es JSON válido, intentamos procesar el raw_data directamente (como texto plano)
            # Esto es una estrategia de último recurso para avanzar en la depuración
            text_to_parse = raw_data
            sys.stderr.write(f"Attempting to parse raw data as plain text for debugging: {text_to_parse[:500]}...\n")
        else:
            # Si es JSON, obtenemos el campo 'text'
            text_field = request_json.get('text')
            if text_field:
                text_to_parse = urllib.parse.unquote(text_field) # Decodificamos si fue urlEncoded
                sys.stderr.write(f"DEBUG: 'text' field from JSON (decoded): {text_to_parse[:500]}...\n")
            else:
                sys.stderr.write("ERROR: JSON was parsed, but 'text' field is missing or empty.\n")
                return jsonify({"status": "error", "message": "JSON parsed but 'text' field missing"}), 400

        # Si llegamos aquí, tenemos 'text_to_parse' ya sea del JSON o del raw data
        # Ahora, tu lógica de extracción de datos...
        nombre_gasto = "Desconocido"
        moneda = "N/A"
        monto = "0.00"
        comercio = "Desconocido"
        fecha_transaccion = "Fecha Desconocida"
        
        # Nuevos campos
        tarjeta = "Desconocida"
        ultimos_4_digitos = "N/A"
        numero_autorizacion = "N/A"
        tipo_transaccion = "Desconocido"
        ciudad_pais_comercio = "Desconocida"

        # ... (Mantén aquí todas tus expresiones regulares como estaban) ...
        # Por ejemplo:
        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD)\s*([\d\.,]+)', text_to_parse)
        if monto_match:
            moneda = monto_match.group(1)
            monto_str = monto_match.group(2).replace('.', '').replace(',', '.')
            monto = monto_str

        # Y todas las demás RegEx para los nuevos campos
        tarjeta_match = re.search(r'(?:Tarjeta|Medio de Pago):\s*([A-Za-z]+)(?:\s*\(?(\*+)(\d{4})\)?)?', text_to_parse, re.IGNORECASE)
        if tarjeta_match:
            tarjeta = tarjeta_match.group(1).upper()
            if tarjeta_match.group(3):
                ultimos_4_digitos = tarjeta_match.group(3)
        
        autorizacion_match = re.search(r'(?:No\.?\s*Autorización|Autorización No?\.?|Código de Autorización|Auth Code):\s*(\w+)', text_to_parse, re.IGNORECASE)
        if autorizacion_match:
            numero_autorizacion = autorizacion_match.group(1).strip()

        tipo_transaccion_match = re.search(r'(Compra|Retiro|Débito|Crédito|Pago|Transacción)\s+(?:por|realizada|efectuada)', text_to_parse, re.IGNORECASE)
        if tipo_transaccion_match:
            tipo_transaccion = tipo_transaccion_match.group(1).strip()


        # Lógica de sobrepaso_ppto
        sobrepaso_ppto = False
        try:
            monto_float = float(monto)
            if moneda == "USD":
                if monto_float > 50.00:
                    sobrepaso_ppto = True
            elif moneda == "CRC":
                if monto_float > 30000.00:
                    sobrepaso_ppto = True
        except ValueError:
            sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{monto}' a número para el cálculo de presupuesto. Asumiendo False.\n")
            sobrepaso_ppto = False

        comentario = f"Transacción de {comercio} por {moneda} {monto}."
        if tarjeta != "Desconocida" and ultimos_4_digitos != "N/A":
            comentario += f" (Tarjeta: {tarjeta} ****{ultimos_4_digitos})."
        if tipo_transaccion != "Desconocido":
            comentario += f" Tipo: {tipo_transaccion}."
        if numero_autorizacion != "N/A":
            comentario += f" Autorización: {numero_autorizacion}."
        if ciudad_pais_comercio != "Desconocida":
            comentario += f" Ubicación: {ciudad_pais_comercio}."


        response_data = {
            "nombre_gasto": nombre_gasto,
            "moneda": moneda,
            "monto": float(monto),
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
    app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT', 5000))
