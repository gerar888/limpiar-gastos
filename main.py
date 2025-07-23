from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "API activa"

@app.route("/limpiar", methods=["POST"])
def limpiar():
    data = request.get_json()
    texto = data.get("texto", "")
    
    limpio = texto.upper()  # Lógica de prueba

    return jsonify({"texto_limpio": limpio})
#mejora: limpieza robusta de texto
