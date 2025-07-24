import os
from flask import Flask, request, jsonify
import re # Importa el módulo de expresiones regulares

app = Flask(__name__) # Tu aplicación Flask

@app.route('/', methods=['POST'])
def handle_request():
    try:
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

        # Expresión regular para Comercio (se repite, así que capturaremos el primero)
        # Búsqueda: "Comercio: " seguida de cualquier caracter ([\s\S]*?) hasta "Ciudad y país:" o "Fecha:" o fin de string
        comercio_match = re.search(r'Comercio:\s*([\s\S]*?)(?:Ciudad y país:|Fecha:|$)', received_text)
        if comercio_match:
            comercio = comercio_match.group(1).strip()
            nombre_gasto = comercio # Asignamos comercio como nombre_gasto por simplicidad
        print(f"DEBUG: Comercio/Nombre del gasto encontrado: '{comercio}'")

        # Expresión regular para Monto y Moneda
        # Búsqueda: "Monto: " seguida de Moneda (USD|CRC|EUR) y luego número con puntos/comas
        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR)\s*([\d\.,]+)', received_text)
        if monto_match:
            moneda = monto_match.group(1)
            # Elimina puntos de miles y asegura que la coma sea el separador decimal para Python (reemplaza por punto)
            monto_str = monto_match.group(2).replace('.', '').replace(',', '.')
            monto = monto_str
        print(f"DEBUG: Monto encontrado: '{monto}', Moneda: '{moneda}'")

        # Expresión regular para Fecha
        # Búsqueda: "Fecha: " seguida de cualquier caracter hasta una coma y "YYYY, HH:MM"
        # Asegúrate de que el formato de fecha en el correo coincida con este patrón.
        fecha_match = re.search(r'Fecha:\s*(.+?, \d{4}, \d{2}:\d{2})', received_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(1).strip()
        print(f"DEBUG: Fecha encontrada: '{fecha_transaccion}'")

        # --- Cálculo para 'sobrepaso_ppto' (ejemplo simple) ---
        sobrepaso_ppto = False
        try:
            # Asegúrate que 'monto' sea un número antes de comparar
            monto_float = float(monto)
            if monto_float > 50.00 and moneda == "USD":
                sobrepaso_ppto = True
            elif monto_float > 30000.00 and moneda == "CRC": # Ejemplo para Costa Rica
                 sobrepaso_ppto = True
        except ValueError:
            print(f"ADVERTENCIA: No se pudo convertir el monto '{monto}' a número para el cálculo de presupuesto. Asumiendo False.")
            sobrepaso_ppto = False # Si hay error al convertir, no sobrepasó presupuesto

        # --- Comentario (puedes dejarlo vacío o generar uno) ---
        comentario = f"Transacción de {comercio} por {moneda} {monto}." # Ejemplo

        # --- Preparar la respuesta JSON para Make ---
        response_data = {
            "nombre_gasto": nombre_gasto,
            "moneda": moneda,
            "monto": float(monto), # Convertir a float ANTES de enviar a Make para asegurar el tipo de dato
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

# YA NO NECESITAMOS EL if __name__ == '__main__': BLOQUE AQUÍ
# Gunicorn se encargará de ejecutar 'app' directamente.
