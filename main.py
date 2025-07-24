import os
from flask import Flask, request, jsonify
import re # Importa el módulo de expresiones regulares

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        print(f"--- NUEVA SOLICITUD RECIBIDA ---")
        print(f"Request Method: {request.method}")
        print(f"Request Headers: {request.headers}")
        print(f"Request Body (raw): {request.data}")

        # El cuerpo de la solicitud de Make llega como texto plano (no JSON en este caso)
        if not request.data:
            print("Error: No body data received in the request.")
            return jsonify({"error": "No data received"}), 400

        received_text = request.data.decode('utf-8')
        print(f"Received text data: {received_text}")

        # --- Lógica de Extracción de Datos del Texto ---
        # Usaremos expresiones regulares para encontrar la información.

        nombre_gasto = "Desconocido"
        moneda = "N/A"
        monto = "0.00"
        comercio = "Desconocido"
        fecha_transaccion = "Fecha Desconocida"

        # Expresión regular para Comercio (se repite, así que capturaremos el primero)
        comercio_match = re.search(r'Comercio:\s*([\s\S]*?)(?:Ciudad y país:|Fecha:|$)', received_text)
        if comercio_match:
            comercio = comercio_match.group(1).strip()
            # Si "UBER EATS COSTA RICA" es lo que quieres como nombre_gasto, lo asignamos.
            # Podrías refinar esto si el "nombre del gasto" es diferente del "comercio".
            nombre_gasto = comercio
        print(f"DEBUG: Comercio/Nombre del gasto encontrado: {comercio}")

        # Expresión regular para Monto y Moneda
        # Busca "Monto: " seguido de la moneda (USD/CRC, etc.) y luego el número.
        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR)\s*([\d\.,]+)', received_text)
        if monto_match:
            moneda = monto_match.group(1)
            monto_str = monto_match.group(2).replace('.', '') # Elimina puntos de miles
            monto = monto_str.replace(',', '.') # Reemplaza coma decimal por punto
        print(f"DEBUG: Monto encontrado: {monto}, Moneda: {moneda}")

        # Expresión regular para Fecha
        fecha_match = re.search(r'Fecha:\s*(.+?, \d{4}, \d{2}:\d{2})', received_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(1).strip()
        print(f"DEBUG: Fecha encontrada: {fecha_transaccion}")

        # --- Cálculo para 'sobrepaso_ppto' (ejemplo simple) ---
        # Esto es un ejemplo. Puedes definir tu propia lógica para esto.
        # Por ejemplo, si el monto es mayor a 50 USD.
        sobrepaso_ppto = False
        try:
            if float(monto) > 50.00 and moneda == "USD":
                sobrepaso_ppto = True
            elif float(monto) > 30000.00 and moneda == "CRC": # Ejemplo para CRC
                 sobrepaso_ppto = True
        except ValueError:
            print(f"ADVERTENCIA: No se pudo convertir el monto '{monto}' a número para el cálculo de presupuesto.")
            sobrepaso_ppto = False # O deja el valor por defecto

        # --- Comentario (puedes dejarlo vacío o generar uno) ---
        comentario = f"Transacción de {comercio} por {moneda} {monto}." # Ejemplo

        # --- Preparar la respuesta JSON para Make ---
        # Make esperará un JSON con los datos parseados.
        response_data = {
            "nombre_gasto": nombre_gasto,
            "moneda": moneda,
            "monto": float(monto), # Convertir a float si Make lo necesita como número
            "comercio": comercio,
            "fecha_transaccion": fecha_transaccion, # Make se encargará de formatearla para Notion
            "sobrepaso_ppto": sobrepaso_ppto,
            "comentario": comentario
        }

        print(f"DEBUG: Datos parseados para Make: {response_data}")

        return jsonify(response_data), 200

    except Exception as e:
        print(f"!!! ERROR FATAL EN LA APLICACIÓN PYTHON: {e}")
        import traceback
        traceback.print_exc() # Esto imprimirá el rastro completo del error
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
