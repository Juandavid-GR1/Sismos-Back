"""Section 16 mandatory cases, reproduced from the files in pruebas/.

Every test loads one scenario file through the real HTTP endpoint, runs the
demo steps and checks the expected result. The previous state, the undo
history and the saved versions are restored after each test (same pattern
as test_completo.py), so the team's data is not modified.
"""
import io
import json
import os
import unittest

import app
from src.dataaccess.repository.VersionesRepository import VersionesRepository

PRUEBAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pruebas")
VERSION = "test-seccion16"


class CasosSeccion16Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.app.test_client()

    def setUp(self):
        self.estado_prueba = app.estado_service.capturar()
        self.historial_prueba = app.historial_service.repository.cargar()

    def tearDown(self):
        app.estado_service.restaurar(self.estado_prueba)
        app.historial_service.repository.guardar(self.historial_prueba)
        app.historial_service._pila.vaciar()
        for accion in reversed(self.historial_prueba):
            app.historial_service._pila.apilar(accion)
        app.historial_service._secuencia = max(
            (int(accion.get("numero", 0)) for accion in self.historial_prueba),
            default=0,
        )
        app.versiones_repository.eliminar(VERSION)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def cargar(self, nombre, tipo):
        with open(os.path.join(PRUEBAS, nombre), "rb") as archivo:
            contenido = archivo.read()
        return self.client.post(
            "/arbol/escenario/cargar",
            data={"tipo_carga": tipo, "archivo": (io.BytesIO(contenido), nombre)},
            content_type="multipart/form-data",
        )

    def cargar_ok(self, nombre, tipo):
        respuesta = self.cargar(nombre, tipo)
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        return respuesta.get_json()

    def evento(self, identificador):
        return self.client.get(f"/sismos/{identificador}").get_json()

    def metricas(self):
        return self.client.get("/arbol/metricas").get_json()

    def inorden(self):
        return [clave[2] for clave in self.metricas()["recorridos"]["inorden"]]

    def contadores(self):
        return self.client.get("/sismos/metricas").get_json()

    def deshacer(self):
        respuesta = self.client.post("/historial/deshacer")
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.get_json()["mensaje"]

    def huella(self):
        return app.estado_service.huella(app.estado_service.capturar())

    # ------------------------------------------------------------------
    # 1. Limits and ties
    # ------------------------------------------------------------------
    def test_01_limites_y_empates(self):
        self.cargar_ok("01_limites_empates_inserciones.json", "inserciones")
        esperadas = {
            101: [3, 4.5, 101],   # M = 4.5 and H = 30 in a populated zone
            102: [2, 4.5, 102],   # same values outside a populated zone
            103: [2, 4.5, 103],   # H = 30.1 > 30
            104: [1, 4.4, 104],   # M = 4.4 < 4.5
            105: [3, 6.0, 105],   # M = 6.0 anywhere
            106: [2, 5.9, 106],   # M = 5.9 < 6.0
            107: [2, 4.5, 107],   # epicenter on the Central / Oriental border
        }
        for identificador, clave in esperadas.items():
            self.assertEqual(self.evento(identificador)["clave"], clave)
        # Same P and M: the id breaks the tie (inserted as 112, 110, 111)
        orden = self.inorden()
        self.assertLess(orden.index(110), orden.index(111))
        self.assertLess(orden.index(111), orden.index(112))
        self.assertEqual(orden, [104, 102, 103, 107, 110, 111, 112, 106, 101, 105])
        # Insertion load: AVL and BST with the same comparator and order
        comparacion = self.client.get("/arbol/comparacion?orden=original").get_json()["resultados"][0]
        self.assertEqual(comparacion["avl"]["altura"], 3)
        self.assertEqual(comparacion["bst"]["altura"], 7)
        # Border point of the populated zone, answered by the zone service
        zona = self.client.post("/zonas/comprobar", json={"longitud": -72.0, "latitud": 6.0}).get_json()
        self.assertFalse(zona["zona_poblada"])

    # ------------------------------------------------------------------
    # 2. Correction and old report
    # ------------------------------------------------------------------
    def test_02_correccion_y_reporte_antiguo(self):
        self.cargar_ok("02_correccion_reporte_antiguo.json", "topologia")
        self.assertEqual(self.evento(201)["clave"], [2, 4.8, 201])
        nodos = self.metricas()["cantidadNodos"]

        paso = self.client.post("/reportes/cola/validar").get_json()
        self.assertEqual(paso["decision"], "correccion")
        corregido = self.evento(201)
        self.assertEqual((corregido["magnitude"], corregido["depth"], corregido["prioridad"]), (6.2, 15.0, 3))

        rechazo = self.client.post("/reportes/cola/validar")
        self.assertEqual(rechazo.status_code, 409)
        self.assertEqual(rechazo.get_json()["decision"], "reporte_antiguo")
        self.assertEqual(self.evento(201)["clave"], [3, 6.2, 201])     # not reverted
        self.assertEqual(self.metricas()["cantidadNodos"], nodos)        # no new node
        self.assertEqual(self.contadores()["correcciones_aceptadas"], 1)
        self.assertEqual(self.contadores()["reportes_descartados"], 1)

        # Undo the rejected queue step: the report goes back to the queue
        self.deshacer()
        self.assertEqual(len(self.client.get("/reportes/cola").get_json()["cola"]), 1)
        # Undo the correction
        self.deshacer()
        self.assertEqual(self.evento(201)["clave"], [2, 4.8, 201])

    # ------------------------------------------------------------------
    # 3. Late report
    # ------------------------------------------------------------------
    def test_03_reporte_tardio(self):
        self.cargar_ok("03_reporte_tardio.json", "topologia")
        antes = self.client.get("/referencias-sismo/302/detalle").get_json()
        self.assertEqual(antes["referencia"]["referencia_id"], 301)

        paso = self.client.post("/reportes/cola/validar").get_json()
        self.assertEqual(paso["decision"], "alta")

        detalle_302 = self.client.get("/referencias-sismo/302/detalle").get_json()
        self.assertEqual([c["id"] for c in detalle_302["candidatos"]], [303, 301])   # closest first
        self.assertEqual(detalle_302["referencia"]["referencia_id"], 303)
        detalle_301 = self.client.get("/referencias-sismo/301/detalle").get_json()
        self.assertEqual(detalle_301["referencia"]["referencia_id"], 303)

    # ------------------------------------------------------------------
    # 4. Rotations and recovery
    # ------------------------------------------------------------------
    def test_04_cuatro_casos_de_rotacion(self):
        self.cargar_ok("04_rotaciones_inserciones.json", "inserciones")
        casos = self.metricas()["contadores"]["casos"]
        self.assertEqual(casos, {"LL": 1, "RR": 1, "LR": 1, "RL": 1})

    def test_05_estres_degradado_y_recuperacion(self):
        rechazo = self.cargar("08_error_desbalanceada_sin_estres.json", "topologia")
        self.assertEqual(rechazo.status_code, 400)

        self.cargar_ok("05_topologia_estres.json", "topologia")
        antes = self.metricas()
        self.assertTrue(antes["modoEstres"])
        self.assertEqual((antes["altura"], antes["balance"]), (7, -7))          # imbalance > 2
        orden_antes = self.inorden()
        referencias_antes = self.client.get("/arbol/escenario/exportar").get_json()["referencias"]["referencias"]

        self.assertEqual(self.client.post("/arbol/recuperar-balance").status_code, 200)
        despues = self.metricas()
        self.assertEqual(despues["altura"], 3)
        self.assertEqual(self.inorden(), orden_antes)                         # same identities and order
        self.assertTrue(self.client.get("/arbol/auditoria").get_json()["valido"])
        referencias = self.client.get("/arbol/escenario/exportar").get_json()["referencias"]["referencias"]
        par = lambda lista: sorted((r["sismo_id"], r["referencia_id"]) for r in lista)
        self.assertEqual(par(referencias), par(referencias_antes))            # same associations
        self.assertEqual(self.client.post("/arbol/modo-estres", json={"activo": False}).status_code, 200)

    # ------------------------------------------------------------------
    # 5. Mass archive
    # ------------------------------------------------------------------
    def test_06_archivo_masivo(self):
        self.cargar_ok("06_archivo_masivo.json", "topologia")
        vista = self.client.get("/sismos/archivo-rama/elegible").get_json()
        self.assertEqual(vista["raiz"], 604)
        self.assertEqual(vista["cantidad"], 7)
        # Root 608 has priority 1 but priority 2 descendants -> not eligible
        self.assertNotIn(608, [c["raiz"] for c in vista["candidatos"]])
        # Ties (3 nodes, same depth) resolved by the larger id
        self.assertEqual([c["raiz"] for c in vista["candidatos"][1:4]], [610, 606, 602])

        archivo = self.client.post("/sismos/archivo-rama/elegible").get_json()
        self.assertEqual(sorted(archivo["eventos_archivados"]), [601, 602, 603, 604, 605, 606, 607])
        self.assertEqual(self.metricas()["cantidadNodos"], 8)
        self.assertEqual(self.contadores()["archivos_masivos"], 1)
        self.assertEqual(self.contadores()["eventos_archivados"], 7)

        self.deshacer()                                                         # whole archive undone
        self.assertEqual(self.metricas()["cantidadNodos"], 15)
        self.assertEqual(self.contadores()["eventos_archivados"], 0)

        self.client.put("/arbol/configuracion", json={"antiguedad_archivo_horas": 200})
        sin_rama = self.client.get("/sismos/archivo-rama/elegible").get_json()
        self.assertFalse(sin_rama["elegible"])

    # ------------------------------------------------------------------
    # Report burst (every queue decision)
    # ------------------------------------------------------------------
    def test_07_rafaga_de_reportes(self):
        self.cargar_ok("07_rafaga_reportes.json", "topologia")
        decisiones = [
            self.client.post("/reportes/cola/automatico").get_json()["decision"]
            for _ in range(7)
        ]
        self.assertEqual(decisiones, [
            "alta", "confirmacion", "correccion", "conflicto",
            "reporte_antiguo", "identificador_retirado", "confirmacion",
        ])
        self.assertEqual(self.client.post("/reportes/cola/descartar").get_json()["decision"], "ruido")
        contadores = self.contadores()
        self.assertEqual((contadores["correcciones_aceptadas"], contadores["conflictos"],
                          contadores["reportes_descartados"]), (1, 1, 3))
        self.deshacer()
        self.assertEqual(len(self.client.get("/reportes/cola").get_json()["cola"]), 1)

    # ------------------------------------------------------------------
    # 6. Persistence and consistency
    # ------------------------------------------------------------------
    def test_08_persistencia_y_consistencia(self):
        self.cargar_ok("05_topologia_normal.json", "topologia")
        huella = self.huella()
        for nombre, mensaje in (
            ("08_error_desbalanceada_sin_estres.json", "modo estrés"),
            ("09_error_altura_inconsistente.json", "Altura inconsistente"),
            ("10_error_orden_bst.json", "orden global BST"),
            ("11_error_prioridad_inconsistente.json", "Metadatos inconsistentes"),
        ):
            respuesta = self.cargar(nombre, "topologia")
            self.assertEqual(respuesta.status_code, 400, nombre)
            self.assertIn(mensaje, respuesta.get_json()["error"])
            self.assertEqual(self.huella(), huella, nombre)                    # state untouched

        # Named version, read again from disk as after a restart
        self.assertEqual(self.client.post("/versiones", json={"nombre": VERSION}).status_code, 201)
        reiniciado = VersionesRepository(app.versiones_repository.json_file)
        self.assertIsNotNone(reiniciado.obtener(VERSION))
        self.cargar_ok("05_topologia_estres.json", "topologia")
        self.assertEqual(self.client.post(f"/versiones/{VERSION}/restaurar").status_code, 200)
        self.assertEqual(self.huella(), huella)
        self.deshacer()                                                         # restoring is undoable
        self.assertTrue(self.metricas()["modoEstres"])


if __name__ == "__main__":
    unittest.main()
