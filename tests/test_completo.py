import io
import json
import unittest

import app


class FasesTest(unittest.TestCase):
    """End-to-end contract tests for the complete HTTP application."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.app.test_client()
        cls.estado_inicial = app.estado_service.capturar()
        cls.historial_inicial = app.historial_service.repository.cargar()
        cls.nombre_version = "test-punto13"

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
        app.versiones_repository.eliminar(self.nombre_version)

    @classmethod
    def tearDownClass(cls):
        app.estado_service.restaurar(cls.estado_inicial)
        app.historial_service.repository.guardar(cls.historial_inicial)
        app.versiones_repository.eliminar(cls.nombre_version)

    def crear_evento(self, identificador=990001, magnitud=4.5):
        respuesta = self.client.post(
            "/sismos",
            json={
                "id": identificador,
                "magnitude": magnitud,
                "depth": 30.0,
                "epicenter_x": -75.0,
                "epicenter_y": 4.0,
                "timestamp": "2026-09-29T10:00:00",
                "station_id": "TEST-01",
            },
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.get_json()

    def agregar_reporte(self, identificador, revision=1, estacion="TEST-R"):
        return self.client.post(
            "/reportes",
            json={
                "sismo_id": identificador,
                "station_id": estacion,
                "magnitude": 4.5,
                "depth": 30.0,
                "epicenter_x": -75.0,
                "epicenter_y": 4.0,
                "timestamp": "2026-09-29T10:00:00",
                "revision": revision,
            },
        )

    def test_endpoints_de_consulta_y_salud(self):
        for ruta in (
            "/sismos",
            "/arbol/configuracion",
            "/arbol/metricas",
            "/arbol/topologia",
            "/arbol/auditoria",
            "/sismos/metricas",
            "/sismos/historico",
            "/sismos/archivo-rama/elegible",
            "/sismos/consultas/pendientes?k=3",
            "/sismos/consultas/magnitud?min=4&max=6",
            "/sismos/consultas/profundidad-fecha?profundidad_max=100"
            "&fecha_desde=2026-01-01T00:00:00"
            "&fecha_hasta=2026-12-31T23:59:59",
            "/referencias-sismo/910002/detalle",
            "/referencias-sismo/910002/usos",
            "/referencias-sismo/910002/actual",
            "/arbol/comparacion",
            "/arbol/escenario/exportar",
            "/versiones",
            "/historial",
            "/reloj",
            "/estaciones",
            "/zonas",
        ):
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)

        self.assertEqual(
            self.client.get("/estaciones/cobertura?lat=4&lon=-75").status_code,
            500,
        )

    def test_crud_evento_y_consulta_de_detalle(self):
        evento = self.crear_evento()
        identificador = evento["id"]

        detalle = self.client.get(f"/sismos/{identificador}")
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.get_json()["estado"], "activo")
        self.assertIn("clave", detalle.get_json())
        self.assertIn("profundidad_nodo", detalle.get_json())

        correccion = self.client.put(
            f"/sismos/{identificador}",
            json={"magnitude": 6.2, "depth": 15.0},
        )
        self.assertEqual(correccion.status_code, 200)
        self.assertEqual(correccion.get_json()["sismo"]["magnitude"], 6.2)

        revisado = self.client.patch(f"/sismos/{identificador}/audit")
        self.assertEqual(revisado.status_code, 200)

        eliminado = self.client.delete(f"/sismos/{identificador}")
        self.assertEqual(eliminado.status_code, 200)
        self.assertEqual(
            self.client.get(f"/sismos/{identificador}").get_json()["estado"],
            "retirado",
        )

    def test_eliminacion_y_deshacer_conservan_el_evento(self):
        self.crear_evento(990002)
        self.assertEqual(self.client.delete("/sismos/990002").status_code, 200)
        self.assertEqual(
            self.client.post("/historial/deshacer").status_code,
            200,
        )
        recuperado = self.client.get("/sismos/990002")
        self.assertEqual(recuperado.status_code, 200)
        self.assertEqual(recuperado.get_json()["estado"], "activo")

    def test_archivo_manual_historico_y_deshacer(self):
        self.crear_evento(990003, magnitud=4.0)
        archivado = self.client.post("/sismos/990003/archivar")
        self.assertEqual(archivado.status_code, 200)
        historico = self.client.get("/sismos/990003")
        self.assertEqual(historico.status_code, 200)
        self.assertEqual(historico.get_json()["estado"], "archivado")

        self.assertEqual(
            self.client.post("/historial/deshacer").status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/sismos/990003").get_json()["estado"],
            "activo",
        )

    def test_reportes_cola_confirmacion_y_descarte(self):
        self.crear_evento(990004)
        agregado = self.agregar_reporte(990004)
        self.assertEqual(agregado.status_code, 200)
        self.assertEqual(self.client.get("/reportes/cola").status_code, 200)

        procesado = self.client.post("/reportes/cola/validar")
        self.assertEqual(procesado.status_code, 200)
        self.assertIn(
            procesado.get_json().get("decision"),
            {"confirmacion", "confirmado", "procesado"},
        )

        self.agregar_reporte(990004, estacion="TEST-RUIDO")
        descartado = self.client.post("/reportes/cola/descartar")
        self.assertEqual(descartado.status_code, 200)
        self.assertEqual(descartado.get_json()["decision"], "ruido")

    def test_reporte_automatico_y_correccion_por_revision(self):
        self.crear_evento(990005)
        agregado = self.agregar_reporte(990005, estacion="TEST-CORR")
        self.assertEqual(agregado.status_code, 200)
        automatico = self.client.post("/reportes/cola/automatico")
        self.assertEqual(automatico.status_code, 200)

        correccion = self.client.put(
            "/sismos/990005/correction",
            json={
                "station_id": "TEST-CORR-2",
                "revision": 2,
                "magnitude": 6.1,
                "depth": 12.0,
                "epicenter_x": -75.01,
                "epicenter_y": 4.01,
            },
        )
        self.assertEqual(correccion.status_code, 200)
        self.assertEqual(correccion.get_json()["magnitude"], 6.1)

    def test_asociaciones_configuracion_y_guardado_manual(self):
        configuracion = self.client.put(
            "/referencias-sismo/configuracion",
            json={"ventana_horas": 48, "radio_km": 40},
        )
        self.assertEqual(configuracion.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/referencias-sismo",
                json={"sismo_id": 910002, "referencia_id": 910003},
            ).status_code,
            201,
        )
        detalle = self.client.get("/referencias-sismo/910002/detalle")
        self.assertEqual(detalle.status_code, 200)
        self.assertIn("candidatos", detalle.get_json())
        self.assertEqual(
            self.client.get("/referencias-sismo/configuracion").status_code,
            200,
        )

    def test_zonas_estaciones_y_reloj(self):
        zona = self.client.post(
            "/zonas/comprobar",
            json={"longitud": -75.0, "latitud": 4.0},
        )
        self.assertEqual(zona.status_code, 200)
        self.assertIn("zona_poblada", zona.get_json())

        estacion = self.client.post(
            "/estaciones",
            json={
                "id": "TEST-ESTACION",
                "nombre": "Estación de prueba",
                "latitud": 4.0,
                "longitud": -75.0,
            },
        )
        self.assertIn(estacion.status_code, {201, 400})

        reloj_antes = self.client.get("/reloj").get_json()["reloj_actual"]
        avanzado = self.client.post("/reloj/avanzar", json={"horas": 1})
        self.assertEqual(avanzado.status_code, 200)
        self.assertNotEqual(
            reloj_antes,
            avanzado.get_json()["reloj_actual"],
        )

    def test_configuracion_acceso_costoso_y_modo_estres(self):
        configuracion = self.client.put(
            "/arbol/configuracion",
            json={"limite_profundidad": 0, "antiguedad_archivo_horas": 72},
        )
        self.assertEqual(configuracion.status_code, 200)
        metricas = self.client.get("/arbol/metricas").get_json()
        self.assertIn("profundidadMaxima", metricas)

        estres = self.client.post("/arbol/modo-estres", json={"activo": True})
        self.assertEqual(estres.status_code, 200)
        self.assertTrue(estres.get_json()["modoEstres"])
        auditoria = self.client.get("/arbol/auditoria")
        self.assertEqual(auditoria.status_code, 200)
        normal = self.client.post("/arbol/modo-estres", json={"activo": False})
        self.assertIn(normal.status_code, {200, 409})

    def test_carga_por_inserciones_y_recuperacion_topologica(self):
        documento = {
            "eventos": [
                {
                    "id": 991001,
                    "magnitude": 4.0,
                    "depth": 20.0,
                    "epicenter_x": -75.0,
                    "epicenter_y": 4.0,
                    "timestamp": "2026-09-29T10:00:00",
                    "revision": 1,
                    "prioridad": 1,
                    "clave": [1, 4.0, 991001],
                    "reporting_stations": [],
                    "status": "Pendiente",
                    "estado_persistencia": "activo",
                },
                {
                    "id": 991002,
                    "magnitude": 4.2,
                    "depth": 20.0,
                    "epicenter_x": -75.01,
                    "epicenter_y": 4.01,
                    "timestamp": "2026-09-29T10:10:00",
                    "revision": 1,
                    "prioridad": 1,
                    "clave": [1, 4.2, 991002],
                    "reporting_stations": [],
                    "status": "Pendiente",
                    "estado_persistencia": "activo",
                },
            ]
        }
        cargado = self.client.post(
            "/arbol/escenario/cargar",
            data={
                "tipo_carga": "inserciones",
                "archivo": (
                    io.BytesIO(json.dumps(documento).encode()),
                    "inserciones.json",
                ),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(cargado.status_code, 200)
        exportado = self.client.get("/arbol/escenario/exportar").get_json()
        topologia = self.client.post(
            "/arbol/escenario/cargar",
            data={
                "tipo_carga": "topologia",
                "archivo": (
                    io.BytesIO(json.dumps(exportado).encode()),
                    "topologia.json",
                ),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(topologia.status_code, 200)

    def test_guardar_version_persistente(self):
        response = self.client.post(
            "/versiones",
            json={"nombre": self.nombre_version},
        )
        self.assertEqual(response.status_code, 201)
        versiones = self.client.get("/versiones").get_json()["versiones"]
        self.assertIn(
            self.nombre_version,
            {version["nombre"] for version in versiones},
        )

        repositorio_recargado = app.VersionesRepository(
            "data/versiones.json"
        )
        self.assertIsNotNone(repositorio_recargado.obtener(self.nombre_version))

    def test_restaurar_version_y_deshacer(self):
        self.client.post("/versiones", json={"nombre": self.nombre_version})
        configuracion_original = self.client.get(
            "/arbol/configuracion"
        ).get_json()
        modificada = {
            "limite_profundidad": 0,
            "antiguedad_archivo_horas": 72,
        }
        self.assertEqual(
            self.client.put("/arbol/configuracion", json=modificada).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                f"/versiones/{self.nombre_version}/restaurar"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/arbol/configuracion").get_json(),
            configuracion_original,
        )
        self.assertEqual(
            self.client.post("/historial/deshacer").status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/arbol/configuracion").get_json(),
            modificada,
        )

    def test_carga_invalida_conserva_escenario(self):
        antes = app.estado_service.huella(app.estado_service.capturar())
        response = self.client.post(
            "/arbol/escenario/cargar",
            data={
                "tipo_carga": "inserciones",
                "archivo": (
                    io.BytesIO(
                        json.dumps(
                            {"eventos": [{"id": 1}, {"id": 1}]}
                        ).encode()
                    ),
                    "duplicados.json",
                ),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        despues = app.estado_service.huella(app.estado_service.capturar())
        self.assertEqual(antes, despues)

    def test_comparacion_ascendente_muestra_ventaja_avl(self):
        respuesta = self.client.get(
            "/arbol/comparacion?orden=ascendente"
        )
        self.assertEqual(respuesta.status_code, 200)
        resultado = respuesta.get_json()["resultados"][0]
        self.assertLessEqual(
            resultado["avl"]["altura"],
            resultado["bst"]["altura"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
