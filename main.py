from flask import Flask, request, jsonify
import re
import urllib.parse # Necesitas importar esto para url_decode

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        # Imprime el raw data que llega al servidor
        print(f"DEBUG: Request.data (raw): {request.data}") 

        # Intenta obtener el JSON
        request_json = request.get_json(silent=True) # Usa silent=True para no fallar si no es JSON o si es inválido

        # Imprime el JSON parsed
        print(f"DEBUG: Request.json (parsed): {request_json}") 

        if not request_json:
            print("ERROR: Request JSON is empty or invalid.")
            return jsonify({"status": "error", "message": "Invalid JSON or empty JSON"}), 400

        text_received = request_json.get('text')

        if not text_received:
            print("ERROR: 'text' field is empty or null.")
            return jsonify({"status": "error", "message": "'text' field is missing or empty"}), 400

        # Intentar decodificar por si Make hizo algún encoding automático (aunque no sea urlEncode explícito)
        text_to_parse = urllib.parse.unquote(text_received)
        print(f"DEBUG: Decoded text (potentially): {text_to_parse}")

        # Ahora, la parte crucial: manejar manualmente los saltos de línea y otras comillas si siguen apareciendo.
        # Los logs de Railway son los que nos dirán si esto es necesario.
        # Por ahora, mantengamos el enfoque en recibir bien la data.

        # Tu lógica de extracción de datos...
        monto_match = re.search(r'Monto: (\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text_to_parse)
        monto = monto_match.group(1) if monto_match else None

        # ... (otras extracciones de tarjeta, últimos 4 dígitos, etc.)

        response_data = {
            "status": "success",
            "extracted_text_preview": text_to_parse[:200] + "..." if len(text_to_parse) > 200 else text_to_parse,
            "monto_extraido": monto
        }
        return jsonify(response_data), 200

    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
