from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "La API está funcionando 🚀"

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    # aquí deberías hacer la llamada a tu modelo en Azure ML o lógica de predicción
    return jsonify({"resultado": "OK", "datos": data})
