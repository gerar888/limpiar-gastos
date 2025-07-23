from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["POST"])
def limpiar_texto():
    data = request.get_json()
    texto = data.get("texto", "")

    # Acá podés limpiar o extraer lo que ocupás, ejemplo:
    resultado = {
        "comercio": "bac credomatic" if "bac" in texto else None,
        "monto": "2100" if "2.100" in texto else None,
        "fecha": "21/07/2025" if "21/07/2025" in texto else None
    }

    return jsonify(resultado)

# Importante: NO pongás app.run()
#mejora: limpieza robusta de texto
