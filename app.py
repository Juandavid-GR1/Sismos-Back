from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permite peticiones desde React

@app.route('/')
def home():
    return "Servidor Flask corriendo correctamente"

if __name__ == '__main__':
    app.run(debug=True, port=5000)