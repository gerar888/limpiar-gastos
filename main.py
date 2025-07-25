import os
import re
import json
import sys
from flask import Flask, request

app = Flask(__name__)

# Función para limpiar el texto (eliminar URLs y el texto "Icono decorativo [URL]")
def clean_text(text):
    # Eliminar patrones de "Icono decorativo [URL]"
    text = re.sub(r'Icono decorativo \[https?://[^\s\]]+\]', '', text)
    # Eliminar cualquier URL restante que no sea parte de un patrón específico que queremos mantener
    text = re.sub(r'https?://[^\s\]]+', '', text)
    # También eliminar los '[https://...]' que quedan después de eliminar los logos al inicio
    text = re.sub(r'\[https?://[^\s\]]+\]', '', text)
    return text

@app.route('/', methods=['POST'])
def process_email():
    try:
        # --- NUEVAS LÍNEAS DE DEPURACIÓN (MUY IMPORTANTES) ---
        sys.stderr.write(f"DEBUG: Request.data (raw): {request.data}\n")
        sys.stderr.write(f"DEBUG: Request.content_type: {request.content_type}\n")
        # --- FIN DE NUEVAS LÍNEAS DE DEPURACIÓN ---

        data = None
        try:
            data = request.json
            sys.stderr.write(f"DEBUG: Request.json (parsed): {data}\n") # Log del JSON parseado
        except Exception as e:
            sys.stderr.write(f"ERROR: No se pudo parsear JSON: {e}\n")
            return json.dumps({"status": "error", "message": f"Invalid JSON format: {e}"}), 400

        if not data or 'text' not in data:
            sys.stderr.write("ERROR: No 'text' field found in the request data or data is empty.\n")
            return json.dumps({"status": "error", "message": "No 'text' field in JSON"}), 400

        received_text = data['text']
        
        # Validación extra: si 'text' es nulo o una cadena vacía
        if not received_text:
            sys.stderr.write("ERROR: 'text' field is empty or null.\n")
            return json.dumps({"status": "error", "message": "'text' field is empty"}), 400

        sys.stderr.write(f"DEBUG: Texto recibido: '{received_text[:200]}...'\n") # Muestra solo los primeros 200 caracteres

        # --- Limpieza del Texto ---
        cleaned_text = clean_text(received_text)
        sys.stderr.write(f"DEBUG: Texto limpiado: '{cleaned_text[:200]}...'\n")

        # --- Lógica de Extracción de Datos del Texto ---
        comercio = "Desconocido"
        monto = 0.0
        moneda = "N/A"
        fecha_transaccion = "N/A"
        tipo_tarjeta = "Desconocido"
        ultimos_4_tarjeta = "N/A"
        autorizacion = "N/A"
        tipo_transaccion = "Desconocido" # Añadido el tipo de transacción

        # Extracción de Comercio
        comercio_match = re.search(r'Comercio:\s*([\s\w]+)', cleaned_text)
        if comercio_match:
            comercio = comercio_match.group(1).strip()
        sys.stderr.write(f"DEBUG: Comercio encontrado: '{comercio}'\n")

        # Extracción de Monto y Moneda
        monto_moneda_match = re.search(r'Monto:\s*([A-Z]{3})\s*([\d\.,]+)', cleaned_text)
        if monto_moneda_match:
            moneda = monto_moneda_match.group(1).strip()
            # Reemplazar ',' por '' para miles, y luego '.' para decimales si es necesario (el float lo maneja)
            monto_str = monto_moneda_match.group(2).replace(',', '') 
            try:
                monto = float(monto_str)
            except ValueError:
                sys.stderr.write(f"ERROR: No se pudo convertir el monto '{monto_str}' a float.\n")
                monto = 0.0 # Valor por defecto si falla la conversión
        sys.stderr.write(f"DEBUG: Monto encontrado: {monto}, Moneda: '{moneda}'\n")

        # Extracción de Fecha
        # Modificado para capturar el formato "Mes Día, Año, HH:MM"
        fecha_match = re.search(r'Fecha:\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}, \d{4}, \d{2}:\d{2}', cleaned_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(0).replace('Fecha:', '').strip()
        sys.stderr.write(f"DEBUG: Fecha encontrada: '{fecha_transaccion}'\n")

        # --- Nuevas Extracciones ---

        # Extracción de Tipo de Tarjeta y Últimos 4 Dígitos
        tarjeta_match = re.search(r'(AMEX|VISA|MASTERCARD)\s*\*+([\d]{4})', cleaned_text, re.IGNORECASE)
        if tarjeta_match:
            tipo_tarjeta = tarjeta_match.group(1).upper()
            ultimos_4_tarjeta = tarjeta_match.group(2)
        else:
            ultimos_4_match = re.search(r'\*+(\d{4})', cleaned_text)
            if ultimos_4_match:
                ultimos_4_tarjeta = ultimos_4_match.group(1)
        sys.stderr.write(f"DEBUG: Tipo Tarjeta: '{tipo_tarjeta}', Últimos 4 Tarjeta: '{ultimos_4_tarjeta}'\n")

        # Extracción de Número de Autorización
        autorizacion_match = re.search(r'Autorización:\s*(\d+)', cleaned_text)
        if autorizacion_match:
            autorizacion = autorizacion_match.group(1).strip()
        sys.stderr.write(f"DEBUG: Autorización: '{autorizacion}'\n")

        # Extracción de Tipo de Transacción
        tipo_transaccion_match = re.search(r'Tipo de Transacción:\s*([A-Z\s]+)', cleaned_text)
        if tipo_transaccion_match:
            tipo_transaccion = tipo_transaccion_match.group(1).strip()
        sys.stderr.write(f"DEBUG: Tipo de Transacción: '{tipo_transaccion}'\n")


        # --- Lógica de Negocio (Ejemplo de sobrepaso_ppto) ---
        sobrepaso_ppto = monto > 50.0 

        # Comentario adicional (opcional)
        comentario = "Gasto procesado automáticamente."
        if sobrepaso_ppto:
            comentario = "¡Alerta! Gasto alto detectado."

        # --- Construir la respuesta JSON ---
        response_data = {
            "comercio": comercio,
            "monto": monto,
            "moneda": moneda,
            "fecha_transaccion": fecha_transaccion,
            "tipo_tarjeta": tipo_tarjeta,
            "ultimos_4_tarjeta": ultimos_4_tarjeta,
            "autorizacion": autorizacion,
            "tipo_transaccion": tipo_transaccion,
            "sobrepaso_ppto": sobrepaso_ppto,
            "comentario": comentario
        }

        sys.stderr.write(f"DEBUG: Respondiendo con JSON: {json.dumps(response_data, indent=2)}\n")
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        sys.stderr.write(f"ERROR: An unexpected error occurred in process_email: {e}\n")
        # Asegúrate de que el error siempre retorne un JSON válido
        return json.dumps({"status": "error", "message": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    sys.stderr.write(f"DEBUG: Starting Flask app on port {port}\n")
    app.run(host='0.0.0.0', port=port)
