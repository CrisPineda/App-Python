from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "API funcionando en Azure 🚀 con GitHub Actions"

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    return jsonify({
        "status": "ok",
        "input": data
    })
