from flask import Flask, request, jsonify
import re
import sys
import os # Importar para obtener el puerto

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        # --- DEBUG: Impresión del contenido de la solicitud ---
        raw_data = request.data.decode('utf-8', errors='ignore')
        sys.stderr.write(f"--- DEBUG RAW DATA RECEIVED ---\n")
        sys.stderr.write(f"Raw Request Data: {raw_data}\n")
        sys.stderr.write(f"--- END RAW DATA ---\n")

        request_json = None
        try:
            request_json = request.get_json(silent=True) # silent=True para evitar errores si no es JSON o si es inválido
        except Exception as json_error:
            sys.stderr.write(f"ERROR al intentar parsear JSON: {json_error}\n")
            sys.stderr.write(f"Data that caused JSON parsing error: {request.data}\n")

        if request_json is None:
            sys.stderr.write("ERROR: Request body was not valid JSON or was empty. Attempting to process raw data as plain text.\n")
            text_to_parse = raw_data # Debería ser un JSON, pero si falla, procesamos el raw_data
        else:
            text_field = request_json.get('text')
            if text_field:
                # Ya sabemos por pruebas anteriores que Make no envía urlEncoded si no se lo pedimos con una función.
                # Mantengo un unquote por si acaso, es inofensivo si no está codificado.
                text_to_parse = urllib.parse.unquote(text_field)
                sys.stderr.write(f"DEBUG: 'text' field from JSON (decoded): {text_to_parse[:500]}...\n")
            else:
                sys.stderr.write("ERROR: JSON was parsed, but 'text' field is missing or empty.\n")
                return jsonify({"status": "error", "message": "JSON parsed but 'text' field missing"}), 400

        # --- Inicialización de variables de extracción ---
        nombre_gasto = "Desconocido"
        moneda = "N/A"
        monto = 0.00 # Inicializar como float para evitar problemas
        comercio = "Desconocido" 
        fecha_transaccion = "Fecha Desconocida"
        tarjeta = "Desconocida"
        ultimos_4_digitos = "N/A"
        numero_autorizacion = "N/A"
        tipo_transaccion = "Desconocido"
        ciudad_pais_comercio = "Desconocida"

        # --- EXTRACCIÓN DEL MONTO Y MONEDA ---
        # Patrón para encontrar "Monto: USD 26.36" o "Monto: CRC 1.234,56"
        # Captura la divisa (USD, CRC, etc. o símbolos $€£) y el número con sus puntos/comas
        monto_match = re.search(
            r'(?:Monto:\s*)?' # "Monto: " (opcional)
            r'(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD|[$€£])' # Grupo 1: Moneda/Símbolo
            r'\s*' # Espacio
            r'([\d\.,]+)', # Grupo 2: El número con puntos y/o comas
            text_to_parse, re.IGNORECASE
        )
        
        if monto_match:
            moneda_identificada = monto_match.group(1).upper()
            monto_str_raw = monto_match.group(2)

            # Estandarizar la moneda al código ISO (USD, CRC, EUR)
            if moneda_identificada == '$':
                moneda = 'USD'
            elif moneda_identificada == '€':
                moneda = 'EUR'
            elif moneda_identificada == 'CRC':
                moneda = 'CRC'
            else: # Si ya es 'USD', 'EUR', etc.
                moneda = moneda_identificada

            # Lógica de limpieza y conversión del monto a float
            # Elimina separadores de miles y ajusta el decimal para Python (que usa punto)
            if moneda == 'USD':
                # Para USD, asumimos punto decimal, y si hay comas, son miles (ej. 1,234.56 USD). Quitar comas.
                monto_cleaned = monto_str_raw.replace(',', '')
            elif moneda == 'CRC':
                # Para CRC, asumimos coma decimal y punto de miles (ej. 1.234,56 CRC). Quitar puntos de miles y cambiar coma por punto.
                monto_cleaned = monto_str_raw.replace('.', '').replace(',', '.')
            else: 
                # Para otras monedas, asumimos punto decimal y quitamos comas (ej. 1,234.56)
                monto_cleaned = monto_str_raw.replace(',', '') 
            
            try:
                monto = float(monto_cleaned)
            except ValueError:
                sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{monto_cleaned}' a float.\n")
                monto = 0.00 # Resetear a 0.00 si falla la conversión

        # --- EXTRACCIÓN DEL COMERCIO ---
        # Patrón que busca "Comercio: [Nombre]"
        # El nombre del comercio puede contener letras, números, espacios, puntos y guiones.
        comercio_match = re.search(
            r'(?:Comercio|Compra en|Movimiento en|Transacción en):\s*([A-Za-z0-9\s\.\-]+)', 
            text_to_parse, re.IGNORECASE
        )
        if comercio_match:
            comercio = comercio_match.group(1).strip()
        
        # --- EXTRACCIÓN DE FECHA DE TRANSACCIÓN ---
        # Patrón para formatos como "25/07/2025" o "25-07-2025" o "25 de Julio, 2025"
        fecha_transaccion_match = re.search(
            r'Fecha:\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{1,2}\s+(?:de)?\s+[A-Za-záéíóúÁÉÍÓÚñÑ]+\s*(?:de)?\s*\d{2,4})', 
            text_to_parse, re.IGNORECASE
        )
        if fecha_transaccion_match:
            fecha_transaccion = fecha_transaccion_match.group(1).strip()

        # --- EXTRACCIÓN DE TARJETA Y ÚLTIMOS 4 DÍGITOS ---
        # Patrón para "Tarjeta: VISA ****1234"
        tarjeta_match = re.search(
            r'(?:Tarjeta|Medio de Pago):\s*([A-Za-z]+)(?:\s*\**(\d{4}))?', # Captura el tipo y los últimos 4 dígitos
            text_to_parse, re.IGNORECASE
        )
        if tarjeta_match:
            tarjeta = tarjeta_match.group(1).upper()
            if tarjeta_match.group(2): # Si se capturaron los últimos 4 dígitos
                ultimos_4_digitos = tarjeta_match.group(2)
            else:
                ultimos_4_digitos = "N/A" # Asegura que esté N/A si no se encuentran

        # --- EXTRACCIÓN DE NÚMERO DE AUTORIZACIÓN ---
        # Patrón para "Autorización: 123456"
        autorizacion_match = re.search(
            r'(?:No\.?\s*Autorización|Autorización No?\.?|Código de Autorización|Auth Code):\s*(\w+)', 
            text_to_parse, re.IGNORECASE
        )
        if autorizacion_match:
            numero_autorizacion = autorizacion_match.group(1).strip()

        # --- EXTRACCIÓN DE TIPO DE TRANSACCIÓN ---
        # Patrón para "Tipo: Compra"
        tipo_transaccion_match = re.search(
            r'(?:Tipo:\s*)(Compra|Retiro|Débito|Crédito|Pago|Transacción)', 
            text_to_parse, re.IGNORECASE
        )
        if tipo_transaccion_match:
            tipo_transaccion = tipo_transaccion_match.group(1).strip()

        # --- Lógica de sobrepaso_ppto ---
        sobrepaso_ppto = False
        try:
            if moneda == "USD":
                if monto > 50.00:
                    sobrepaso_ppto = True
            elif moneda == "CRC":
                if monto > 30000.00:
                    sobrepaso_ppto = True
        except TypeError: # Si monto no fue un número
            sys.stderr.write(f"ADVERTENCIA: Monto no es numérico para cálculo de presupuesto: {monto}. Asumiendo False.\n")
            sobrepaso_ppto = False

        # --- Generación del Comentario ---
        comentario = f"Transacción de {comercio} por {moneda} {monto:.2f}." # Formatear monto a 2 decimales
        if tarjeta != "Desconocida" and ultimos_4_digitos != "N/A":
            comentario += f" (Tarjeta: {tarjeta} ****{ultimos_4_digitos})."
        if tipo_transaccion != "Desconocido":
            comentario += f" Tipo: {tipo_transaccion}."
        if numero_autorizacion != "N/A":
            comentario += f" Autorización: {numero_autorizacion}."
        if ciudad_pais_comercio != "Desconocida": # Si logras extraer esto, lo añadiría.
            comentario += f" Ubicación: {ciudad_pais_comercio}."

        # --- Preparación de la Respuesta JSON ---
        response_data = {
            "nombre_gasto": nombre_gasto,
            "moneda": moneda,
            "monto": monto, # Ya es float
            "comercio": comercio,
            "fecha_transaccion": fecha_transaccion,
            "sobrepaso_ppto": sobrepaso_ppto,
            "comentario": comentario,
            "tarjeta": tarjeta,
            "ultimos_4_digitos": ultimos_4_digitos,
            "numero_autorizacion": numero_autorizacion,
            "tipo_transaccion": tipo_transaccion,
            "ciudad_pais_comercio": ciudad_pais_comercio # Si no se extrae, seguirá siendo "Desconocida"
        }

        sys.stderr.write(f"DEBUG: Final response data: {response_data}\n")
        return jsonify(response_data), 200

    except Exception as e:
        sys.stderr.write(f"!!! ERROR FATAL EN LA APLICACIÓN PYTHON: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr) # Imprime el stack trace completo al stderr
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000)) # Obtiene el puerto de la variable de entorno, o usa 5000
    app.run(debug=True, host='0.0.0.0', port=port)
