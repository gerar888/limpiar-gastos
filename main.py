from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "API is running"

@app.route("/limpiar", methods=["POST"])
def limpiar():
    data = request.json
    texto = data.get("texto", "")
    
    # Aquí va la lógica para limpiar el texto, por ahora simple
    respuesta = {
        "texto_original": texto,
        "limpio": texto.upper()  # reemplazá esto por tu limpieza real
    }
    return jsonify(respuesta)
#mejora: limpieza robusta de texto
