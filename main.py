import os
from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        print(f"--- NUEVA SOLICITUD RECIBIDA ---")
        print(f"Request Method: {request.method}")
        print(f"Request Headers: {request.headers}")
        print(f"Request Body (raw): {request.data}")

        if not request.data:
            print("Error: No body data received in the request.")
            return jsonify({"error": "No data received"}), 400

        received_text = request.data.decode('utf-8')
        print(f"Received text data: {received_text}")

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
        print(f"DEBUG: Comercio/Nombre del gasto encontrado: {comercio}")

        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR)\s*([\d\.,]+)', received_text)
        if monto_match:
            moneda = monto_match.group(1)
            monto_str = monto_match.group(2).replace('.', '')
            monto = monto_str.replace(',', '.')
        print(f"DEBUG: Monto encontrado: {monto}, Moneda: {moneda}")

        fecha_match = re.search(r'Fecha:\s*(.+?, \d{4}, \d{2}:\d{2})', received_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(1).strip()
        print(f"DEBUG: Fecha encontrada: {fecha_transaccion}")

        sobrepaso_ppto = False
        try:
            if float(monto) > 50.00 and moneda == "USD":
                sobrepaso_ppto = True
            elif float(monto) > 30000.00 and moneda == "CRC":
                 sobrepaso_ppto = True
        except ValueError:
            print(f"ADVERTENCIA: No se pudo convertir el monto '{monto}' a número para el cálculo de presupuesto.")
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

        print(f"DEBUG: Datos parseados para Make: {response_data}")

        return jsonify(response_data), 200

    except Exception as e:
        print(f"!!! ERROR FATAL EN LA APLICACIÓN PYTHON: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500

# Esto asegura que gunicorn se encargue de ejecutar la app en Railway
# y que la app.run() solo se use si ejecutas el archivo directamente para pruebas locales.
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
