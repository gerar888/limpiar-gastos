from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route("/limpiar", methods=["POST"])
def limpiar():
    try:
        data = request.get_json()
        texto = data.get("texto", "")

        # Tu lógica de extracción:
        comercio = re.search(r"compra en (.+?) \*\*\*\*", texto)
        ciudad = re.search(r"en ([A-Za-z\s]+) el", texto)
        fecha = re.search(r"el (\d{2}/\d{2}/\d{4})", texto)
        monto = re.search(r"por (₡|¢)?([\d.,]+)", texto)

        return jsonify({
            "comercio": comercio.group(1) if comercio else None,
            "ciudad": ciudad.group(1) if ciudad else None,
            "fecha": fecha.group(1) if fecha else None,
            "monto": monto.group(2) if monto else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#mejora: limpieza robusta de texto
