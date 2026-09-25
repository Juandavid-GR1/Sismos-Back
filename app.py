from flask import Flask
from flask_cors import CORS

# ---------------------------------------------------------
# Controllers existentes
# ---------------------------------------------------------

from src.presentation.controllers.EstacionesController import station_bp
from src.presentation.controllers.SismosController import sismo_bp

from src.presentation.controllers.ReportesController import (
    register_reporte_routes
)

from src.presentation.controllers.ZonaController import (
    register_zona_routes
)

# ---------------------------------------------------------
# Repositorios
# ---------------------------------------------------------

from src.dataaccess.repository.SismoJsonRepository import (
    SismoJsonRepository
)

from src.dataaccess.repository.ZonaRepository import (
    ZonaRepository
)

# ---------------------------------------------------------
# Services
# ---------------------------------------------------------

from src.business.services.SismosService import (
    SismoService
)

from src.business.services.reporte_service import (
    ReporteService
)

from src.business.services.ZonaService import (
    ZonaService
)

# ---------------------------------------------------------
# Algoritmos
# ---------------------------------------------------------

from src.business.algortimos.sismos.Priority_Key_sismo import (
    PriorityKeyService
)


app = Flask(__name__)

CORS(app)


# =========================================================
# REPOSITORIOS
# =========================================================

sismo_repository = SismoJsonRepository()

zona_repository = ZonaRepository(
    "zonas.json"
)


# =========================================================
# SERVICES
# =========================================================

sismo_service = SismoService(
    sismo_repository
)

priority_key_service = PriorityKeyService()

zona_service = ZonaService(
    zona_repository
)

reporte_service = ReporteService(
    sismo_service=sismo_service,
    priority_key_service=priority_key_service,
    zona_service=zona_service
)


# =========================================================
# REGISTRO DE BLUEPRINTS EXISTENTES
# =========================================================

# Estaciones
app.register_blueprint(station_bp)

# Sismos
app.register_blueprint(sismo_bp)


# =========================================================
# REGISTRO DE RUTAS CON INYECCIÓN DE DEPENDENCIAS
# =========================================================

# Reportes
register_reporte_routes(
    app,
    reporte_service
)

# Zonas
register_zona_routes(
    app,
    zona_service
)


# =========================================================
# RUTA PRINCIPAL
# =========================================================

@app.route("/")
def home():
    return "Servidor Flask corriendo correctamente"


# =========================================================
# EJECUCIÓN
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000
    )