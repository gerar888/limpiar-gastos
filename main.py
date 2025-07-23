from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route("/", methods=["POST"])
def procesar_texto():
    data = request.get_json()
    texto = data.get("texto", "")

    # Limpieza inicial
    texto = texto.replace('\n', ' ').strip()

    # Extraer tipo de transacción (ej: compra, pago, etc.)
    tipo_transaccion_match = re.search(r"^(compra|pago|retiro|transferencia)", texto, re.IGNORECASE)
    tipo_transaccion = tipo_transaccion_match.group(1).lower() if tipo_transaccion_match else None

    # Extraer monto y moneda
    monto_match = re.search(r"por\s+([₡$€])?([\d.,]+)", texto)
    moneda = monto_match.group(1) if monto_match else None
    monto_raw = monto_match.group(2).replace(".", "").replace(",", ".") if monto_match else None
    monto = float(monto_raw) if monto_raw else None

    # Extraer fecha y hora
    fecha_match = re.search(r"el\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", texto)
    fecha = fecha_match.group(1) if fecha_match else None

    # Extraer comercio y país
    comercio_match = re.search(r"en\s+(.+?)\s+([A-Z]{2})$", texto)
    comercio = comercio_match.group(1).strip() if comercio_match else None
    ciudad_pais = comercio_match.group(2) if comercio_match else None

    return jsonify({
        "autorizacion": None,
        "ciudad_pais": ciudad_pais,
        "comercio": comercio,
        "fecha": fecha,
        "moneda": moneda,
        "monto": monto,
        "referencia": None,
        "tipo_transaccion": tipo_transaccion
    })

if __name__ == "__main__":
    app.run(debug=True)
#mejora: limpieza robusta de texto
