from flask import Flask, request, jsonify
import re
import sys
import os # Importar para obtener el puerto
import urllib.parse # Necesitas esta importación para urllib.parse.unquote

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
                # Se mantiene unquote por si Make decidiera codificar, es inofensivo si no lo hace.
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
        # Captura: [Moneda/Símbolo] [Espacios] [Número con puntos/comas/decimales]
        monto_match = re.search(
            r'(?:Monto:\s*)?' # "Monto: " (opcional, para ser más flexible)
            r'(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD|[$€£])' # Grupo 1: Moneda/Símbolo
            r'\s*' # Espacios
            r'([\d\.,]+)', # Grupo 2: El número, que puede tener puntos, comas o ambos.
            text_to_parse, re.IGNORECASE
        )
        
        if monto_match:
            moneda_identificada = monto_match.group(1).upper()
            monto_str_raw = monto_match.group(2)

            # Estandarizar la moneda a un código ISO (USD, CRC, EUR, etc.)
            if moneda_identificada == '$':
                moneda = 'USD'
            elif moneda_identificada == '€':
                moneda = 'EUR'
            elif moneda_identificada == 'CRC':
                moneda = 'CRC'
            else: # Si ya es 'USD', 'EUR', etc.
                moneda = moneda_identificada

            # Lógica de limpieza y conversión del monto a float, específica por moneda.
            monto_cleaned = monto_str_raw
            if moneda == 'USD':
                # Para USD: Asumimos punto como decimal. Si hay comas, son miles (ej. 1,234.56). Quitar comas.
                monto_cleaned = monto_str_raw.replace(',', '')
            elif moneda == 'CRC':
                # Para CRC:
                # Costa Rica usa coma (,) para decimales y punto (.) para miles.
                # Ejemplos: 26.250,00 CRC (veintiséis mil doscientos cincuenta con cero céntimos)
                #           26,25 CRC (veintiséis con veinticinco céntimos)
                #           26250 CRC (veintiséis mil doscientos cincuenta sin decimales indicados)

                if ',' in monto_str_raw: # Si el número contiene una coma, asumimos que es el separador decimal (formato CRC)
                    monto_cleaned = monto_str_raw.replace('.', '') # Quita los puntos de miles
                    monto_cleaned = monto_cleaned.replace(',', '.') # Cambia la coma decimal por punto decimal para Python
                else: # Si no hay coma, podría ser un entero grande o un decimal con punto (USD-like)
                    # En CRC, si no hay coma, es probable un entero sin decimales (ej. 26250)
                    # No hacer ningún replace si no hay coma, a menos que haya puntos (miles USD-like)
                    # Si hay puntos pero no comas, es posible que sea un formato mixto o un entero grande
                    # Para simplificar y cubrir 26250 CRC, si no hay coma, lo dejamos como está.
                    # Si fuera "26.250" sin coma, ya lo manejaría directamente float.
                    monto_cleaned = monto_str_raw # No se hace ningún reemplazo para números enteros sin coma.

            else: # Para otras monedas, por defecto asumimos formato con punto decimal (como USD)
                monto_cleaned = monto_str_raw.replace(',', '') 
            
            try:
                monto = float(monto_cleaned)
            except ValueError:
                sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{monto_cleaned}' a float. Estableciendo a 0.00.\n")
                monto = 0.00 # Resetear a 0.00 si falla la conversión

        # --- EXTRACCIÓN DEL COMERCIO ---
        # Patrón flexible para "Comercio: [Nombre]" o "Compra en [Nombre]"
        # Captura: [Nombre del comercio] que puede contener letras, números, espacios, puntos, guiones y ampersands (&).
        comercio_match = re.search(
            r'(?:Comercio|Compra en|Movimiento en|Transacción en):\s*([A-Za-z0-9\s\.\-&]+)', # Añadido '&' para nombres como "AMZN Mktp US"
            text_to_parse, re.IGNORECASE
        )
        if comercio_match:
            comercio = comercio_match.group(1).strip()
        
        # --- EXTRACCIÓN DE FECHA DE TRANSACCIÓN ---
        # Patrón para formatos comunes de fecha
        fecha_transaccion_match = re.search(
            r'Fecha:\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{1,2}\s+(?:de)?\s+[A-Za-záéíóúÁÉÍÓÚñÑ]+\s*(?:de)?\s*\d{2,4})', 
            text_to_parse, re.IGNORECASE
        )
        if fecha_transaccion_match:
            fecha_transaccion = fecha_transaccion_match.group(1).strip()

        # --- EXTRACCIÓN DE TARJETA Y ÚLTIMOS 4 DÍGITOS ---
        # Patrón para "Tarjeta: VISA ****1234"
        tarjeta_match = re.search(
            r'(?:Tarjeta|Medio de Pago):\s*([A-Za-z]+)(?:\s*\*+(\d{4}))?', # Captura el tipo y los últimos 4 dígitos
            text_to_parse, re.IGNORECASE
        )
        if tarjeta_match:
            tarjeta = tarjeta_match.group(1).upper()
            if tarjeta_match.group(2): # Si se capturaron los últimos 4 dígitos
                ultimos_4_digitos = tarjeta_match.group(2)
            else:
                ultimos_4_digitos = "N/A" 

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
        # Asegúrate de que monto sea un número antes de comparar
        if isinstance(monto, (int, float)):
            if moneda == "USD":
                if monto > 50.00:
                    sobrepaso_ppto = True
            elif moneda == "CRC":
                if monto > 30000.00: # Ajusta este umbral si 30,000 es para el ejemplo
                    sobrepaso_ppto = True
        else: 
            sys.stderr.write(f"ADVERTENCIA: Monto no es numérico para cálculo de presupuesto ({monto}). Asumiendo False.\n")
            sobrepaso_ppto = False

        # --- Generación del Comentario ---
        # Formatear el monto con 2 decimales para el comentario
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
