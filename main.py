
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "¡Hola! La API está activa."

@app.route("/procesar", methods=["POST"])
def procesar():
    data = request.get_json()
    texto = data.get("texto", "")
    resultado = texto.upper()
    return jsonify({"resultado": resultado})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
