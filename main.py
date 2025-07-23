from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route("/", methods=["POST"])
def limpiar_texto():
    data = request.get_json()
    texto = data.get("texto", "")

    # Expresiones regulares para extraer variables
    comercio = re.search(r"compra en (.*?) \*{4}", texto)
    moneda = re.search(r"por (\D{1,3})\d", texto)
    monto = re.search(r"por [^\d]*([\d.,]+)", texto)
    fecha = re.search(r"el (\d{2}/\d{2}/\d{4})", texto)
    ciudad_pais = re.search(r"en (.*?) \*{4}", texto)

    resultado = {
        "autorizacion": None,
        "ciudad_pais": ciudad_pais.group(1) if ciudad_pais else None,
        "comercio": comercio.group(1) if comercio else None,
        "fecha": fecha.group(1) if fecha else None,
        "moneda": moneda.group(1) if moneda else None,
        "monto": monto.group(1).replace(".", "").replace(",", ".") if monto else None,
        "referencia": None,
        "tipo_transaccion": None
    }

    return jsonify(resultado)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
#mejora: limpieza robusta de texto
