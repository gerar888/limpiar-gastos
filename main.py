import os
from flask import Flask, request, jsonify
import re
import sys # Mantener esta importación para sys.stderr

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    # --- LOG DE DEPURACION: Esta línea nos dirá si la función se ejecuta ---
    sys.stderr.write(f"--- LOG DE DEPURACION: Solicitud recibida en handle_request ---\n")
    
    try:
        sys.stderr.write(f"--- NUEVA SOLICITUD RECIBIDA ---\n")
        sys.stderr.write(f"Request Method: {request.method}\n")
        sys.stderr.write(f"Request Headers: {request.headers}\n")
        # sys.stderr.write(f"Request Body (raw): {request.data}\n") # Comentado para evitar logs muy largos

        if not request.data:
            sys.stderr.write("Error: No body data received in the request.\n")
            return jsonify({"error": "No data received"}), 400

        received_text = request.data.decode('utf-8')
        sys.stderr.write(f"Received text data: {received_text}\n")

        # --- Lógica de Extracción de Datos del Texto ---
        nombre_gasto = "Desconocido"
        moneda = "N/A"
        monto = "0.00"
        comercio = "Desconocido"
        fecha_transaccion = "Fecha Desconocida"

        comercio_match = re.search(r'Comercio:\s*([\s\S]*?)(?:Ciudad y país:|Fecha:|$)', received_text)
        if comercio_match:
            comercio = comercio_match.group(1).strip()
            nombre_gasto = comercio
        sys.stderr.write(f"DEBUG: Comercio/Nombre del gasto encontrado: '{comercio}'\n")

        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR)\s*([\d\.,]+)', received_text)
        if monto_match:
            moneda = monto_match.group(1)
            monto_str = monto_match.group(2).replace('.', '').replace(',', '.')
            monto = monto_str
        sys.stderr.write(f"DEBUG: Monto encontrado: '{monto}', Moneda: '{moneda}'\n")

        fecha_match = re.search(r'Fecha:\s*(.+?, \d{4}, \d{2}:\d{2})', received_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(1).strip()
        sys.stderr.write(f"DEBUG: Fecha encontrada: '{fecha_transaccion}'\n")

        sobrepaso_ppto = False
        try:
            monto_float = float(monto)
            if monto_float > 50.00 and moneda == "USD":
                sobrepaso_ppto = True
            elif monto_float > 30000.00 and moneda == "CRC":
                 sobrepaso_ppto = True
        except ValueError:
            sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{monto}' a número para el cálculo de presupuesto. Asumiendo False.\n")
            sobrepaso_ppto = False

        comentario = f"Transacción de {comercio} por {moneda} {monto}."

        response_data = {
            "nombre_gasto": nombre_gasto,
            "moneda": moneda,
            "monto": float(monto),
            "comercio": comercio,
            "fecha_transaccion": fecha_transaccion,
            "sobrepaso_ppto": sobrepaso_ppto,
            "comentario": comentario
        }

        sys.stderr.write(f"DEBUG: Datos parseados para Make: {response_data}\n")

        return jsonify(response_data), 200

    except Exception as e:
        sys.stderr.write(f"!!! ERROR FATAL EN LA APLICACIÓN PYTHON: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500
