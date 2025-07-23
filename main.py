from flask import Flask, request, jsonify
import re

app = Flask(__name__)

@app.route("/", methods=["POST"])
def extraer_datos():
    data = request.get_json()
    texto = data.get("texto", "")

    # Limpieza básica
    texto = re.sub(r'\s+', ' ', texto.replace('\n', ' ')).strip()

    # Regex para las variables
    comercio = re.search(r"(?<=Comercio: ).*?(?= Ciudad| País| Fecha)", texto)
    ciudad_pais = re.search(r"(?<=Ciudad/Pais: ).*?(?= Fecha)", texto)
    fecha = re.search(r"(?<=Fecha: )\d{2}/\d{2}/\d{4}", texto)
    monto_moneda = re.search(r"(?<=Monto: )([\d,\.]+)\s*(CRC|USD|EUR|₡|\$)", texto)
    tipo_transaccion = re.search(r"(?<=Tipo de Transacción: ).*?(?= Autorización| Código)", texto)
    autorizacion = re.search(r"(?<=Autorización: )\d+", texto)
    referencia = re.search(r"(?<=Referencia: )\d+", texto)

    # Parseo seguro
    resultado = {
        "comercio": comercio.group() if comercio else None,
        "ciudad_pais": ciudad_pais.group() if ciudad_pais else None,
        "fecha": fecha.group() if fecha else None,
        "monto": monto_moneda.group(1).replace(',', '') if monto_moneda else None,
        "moneda": monto_moneda.group(2) if monto_moneda else None,
        "tipo_transaccion": tipo_transaccion.group() if tipo_transaccion else None,
        "autorizacion": autorizacion.group() if autorizacion else None,
        "referencia": referencia.group() if referencia else None,
    }

    return jsonify(resultado)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

#mejora: limpieza robusta de texto
