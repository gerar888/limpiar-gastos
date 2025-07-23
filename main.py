from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/limpiar", methods=["POST"])
def limpiar():
    data = request.get_json()
    texto = data.get("texto", "")
    
    # Procesamiento de prueba (luego lo cambiás por lo tuyo)
    limpio = texto.upper()

    return jsonify({"texto_limpio": limpio})
#mejora: limpieza robusta de texto
