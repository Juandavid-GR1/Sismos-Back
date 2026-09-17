from flask import Flask
from flask_cors import CORS
from src.controllers.EstacionesController import station_bp

app = Flask(__name__)
CORS(app)  # Habilita CORS para permitir peticiones desde React

# Registrar el Blueprint de estaciones
app.register_blueprint(station_bp)


@app.route("/")
def home():
    return "Servidor Flask corriendo correctamente"


if __name__ == "__main__":
    app.run(debug=True, port=5000)