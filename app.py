import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

AML_ENDPOINT_URL = os.environ.get("AML_ENDPOINT_URL")
AML_API_KEY = os.environ.get("AML_API_KEY")

# columnas EXACTAS que espera tu endpoint (en ese orden)
COLUMNS = [
    "Pregunta_1",
    "Pregunta 2",
    "Pregunta 3",
    "Pregunta 6",
    "Pregunta 7",
    "Sum_Insuf"
]

@app.get("/health")
def health():
    ok = bool(AML_ENDPOINT_URL and AML_API_KEY)
    return jsonify({"status": "ok" if ok else "misconfigured"}), 200 if ok else 500

@app.post("/predict")
def predict():
    """
    Espera JSON como:
    {
      "Pregunta_1": 3,
      "Pregunta_2": 4,        # Nota: en tu CSV es "Pregunta 2" con espacio.
      "Pregunta_3": 2,        # Para enviar desde frontend, aceptaré ambos formatos.
      "Pregunta_6": 5,
      "Pregunta_7": 3,
      "Sum_Insuf": 17         # opcional: si no viene, se calcula
    }
    """
    if not (AML_ENDPOINT_URL and AML_API_KEY):
        return jsonify({"error": "AML endpoint not configured"}), 500

    try:
        payload_in = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Body must be JSON"}), 400

    # Normalizo claves para aceptar "Pregunta 2" (espacio) o "Pregunta_2" (guion bajo) desde el frontend
    normalized = {}
    for k, v in (payload_in or {}).items():
        k_norm = k.replace("_", " ")
        if k_norm.startswith("Pregunta "):
            normalized[k_norm] = v

    # Mapeo explícito para no depender solo de la normalización
    def get_num(key_with_space, alt_key_with_underscore):
        if key_with_space in payload_in:
            return payload_in[key_with_space]
        if alt_key_with_underscore in payload_in:
            return payload_in[alt_key_with_underscore]
        if key_with_space in normalized:
            return normalized[key_with_space]
        return None

    p1 = get_num("Pregunta_1", "Pregunta_1")
    p2 = get_num("Pregunta 2", "Pregunta_2")
    p3 = get_num("Pregunta 3", "Pregunta_3")
    p6 = get_num("Pregunta 6", "Pregunta_6")
    p7 = get_num("Pregunta 7", "Pregunta_7")

    # Validación básica
    missing = []
    for name, val in [("Pregunta_1", p1), ("Pregunta 2", p2), ("Pregunta 3", p3), ("Pregunta 6", p6), ("Pregunta 7", p7)]:
        if val is None:
            missing.append(name)
    if missing:
        return jsonify({"error": "Missing fields", "missing": missing}), 400

    # Sum_Insuf: si no viene, lo calculo
    sum_in = payload_in.get("Sum_Insuf")
    if sum_in is None:
        try:
            sum_in = float(p1) + float(p2) + float(p3) + float(p6) + float(p7)
        except Exception:
            return jsonify({"error": "Values must be numeric"}), 400

    # Construyo el payload EXACTO que espera el endpoint de Azure ML
    aml_payload = {
        "input_data": {
            "columns": COLUMNS,
            "index": [0],
            "data": [[float(p1), float(p2), float(p3), float(p6), float(p7), float(sum_in)]]
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AML_API_KEY}"
    }

    try:
        resp = requests.post(AML_ENDPOINT_URL, data=json.dumps(aml_payload), headers=headers, timeout=30)
        try:
            out = resp.json()
        except Exception:
            out = {"raw_text": resp.text}
        return jsonify({"status_code": resp.status_code, "prediction": out}), resp.status_code
    except requests.RequestException as e:
        return jsonify({"error": "Failed calling AML endpoint", "detail": str(e)}), 502

# Entry point para gunicorn
if __name__ == "__main__":
    # Solo para correr local: python app.py
    app.run(host="0.0.0.0", port=8000)
