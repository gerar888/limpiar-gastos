import os
from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    print(f"--- LOG DE DEPURACION: Solicitud recibida en handle_request ---") # Este es el nuevo print
    # raise Exception("ERROR FORZADO PARA DEPURACION INTERNA") # ¡Comenta o quita esta línea si la habías puesto!

    try:
        # Los siguientes prints deberían aparecer si la línea de arriba funciona
        print(f"--- NUEVA SOLICITUD RECIBIDA ---")
        print(f"Request Method: {request.method}")
        print(f"Request Headers: {request.headers}")
        # print(f"Request Body (raw): {request.data}") # Lo comentamos para evitar logs muy largos

        if not request.data:
            print("Error: No body data received in the request.")
            return jsonify({"error": "No data received"}), 400

        received_text = request.data.decode('utf-8')
        print(f"Received text data: {received_text}") # Aquí debería aparecer todo el texto del correo

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
        print(f"DEBUG: Comercio/Nombre del gasto encontrado: '{comercio}'")

        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR)\s*([\d\.,]+)', received_text)
        if monto_match:
            moneda = monto_match.group(1)
            monto_str = monto_match.group(2).replace('.', '').replace(',', '.')
            monto = monto_str
        print(f"DEBUG: Monto encontrado: '{monto}', Moneda: '{moneda}'")

        fecha_match = re.search(r'Fecha:\s*(.+?, \d{4}, \d{2}:\d{2})', received_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(1).strip()
        print(f"DEBUG: Fecha encontrada: '{fecha_transaccion}'")

        sobrepaso_ppto = False
        try:
            monto_float = float(monto)
            if monto_float > 50.00 and moneda == "USD":
                sobrepaso_ppto = True
            elif monto_float > 30000.00 and moneda == "CRC":
                 sobrepaso_ppto = True
        except ValueError:
            print(f"ADVERTENCIA: No se pudo convertir el monto '{monto}' a número para el cálculo de presupuesto. Asumiendo False.")
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

# No se necesita el if __name__ == '__main__': aquí para Railway.
