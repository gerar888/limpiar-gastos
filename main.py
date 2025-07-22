
from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route("/", methods=["POST"])
def limpiar_texto():
    data = request.get_json()
    texto_original = data.get("texto", "")
    
    # Ejemplo de limpieza básica:
    texto_limpio = re.sub(r'\s+', ' ', texto_original.replace('\n', ' ')).strip()

    return jsonify({
        "original": texto_original,
        "limpio": texto_limpio
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

