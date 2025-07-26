from flask import Flask, request, jsonify
import re
import sys
import os # Importar para obtener el puerto
import urllib.parse 

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        # --- DEBUG: Impresión del contenido de la solicitud (RAW y JSON) ---
        raw_data = request.data.decode('utf-8', errors='ignore')
        sys.stderr.write(f"--- DEBUG RAW DATA RECEIVED ---\n")
        sys.stderr.write(f"Raw Request Data: {raw_data}\n")
        sys.stderr.write(f"--- END RAW DATA ---\n")

        request_json = None
        try:
            request_json = request.get_json(silent=True)
        except Exception as json_error:
            sys.stderr.write(f"ERROR al intentar parsear JSON: {json_error}\n")
            sys.stderr.write(f"Data that caused JSON parsing error: {request.data}\n")

        if request_json is None:
            sys.stderr.write("ERROR: Request body was not valid JSON or was empty. Attempting to process raw data as plain text.\n")
            text_to_parse = raw_data
        else:
            text_field = request_json.get('text')
            if text_field:
                text_to_parse = urllib.parse.unquote(text_field)
                sys.stderr.write(f"DEBUG: 'text' field from JSON (decoded): {text_to_parse[:500]}...\n")
            else:
                sys.stderr.write("ERROR: JSON was parsed, but 'text' field is missing or empty.\n")
                return jsonify({"status": "error", "message": "JSON parsed but 'text' field missing"}), 400

        # --- Inicialización de variables de extracción ---
        nombre_gasto = "Desconocido"
        moneda = "N/A"
        monto = 0.00 # Inicializar como float
        comercio = "Desconocido" 
        fecha_transaccion = "Fecha Desconocida"
        tarjeta = "Desconocida"
        ultimos_4_digitos = "N/A"
        numero_autorizacion = "N/A"
        tipo_transaccion = "Desconocido"
        ciudad_pais_comercio = "Desconocida"

        # --- EXTRACCIÓN DEL MONTO Y MONEDA ---
        # RegEx para capturar la moneda y el valor.
        # Es flexible para "Monto: ", moneda/símbolo, y el número con puntos y/o comas.
        monto_match = re.search(
            r'(?:Monto:\s*)?' 
            r'(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD|[$€£])' 
            r'\s*' 
            r'([\d\.,]+)', # Captura el número con puntos y/o comas
            text_to_parse, re.IGNORECASE
        )
        
        if monto_match:
            moneda_identificada = monto_match.group(1).upper()
            monto_str_raw = monto_match.group(2)

            # Estandarizar la moneda a un código ISO
            if moneda_identificada == '$':
                moneda = 'USD'
            elif moneda_identificada == '€':
                moneda = 'EUR'
            elif moneda_identificada == 'CRC':
                moneda = 'CRC'
            else: 
                moneda = moneda_identificada

            # Lógica de limpieza y conversión del monto a float, específica por moneda.
            monto_cleaned = monto_str_raw
            if moneda == 'USD':
                # Para USD: Asumimos punto como decimal. Si hay comas, son miles (ej. 1,234.56). Quitar comas.
                monto_cleaned = monto_str_raw.replace(',', '')
            elif moneda == 'CRC':
                # Para CRC (Costa Rica): Coma (,) para decimales y punto (.) para miles.
                # Ejemplos: 26.250,00 CRC, 26,25 CRC, 26250 CRC (sin decimales)

                # Prioridad 1: Si hay coma, asumimos formato con coma decimal (ej. 1.234,56)
                if ',' in monto_str_raw:
                    monto_cleaned = monto_str_raw.replace('.', '') # Quita los puntos de miles
                    monto_cleaned = monto_cleaned.replace(',', '.') # Cambia la coma decimal por punto decimal para Python
                # Prioridad 2: Si no hay coma, pero hay puntos (ej. 26.25, o 26.250 sin coma)
                # y el número DESPUÉS del último punto tiene 1 o 2 dígitos, asumimos que el punto era separador de miles
                # (o un error donde el punto fue un decimal y se omitieron los miles)
                # Esto es para casos como "26.25" que en realidad debe ser "26250".
                elif '.' in monto_str_raw:
                    # Dividir por el punto para ver la parte decimal
                    parts = monto_str_raw.split('.')
                    # Si el último segmento tiene 1 o 2 dígitos, es probable que el punto sea un separador de miles mal puesto.
                    # Ej: "26.25" -> parts = ["26", "25"]. len("25") es 2.
                    # Ej: "2.2" -> parts = ["2", "2"]. len("2") es 1.
                    if len(parts[-1]) <= 2: 
                        monto_cleaned = monto_str_raw.replace('.', '') # Elimina todos los puntos. Ej: "26.25" -> "2625"
                    else: # Si tiene más de 2 dígitos, asumimos que es un número con punto decimal o punto de miles.
                          # Ej: "123.456" - puede ser 123.456 (USD) o 123456 (CRC sin coma)
                          # Para CRC sin coma y puntos, asumimos que los puntos son separadores de miles y los eliminamos
                          # Si fuera 26.00, se convertiría a 2600. Necesitamos el log para afinar más.
                        monto_cleaned = monto_str_raw.replace('.', '')
                else: 
                    # Si no hay puntos ni comas (ej. "26250"), se deja tal cual.
                    monto_cleaned = monto_str_raw
            else: # Para otras monedas (por defecto como USD, punto decimal)
                monto_cleaned = monto_str_raw.replace(',', '') 
            
            try:
                monto = float(monto_cleaned)
            except ValueError:
                sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{monto_cleaned}' a float. Estableciendo a 0.00.\n")
                monto = 0.00 

        # --- EXTRACCIÓN DEL COMERCIO ---
        # Patrón flexible que busca la etiqueta "Comercio:" o frases similares.
        # Captura el nombre que puede contener letras, números, espacios, puntos, guiones y ampersands (&).
        comercio_match = re.search(
            r'(?:Comercio|Compra en|Movimiento en|Transacción en):\s*([A-Za-z0-9\s\.\-&]+)', 
            text_to_parse, re.IGNORECASE
        )
        if comercio_match:
            comercio = comercio_match.group(1).strip()
        
        # --- EXTRACCIÓN DE FECHA DE TRANSACCIÓN ---
        fecha_transaccion_match = re.search(
            r'Fecha:\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{1,2}\s+(?:de)?\s+[A-Za-záéíóúÁÉÍÓÚñÑ]+\s*(?:de)?\s*\d{2,4})', 
            text_to_parse, re.IGNORECASE
        )
        if fecha_transaccion_match:
            fecha_transaccion = fecha_transaccion_match.group(1).strip()

        # --- EXTRACCIÓN DE TARJETA Y ÚLTIMOS 4 DÍGITOS ---
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

        # --- EXTRACCIÓN DE NÚMERO DE AUTORIZACIÓN ---
        autorizacion_match = re.search(
            r'(?:No\.?\s*Autorización|Autorización No?\.?|Código de Autorización|Auth Code):\s*(\w+)', 
            text_to_parse, re.IGNORECASE
        )
        if autorizacion_match:
            numero_autorizacion = autorizacion_match.group(1).strip()

        # --- EXTRACCIÓN DE TIPO DE TRANSACCIÓN ---
        tipo_transaccion_match = re.search(
            r'(?:Tipo:\s*)(Compra|Retiro|Débito|Crédito|Pago|Transacción)', 
            text_to_parse, re.IGNORECASE
        )
        if tipo_transaccion_match:
            tipo_transaccion = tipo_transaccion_match.group(1).strip()

        # --- Lógica de sobrepaso_ppto ---
        sobrepaso_ppto = False
        if isinstance(monto, (int, float)):
            if moneda == "USD":
                if monto > 50.00:
                    sobrepaso_ppto = True
            elif moneda == "CRC":
                if monto > 30000.00: 
                    sobrepaso_ppto = True
        else: 
            sys.stderr.write(f"ADVERTENCIA: Monto no es numérico para cálculo de presupuesto ({monto}). Asumiendo False.\n")
            sobrepaso_ppto = False

        # --- Generación del Comentario ---
        comentario = f"Transacción de {comercio} por {moneda} {monto:.2f}." 
        if tarjeta != "Desconocida" and ultimos_4_digitos != "N/A":
            comentario += f" (Tarjeta: {tarjeta} ****{ultimos_4_digitos})."
        if tipo_transaccion != "Desconocido":
            comentario += f" Tipo: {tipo_transaccion}."
        if numero_autorizacion != "N/A":
            comentario += f" Autorización: {numero_autorizacion}."
        if ciudad_pais_comercio != "Desconocida":
            comentario += f" Ubicación: {ciudad_pais_comercio}."

        # --- Preparación de la Respuesta JSON ---
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
