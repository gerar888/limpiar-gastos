from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/limpiar", methods=["POST"])
def limpiar():
    data = request.get_json()
    texto = data.get("texto", "")

    # Ejemplo de extracción (muy simple para no fallar)
    if "por" in texto:
        monto = texto.split("por")[1].split(" ")[0]
    else:
        monto = "no encontrado"

    return jsonify({
        "monto_extraido": monto
    })

if __name__ == "__main__":
    app.run(debug=True)
#mejora: limpieza robusta de texto
