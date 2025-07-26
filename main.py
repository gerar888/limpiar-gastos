import os
from flask import Flask, request, jsonify
import re
import sys

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    sys.stderr.write(f"--- LOG DE DEPURACION: Solicitud recibida en handle_request ---\n")
    
    try:
        sys.stderr.write(f"--- NUEVA SOLICITUD RECIBIDA ---\n")
        sys.stderr.write(f"Request Method: {request.method}\n")
        sys.stderr.write(f"Request Headers: {request.headers}\n")

        # --- CAMBIO IMPORTANTE AQUÍ: LEER JSON SI Make ENVÍA JSON ---
        request_json = request.get_json()
        if not request_json or 'text' not in request_json:
            sys.stderr.write("Error: 'text' field is empty or null in JSON payload.\n")
            return jsonify({"error": "'text' field is empty or null"}), 400
        
        received_text = request_json.get('text')
        # Si Make envía texto plano directamente, usar esta línea en su lugar y comentar las 4 anteriores:
        # received_text = request.data.decode('utf-8') 
        
        sys.stderr.write(f"Received text data: {received_text}\n")

        # --- Lógica de Extracción de Datos del Texto ---
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
        ciudad_pais_comercio = "Desconocida" # Inicializar como string

        # Expresiones Regulares (RegEx) para extraer la información
        # Asegúrate de que los patrones coincidan exactamente con tus correos
        
        # Comercio
        comercio_match = re.search(r'Comercio:\s*([\s\S]*?)(?:Ciudad y país:|Fecha:|Monto:|$)', received_text)
        if comercio_match:
            comercio = comercio_match.group(1).strip()
            nombre_gasto = comercio
        sys.stderr.write(f"DEBUG: Comercio/Nombre del gasto encontrado: '{comercio}'\n")

        # Monto y Moneda
        monto_match = re.search(r'Monto:\s*(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD)\s*([\d\.,]+)', received_text)
        if monto_match:
            moneda = monto_match.group(1)
            # Manejo de separador de miles (punto) y decimales (coma) o viceversa
            monto_str = monto_match.group(2).replace('.', '').replace(',', '.') # Asume 1.000,00 -> 1000.00
            monto = monto_str
        sys.stderr.write(f"DEBUG: Monto encontrado: '{monto}', Moneda: '{moneda}'\n")

        # Fecha de Transacción
        fecha_match = re.search(r'Fecha:\s*(.+?, \d{4}, \d{2}:\d{2})', received_text)
        if fecha_match:
            fecha_transaccion = fecha_match.group(1).strip()
        sys.stderr.write(f"DEBUG: Fecha encontrada: '{fecha_transaccion}'\n")
        
        # --- Nuevas Extracciones ---

        # Tarjeta (ej. AMEX, VISA, MASTERCARD) y Últimos 4 Dígitos
        # Patrones comunes: "Tarjeta: AMEX (****1234)", "Tarjeta AMEX ****1234", "Terminada en 1234 (VISA)"
        # Ajusta este patrón a cómo aparece en tus correos
        tarjeta_match = re.search(r'(?:Tarjeta|Medio de Pago):\s*([A-Za-z]+)(?:\s*\(?(\*+)(\d{4})\)?)?', received_text, re.IGNORECASE)
        if tarjeta_match:
            tarjeta = tarjeta_match.group(1).upper() # Convertir a mayúsculas (VISA, AMEX, etc.)
            if tarjeta_match.group(3): # Si se capturaron los últimos 4 dígitos
                ultimos_4_digitos = tarjeta_match.group(3)
        # Otro patrón si la tarjeta y los 4 dígitos están separados o en otro formato
        else:
             ultimos_4_digitos_match = re.search(r'(?:terminada en|finaliza en|con tarjeta)\s*(\d{4})', received_text, re.IGNORECASE)
             if ultimos_4_digitos_match:
                 ultimos_4_digitos = ultimos_4_digitos_match.group(1)
             tarjeta_tipo_match = re.search(r'(Visa|Mastercard|Amex|American Express|Discover|Diners Club)', received_text, re.IGNORECASE)
             if tarjeta_tipo_match:
                 tarjeta = tarjeta_tipo_match.group(1).upper()

        sys.stderr.write(f"DEBUG: Tarjeta: '{tarjeta}', Últimos 4 Dígitos: '{ultimos_4_digitos}'\n")

        # Número de Autorización
        # Patrones comunes: "No. Autorización: 123456", "Autorización #123456", "Código de Autorización: 123456"
        autorizacion_match = re.search(r'(?:No\.?\s*Autorización|Autorización No?\.?|Código de Autorización|Auth Code):\s*(\w+)', received_text, re.IGNORECASE)
        if autorizacion_match:
            numero_autorizacion = autorizacion_match.group(1).strip()
        sys.stderr.write(f"DEBUG: Número de Autorización: '{numero_autorizacion}'\n")

        # Tipo de Transacción (ej. Compra, Retiro, Débito, Crédito)
        # Ajusta este patrón si tus correos usan frases específicas
        tipo_transaccion_match = re.search(r'(Compra|Retiro|Débito|Crédito|Pago|Transacción)\s+(?:por|realizada|efectuada)', received_text, re.IGNORECASE)
        if tipo_transaccion_match:
            tipo_transaccion = tipo_transaccion_match.group(1).strip()
        else: # Si no se encuentra un tipo explícito, intentar inferir por la moneda/monto o saldo
            if re.search(r'nuevo saldo|saldo actual|disponible', received_text, re.IGNORECASE):
                if float(monto) > 0: # Si es un aumento de saldo o un gasto
                     tipo_transaccion = "Compra/Débito" # Se puede afinar más
            elif re.search(r'Reverso|Anulación', received_text, re.IGNORECASE):
                tipo_transaccion = "Reverso/Anulación"
            elif re.search(r'Retiro', received_text, re.IGNORECASE):
                tipo_transaccion = "Retiro"
            elif float(monto) < 0:
                tipo_transaccion = "Crédito/Reembolso"


        sys.stderr.write(f"DEBUG: Tipo de Transacción: '{tipo_transaccion}'\n")

        # Ciudad y País del Comercio (ej. San José, Costa Rica)
        # Este es más delicado porque los formatos varían mucho.
        # Intento 1: "Ciudad y país: San José, Costa Rica"
        ciudad_pais_match = re.search(r'Ciudad y país:\s*([\s\S]*?)(?:Fecha:|Monto:|$)', received_text)
        if ciudad_pais_match:
            ciudad_pais_comercio = ciudad_pais_match.group(1).strip()
        # Intento 2: Buscar patrones comunes para ubicaciones después del Comercio o de la Dirección
        elif re.search(r'\b(?:ciudad|city|ubicacion|location):\s*([A-Za-z\s,.]+)\s*,\s*([A-Za-z\s.]+)\b', received_text, re.IGNORECASE):
             ciudad_pais_comercio = re.search(r'\b(?:ciudad|city|ubicacion|location):\s*([A-Za-z\s,.]+)\s*,\s*([A-Za-z\s.]+)\b', received_text, re.IGNORECASE).group(1).strip() + ", " + re.search(r'\b(?:ciudad|city|ubicacion|location):\s*([A-Za-z\s,.]+)\s*,\s*([A-Za-z\s.]+)\b', received_text, re.IGNORECASE).group(2).strip()
        
        sys.stderr.write(f"DEBUG: Ciudad y País del Comercio: '{ciudad_pais_comercio}'\n")

        # Lógica de sobrepaso de presupuesto (sin cambios, pero se mantiene)
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
            "monto": float(monto), # Aseguramos que sea float para Notion
            "comercio": comercio,
            "fecha_transaccion": fecha_transaccion,
            "sobrepaso_ppto": sobrepaso_ppto,
            "comentario": comentario,
            # --- Nuevos campos en el JSON de respuesta ---
            "tarjeta": tarjeta,
            "ultimos_4_digitos": ultimos_4_digitos,
            "numero_autorizacion": numero_autorizacion,
            "tipo_transaccion": tipo_transaccion,
            "ciudad_pais_comercio": ciudad_pais_comercio
        }

        sys.stderr.write(f"DEBUG: Datos parseados para Make: {response_data}\n")

        return jsonify(response_data), 200

    except Exception as e:
        sys.stderr.write(f"!!! ERROR FATAL EN LA APLICACIÓN PYTHON: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500

if __name__ == '__main__':
    # Esto es solo para depuración local si lo corres directamente. Railway usa Gunicorn.
    app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT', 5000))
