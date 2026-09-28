from flask import Flask
from flask_cors import CORS
from datetime import datetime, timedelta

# Repositorios y Persistencia
from src.dataaccess.repository.JsonColasRepository import ColaJsonPersistencia
from src.dataaccess.repository.SismoJsonRepository import SismoJsonRepository
from src.dataaccess.repository.ZonaRepository import ZonaRepository

# Algoritmos y Servicios
from src.business.algortimos.sismos.Priority_Key_sismo import PriorityKeyService
from src.business.services.AvlService import AvlService
from src.business.services.cola_reportes import ColaReportesService
from src.business.services.EliminadosService import EliminadosService
from src.business.services.ModoAutomaticoService import ModoAutomaticoService
from src.business.services.reporte_service import ReporteService
from src.business.services.RelojService import RelojService
from src.business.services.SismosService import SismoService
from src.business.services.ZonaService import ZonaService

# Controladores y Rutas
from src.presentation.controllers.ArbolController import register_arbol_routes
from src.presentation.controllers.EstacionesController import station_bp
from src.presentation.controllers.RelojController import register_reloj_routes
from src.presentation.controllers.ReportesController import register_reporte_routes
from src.presentation.controllers.SismosController import register_sismo_routes
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

avl_service = AvlService()
zona_service = ZonaService(zona_repository)

# The simulation clock starts one year ahead so that timestamps sent by
# the frontend are "in the past" during development. For the defense,
# set it to the date of the scenario / test cases.
reloj_service = RelojService(hora_inicial=datetime.now() + timedelta(days=365))
eliminados_service = EliminadosService()
sismo_service = SismoService(sismo_repository, avl_service, zona_service, reloj_service, eliminados_service)
priority_key_service = PriorityKeyService()

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

# Rutas con inyección de dependencias
register_sismo_routes(app, sismo_service)
register_reporte_routes(app, reporte_service, cola_reportes, modo_automatico_service)
register_zona_routes(app, zona_service)
register_arbol_routes(app, avl_service)
register_reloj_routes(app, reloj_service)


# Rebuild the in-memory AVL from the persisted catalog. Without this the
# tree was empty after every restart while sismos.json still had events.
avl_service.cargar_desde(sismo_repository.get_all())


# =========================================================
# RUTAS BÁSICAS Y EJECUCIÓN
# =========================================================

@app.route("/")
def home():
    return "Servidor Flask corriendo correctamente"


if __name__ == "__main__":
    app.run(debug=True, port=5000)