import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

AML_ENDPOINT_URL = os.environ.get("AML_ENDPOINT_URL")
AML_API_KEY = os.environ.get("AML_API_KEY")

# columnas EXACTAS que espera tu endpoint (en ese orden)
COLUMNS = ["Pregunta_1","Pregunta 2","Pregunta 3","Pregunta 6","Pregunta 7","Sum_Insuf"]

@app.get("/health")
def health():
    ok = bool(AML_ENDPOINT_URL and AML_API_KEY)
    return jsonify({"status": "ok" if ok else "misconfigured"}), 200 if ok else 500

@app.post("/predict")
def predict():
    """
    Espera JSON:
    {
      "Pregunta_1": 3, "Pregunta_2": 4, "Pregunta_3": 2,
      "Pregunta_6": 5, "Pregunta_7": 3,
      "Sum_Insuf": 17  # opcional, si no viene lo calculo
    }
    """
    if not (AML_ENDPOINT_URL and AML_API_KEY):
        return jsonify({"error": "AML endpoint not configured"}), 500

    try:
        body = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"error": "Body must be JSON"}), 400

    def getv(*keys):
        for k in keys:
            if k in body: return body[k]
        return None

    p1 = getv("Pregunta_1","Pregunta 1")
    p2 = getv("Pregunta 2","Pregunta_2")
    p3 = getv("Pregunta 3","Pregunta_3")
    p6 = getv("Pregunta 6","Pregunta_6")
    p7 = getv("Pregunta 7","Pregunta_7")

    missing = [n for n,v in [("Pregunta_1",p1),("Pregunta 2",p2),("Pregunta 3",p3),("Pregunta 6",p6),("Pregunta 7",p7)] if v is None]
    if missing:
        return jsonify({"error":"Missing fields","missing":missing}), 400

    sum_insuf = body.get("Sum_Insuf")
    if sum_insuf is None:
        try:
            sum_insuf = float(p1)+float(p2)+float(p3)+float(p6)+float(p7)
        except Exception:
            return jsonify({"error":"Values must be numeric"}), 400

    aml_payload = {
        "input_data": {
            "columns": COLUMNS,
            "index": [0],
            "data": [[float(p1), float(p2), float(p3), float(p6), float(p7), float(sum_insuf)]]
        }
    }
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {AML_API_KEY}"}

    resp = requests.post(AML_ENDPOINT_URL, data=json.dumps(aml_payload), headers=headers, timeout=30)
    try:
        out = resp.json()
    except Exception:
        out = {"raw": resp.text}
    return jsonify({"status_code": resp.status_code, "prediction": out}), resp.status_code

# mini front para probar desde el navegador
INDEX_HTML = """
<!doctype html><meta charset="utf-8">
<h2>Demo Insuficiencia</h2>
<form id="f">
  <label>P1 <input name="Pregunta_1" type="number" value="3"></label><br>
  <label>P2 <input name="Pregunta_2" type="number" value="4"></label><br>
  <label>P3 <input name="Pregunta_3" type="number" value="2"></label><br>
  <label>P6 <input name="Pregunta_6" type="number" value="5"></label><br>
  <label>P7 <input name="Pregunta_7" type="number" value="3"></label><br>
  <button type="submit">Predecir</button>
</form>
<pre id="out"></pre>
<script>
document.getElementById('f').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  // convierte strings a números
  for (const k in body) body[k] = Number(body[k]);
  const r = await fetch('/predict', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
});
</script>
"""
@app.get("/")
def home():
    return render_template_string(INDEX_HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
