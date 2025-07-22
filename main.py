from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route("/", methods=["POST"])
def limpiar_texto():
    data = request.get_json()
    texto_original = data.get("texto", "")

    # Limpieza más robusta
    texto_limpio = re.sub(r'\s+', ' ', texto_original)
    texto_limpio = texto_limpio.strip()
    texto_limpio = texto_limpio.lower()

    return jsonify({
        "original": texto_original,
        "limpio": texto_limpio
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

mejora: limpieza robusta de texto
