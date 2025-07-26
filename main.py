from flask import Flask, request, jsonify
import re
import sys
import os
import urllib.parse

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
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
        nombre_gasto = "Desconocido" # Se mantendrá "Desconocido" por ahora, si no hay un patrón claro para un "nombre de gasto" distinto al "comercio".
                                      # Si quieres que 'nombre_gasto' sea lo mismo que 'comercio', lo asignaremos al final.
        moneda = "N/A"
        monto = 0.00 
        comercio = "Desconocido" # Ahora será más inteligente
        fecha_transaccion = "Fecha Desconocida"
        tarjeta = "Desconocida"
        ultimos_4_digitos = "N/A"
        numero_autorizacion = "N/A"
        tipo_transaccion = "Desconocido"
        ciudad_pais_comercio = "Desconocida"

        # --- EXTRACCIÓN DEL MONTO Y MONEDA ---
        monto_match = re.search(
            r'(?:Monto:\s*)?' 
            r'(USD|CRC|EUR|ARS|MXN|BRL|GTQ|HNL|NIO|PAB|DOP|CLP|COP|PEN|PYG|UYU|VES|BOB|GYD|SRD|XCD|[$€£])' 
            r'\s*' 
            r'([\d\.,]+)', 
            text_to_parse, re.IGNORECASE
        )
        
        original_monto_str_raw = "" # Guardar el string original para la lógica de multiplicación
        if monto_match:
            moneda_identificada = monto_match.group(1).upper()
            original_monto_str_raw = monto_match.group(2) # Guarda el string original capturado
            monto_str_processed = original_monto_str_raw # Variable para trabajar con ella

            if moneda_identificada == '$':
                moneda = 'USD'
            elif moneda_identificada == '€':
                moneda = 'EUR'
            elif moneda_identificada == 'CRC':
                moneda = 'CRC'
            else: 
                moneda = moneda_identificada

            # Lógica de limpieza y conversión del monto a float, específica por moneda.
            if moneda == 'USD':
                monto_str_processed = monto_str_processed.replace(',', '') # Quita comas de miles para USD
            elif moneda == 'CRC':
                # Regla 1: Si hay coma, es el decimal (formato CRC estándar: 1.234,56)
                if ',' in monto_str_processed:
                    monto_str_processed = monto_str_processed.replace('.', '') # Quita los puntos de miles
                    monto_str_processed = monto_str_processed.replace(',', '.') # Cambia coma decimal por punto decimal
                # Regla 2: Si NO hay coma, pero hay puntos. Esto puede ser un entero (123.456) o un decimal mal puesto (26.25 para 26250)
                elif '.' in monto_str_processed:
                    parts = monto_str_processed.split('.')
                    # Si el último segmento tiene 1 o 2 dígitos, y es un CRC, es muy probable que sea un formato "decimal" incorrecto
                    # que en realidad es un número entero con punto de miles mal colocado, o que se esperaba un número mayor.
                    if len(parts[-1]) <= 2: 
                        monto_str_processed = monto_str_processed.replace('.', '') # Elimina todos los puntos. Ej: "26.25" -> "2625"
                    else: # Si el último segmento tiene 3 o más dígitos después del punto (ej. 123.456), asumimos que el punto es un separador de miles y lo quitamos
                          # Esto es para casos como "123.456" que debería ser "123456"
                        monto_str_processed = monto_str_processed.replace('.', '')
                # Regla 3: Si no hay puntos ni comas (ej. "26250"), se deja tal cual.
                # monto_str_processed ya tiene el valor original si no hubo puntos/comas
            
            try:
                monto = float(monto_str_processed)
            except ValueError:
                sys.stderr.write(f"ADVERTENCIA: No se pudo convertir el monto '{monto_str_processed}' a float. Estableciendo a 0.00.\n")
                monto = 0.00 

            # --- LÓGICA DE MULTIPLICACIÓN POR 1000 PARA COLONES (CRC) ---
            # Solo aplica si la moneda es CRC y el monto es "sospechosamente" bajo
            # Y si el string original contenía un punto y los dígitos después eran 1 o 2 (ej. 26.25)
            if moneda == 'CRC' and monto < 1000 and '.' in original_monto_str_raw:
                parts = original_monto_str_raw.split('.')
                if len(parts[-1]) <= 2: # Si el último segmento después del punto tiene 1 o 2 dígitos
                    sys.stderr.write(f"DEBUG: Monto CRC '{original_monto_str_raw}' (extraído como {monto}) parece ser un valor bajo. Multiplicando por 1000.\n")
                    monto = monto * 1000.0
                    sys.stderr.write(f"DEBUG: Nuevo monto CRC: {monto}\n")


        # --- EXTRACCIÓN DEL COMERCIO ---
        # Patrón flexible para "Comercio: [Nombre]" o frases similares.
        # Captura el nombre que puede contener letras, números, espacios, puntos, guiones y ampersands (&).
        comercio_match = re.search(
            r'(?:Comercio|Compra en|Movimiento en|Transacción en):\s*([A-Za-z0-9\s\.\-&]+)', 
            text_to_parse, re.IGNORECASE
        )
        if comercio_match:
            comercio_raw = comercio_match.group(1).strip()
            
            # --- Ajuste para el nombre del comercio / nombre_gasto: Capturar todo delante de "Ciudad" ---
            # Si "Ciudad" está en el nombre del comercio, la RegEx busca "Ciudad" y captura lo que haya antes.
            ciudad_split_match = re.search(r'(.+?)\s+Ciudad', comercio_raw, re.IGNORECASE)
            if ciudad_split_match:
                comercio = ciudad_split_match.group(1).strip()
            else:
                comercio = comercio_raw # Si no encuentra "Ciudad", usa el nombre completo extraído.
            
            # Asignar a nombre_gasto también si es lo que deseas
            nombre_gasto = comercio 
        
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
            "nombre_gasto": nombre_gasto, # Ahora se asigna lo que se extrae para comercio
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
