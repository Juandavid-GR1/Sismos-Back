from flask import Flask
from flask_cors import CORS

# Repositorios y Persistencia
from src.dataaccess.repository.JsonColasRepository import ColaJsonPersistencia
from src.dataaccess.repository.SismoJsonRepository import SismoJsonRepository
from src.dataaccess.repository.ZonaRepository import ZonaRepository

# Algoritmos y Servicios
from src.business.algortimos.sismos.Priority_Key_sismo import PriorityKeyService
from src.business.services.cola_reportes import ColaReportesService
from src.business.services.ModoAutomaticoService import ModoAutomaticoService
from src.business.services.reporte_service import ReporteService
from src.business.services.SismosService import SismoService
from src.business.services.ZonaService import ZonaService

# Controladores y Rutas
from src.presentation.controllers.EstacionesController import station_bp
from src.presentation.controllers.ReportesController import register_reporte_routes
from src.presentation.controllers.SismosController import sismo_bp
from src.presentation.controllers.ZonaController import register_zona_routes

app = Flask(__name__)
CORS(app)


# =========================================================
# REPOSITORIOS Y PERSISTENCIA
# =========================================================

sismo_repository = SismoJsonRepository()
zona_repository = ZonaRepository("zonas.json")
cola_persistencia = ColaJsonPersistencia("data/reportes_cola.json")


# =========================================================
# SERVICIOS
# =========================================================

sismo_service = SismoService(sismo_repository)
priority_key_service = PriorityKeyService()
zona_service = ZonaService(zona_repository)

reporte_service = ReporteService(
    sismo_service=sismo_service,
    priority_key_service=priority_key_service,
    zona_service=zona_service,
)

cola_reportes = ColaReportesService(persistencia=cola_persistencia)

modo_automatico_service = ModoAutomaticoService(
    cola_reportes=cola_reportes,
    reporte_service=reporte_service,
)


# =========================================================
# REGISTRO DE BLUEPRINTS Y RUTAS
# =========================================================

# Blueprints directos
app.register_blueprint(station_bp)
app.register_blueprint(sismo_bp)

# Rutas con inyección de dependencias
register_reporte_routes(app, reporte_service, cola_reportes, modo_automatico_service)
register_zona_routes(app, zona_service)


# =========================================================
# RUTAS BÁSICAS Y EJECUCIÓN
# =========================================================

@app.route("/")
def home():
    return "Servidor Flask corriendo correctamente"


if __name__ == "__main__":
    app.run(debug=True, port=5000)