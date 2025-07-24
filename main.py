import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_request():
    try:
        # Estos PRINTS nos dirán qué está llegando y si hay errores.
        print(f"--- NUEVA SOLICITUD RECIBIDA ---")
        print(f"Request Method: {request.method}") # Para confirmar que es POST
        print(f"Request Headers: {request.headers}")
        print(f"Request Body (raw): {request.data}") # Contenido tal cual llega

        # Intentamos parsear el JSON. Si no es JSON, get_json(silent=True) devolverá None
        data = request.get_json(silent=True)
        print(f"Received JSON data (after get_json): {data}") # Debería ser None si el body es texto plano

        # Aquí es donde iría tu lógica para procesar el texto plano del correo.
        # Por ahora, solo devolveremos un mensaje de éxito.
        if request.data:
            # Si el cuerpo no es JSON, es texto plano. Lo decodificamos.
            received_text = request.data.decode('utf-8')
            print(f"Received text data: {received_text}")
            response_message = "Texto recibido y procesado (simulado)."
            response_data = {"text_content": received_text}
        else:
            response_message = "Solicitud recibida, sin cuerpo de texto."
            response_data = {}


        return jsonify({"message": response_message, "received_details": response_data}), 200

    except Exception as e:
        # Si ocurre CUALQUIER error en tu código Python, lo veremos aquí.
        print(f"!!! ERROR EN LA APLICACIÓN PYTHON: {e}")
        import traceback
        traceback.print_exc() # Esto imprimirá el rastro completo del error
        return jsonify({"error": str(e), "message": "Error interno del servidor Python"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    # Esto hace que Flask escuche en todas las interfaces, lo que es necesario en Railway.
    app.run(host='0.0.0.0', port=port)
