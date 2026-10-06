# Archivos de prueba 

Datos reproducibles para demostrar la solución. Cada archivo se generó usando la API real del backend y luego se exportó con `GET /arbol/escenario/exportar`. Todos los resultados "obtenidos" de esta guía se comprobaron cargando cada archivo en un backend limpio. La misma comprobación está automatizada en `tests/test_casos_seccion16.py`.

## Cómo usarlos

**En la interfaz:** Análisis → **Persistencia** → elige el modo de carga → selecciona el archivo con el explorador → **Cargar**.

- **Carga por inserciones:** solo para los archivos que dicen `inserciones`. Contienen el arreglo `eventos`, que se inserta en ese orden en el AVL (con balanceo) y en un BST sin balanceo. Al terminar se muestran raíz, altura, profundidad máxima y hojas de los dos árboles, con el enlace "Ver los dos árboles dibujados".
- **Carga por topología:** para todos los demás. Son exportaciones completas: recuperan la forma exacta del árbol, la cola en su orden, el reloj, las zonas, los parámetros, las asociaciones y los contadores.

**Con pruebas automáticas** (desde la carpeta del backend):

```
python -m pytest tests/test_casos_seccion16.py -v
```

Cada prueba restaura el estado, el historial y las versiones al terminar, igual que `test_completo.py`.

> **Reloj:** al cargar por topología, el reloj del escenario toma la fecha del archivo (por ejemplo 2026-10-01 12:00 UTC). Para crear eventos nuevos con la hora actual, primero avanza el reloj ("Ahora" en el menú del reloj).

| Archivo | Modo | Caso |
|---|---|---|
| `01_limites_empates_inserciones.json` | inserciones | Límites y empates |
| `01_limites_empates_topologia.json` | topología | Límites y empates (mismo escenario) |
| `02_correccion_reporte_antiguo.json` | topología | Corrección y reporte antiguo |
| `03_reporte_tardio.json` | topología | Reporte tardío |
| `04_rotaciones_inserciones.json` | inserciones | Rotaciones LL, RR, LR y RL |
| `05_topologia_estres.json` | topología | Estructura degradada en estrés y recuperación |
| `05_topologia_normal.json` | topología | Persistencia: topología normal |
| `06_archivo_masivo.json` | topología | Archivo masivo |
| `07_rafaga_reportes.json` | topología | Ráfaga de reportes (todas las decisiones de la cola) |
| `08_error_desbalanceada_sin_estres.json` | topología | Debe rechazarse |
| `09_error_altura_inconsistente.json` | topología | Debe rechazarse |
| `10_error_orden_bst.json` | topología | Debe rechazarse |
| `11_error_prioridad_inconsistente.json` | topología | Debe rechazarse |

---

## 1. Límites y empates

**Estado inicial:** 10 eventos del 2026-10-01 a las 08:00 UTC; reloj a las 12:00 UTC.

| Id | M | H (km) | Epicentro | Prioridad esperada | Obtenida |
|---|---|---|---|---|---|
| 101 | 4.5 | 30.0 | Bogotá (-74.08, 4.60), zona poblada | 3 (M ≥ 4.5, H ≤ 30 y zona poblada) | 3 |
| 102 | 4.5 | 30.0 | Amazonía (-70, 0), no poblada | 2 | 2 |
| 103 | 4.5 | 30.1 | Bogotá | 2 (H > 30) | 2 |
| 104 | 4.4 | 10.0 | Bogotá | 1 (M < 4.5) | 1 |
| 105 | 6.0 | 200.0 | Amazonía | 3 (M ≥ 6.0 en cualquier lugar) | 3 |
| 106 | 5.9 | 200.0 | Amazonía | 2 | 2 |
| 107 | 4.5 | 30.0 | **Borde** (-72.0, 6.0) entre Zona Central (poblada) y Zona Oriental (no poblada) | 2 | 2 |
| 112, 110, 111 | 5.0 | 50.0 | Amazonía | 2 (empate de P y M) | 2 |

**Pasos:** cargar `01_limites_empates_inserciones.json` por inserciones. Luego, en Árboles, revisar el recorrido inorden.

**Resultado obtenido:**

- Inorden: `104, 102, 103, 107, 110, 111, 112, 106, 101, 105`. Los eventos 110, 111 y 112 tienen igual P y M y se insertaron en el orden 112, 110, 111. Aun así quedan ordenados por identificador: el desempate de K = (P, M, I) es el id.
- AVL: altura 3, 4 hojas, raíz (2, 5.0, 110). BST con el mismo orden: altura 7, 3 hojas, raíz (3, 4.5, 101).
- **Borde de zona:** el punto (-72.0, 6.0) da `zona_poblada = false` (`POST /zonas/comprobar`). El algoritmo de ray casting usa comparaciones estrictas, así que un punto de un borde compartido pertenece a una sola zona: la que está al este (o al norte). Por eso cae en la Zona Oriental.

## 2. Corrección y reporte antiguo

**Estado inicial:** el evento 201 (M 4.8, H 70 km, Bogotá) con prioridad 2, clave (2, 4.8, 201). La cola tiene dos reportes del 201: revisión 2 (M 6.2, H 15) y después revisión 1 (M 4.8, H 70).

**Pasos:** Observatorio → Reportes → procesar la cola paso a paso.

| Paso | Esperado | Obtenido |
|---|---|---|
| 1 (rev. 2) | Corrección: prioridad 2 → 3 | `correccion`, clave (3, 6.2, 201), revisión 2 |
| 2 (rev. 1) | Rechazo por revisión menor, sin nuevo nodo y sin revertir | `reporte_antiguo` (409); el evento sigue en (3, 6.2, 201); los nodos siguen siendo 3 |
| Contadores | correcciones +1, descartados +1 | correcciones_aceptadas = 1, reportes_descartados = 1 |
| Deshacer ×1 | El reporte rechazado vuelve a la cola | cola = 1 |
| Deshacer ×2 | Se deshace la corrección | (2, 4.8, 201), revisión 1 |

## 3. Reporte tardío

**Estado inicial:** evento 301 (M 5.6, 10:00) y evento 302 (M 4.2, 10:20), a 5.5 km entre sí. La referencia de 302 es 301. En la cola está el reporte del evento 303 (M 6.1, ocurrido a las **09:55**).

**Pasos:** procesar la cola y luego revisar Análisis → Asociaciones (eventos 301, 302 y 303).

**Resultado obtenido:**

- Decisión `alta`: se registra el 303.
- Candidatos nuevos de 302: `303 (1.57 km)` y `301 (5.55 km)`. Por la política (menor distancia, luego mayor magnitud, luego menor id), la referencia de 302 pasa de 301 a **303**.
- 301 también obtiene como referencia a 303 (4.0 km): es más fuerte y ocurrió antes.
- 303 no tiene referencia (no existe un evento anterior más fuerte). Lo usan como referencia 301 y 302.

## 4. Rotaciones y recuperación

### Cuatro casos de balanceo (`04_rotaciones_inserciones.json`, inserciones)

Ocho eventos de prioridad 1 cuya magnitud fija el orden de las claves: 30, 20, 10 → **LL**; 40, 50 → **RR**; 25 → **RL**; 5, 7 → **LR**.

**Obtenido:** casos LL = 1, RR = 1, LR = 1, RL = 1 (Árboles → AVL activo → "Casos LL / RR / LR / RL"). AVL de altura 3 y BST de altura 4.

### Estructura degradada en estrés (`05_topologia_estres.json`, topología)

Ocho claves ascendentes insertadas con el modo estrés activo forman una cadena. Cada evento tiene una asociación con el siguiente: es más pequeño, ocurrió después y está a unos 3 km.

| Paso | Esperado | Obtenido |
|---|---|---|
| Cargar `08_error_desbalanceada_sin_estres.json` | Rechazo | 400 «Una topología desbalanceada requiere modo estrés.» |
| Cargar `05_topologia_estres.json` | Se carga en estrés | modo estrés activo; altura 7; factor de la raíz −7 (desbalance > 2) |
| Verificar estructura | Desbalance esperado, sin errores de orden | 6 nodos con `desbalance_esperado` (factores −2 a −7); válido |
| Recuperación global | Altura logarítmica | altura 3; 8 casos aplicados |
| Identidades y orden | Iguales | inorden `501…508` igual antes y después |
| Asociaciones | Iguales | las 7 parejas (evento, referencia) no cambian |
| Volver a modo normal | Permitido | 200 |

## 5. Archivo masivo (`06_archivo_masivo.json`, topología)

**Estado inicial:** 15 eventos del 2026-10-01 (unas 100 h antes del reloj, que está en el 2026-10-05 12:00; T = 72 h). Los 601 a 611 tienen prioridad 1 y los 612 a 615 prioridad 2. La raíz del árbol es **608**, de prioridad 1.

| Paso | Esperado | Obtenido |
|---|---|---|
| Ver la rama elegible (Análisis → Archivo) | La de más nodos | raíz **604**, 7 eventos (601 a 607), profundidad 1 |
| Raíz de baja prioridad con un descendiente de prioridad mayor | No elegible | 608 no aparece entre los candidatos (su subárbol contiene 612 a 615) |
| Criterios de desempate | Más nodos, luego mayor profundidad, luego mayor id | orden de candidatos: 604 (7), 610 (3), 606 (3), 602 (3), luego hojas 611, 609, 607… |
| Archivar | 7 eventos al histórico | eventos_archivados = [604, 602, 601, 603, 606, 605, 607]; quedan 8 nodos; archivos_masivos = 1; eventos_archivados = 7 |
| Deshacer | Se revierte el archivo completo | 15 nodos; contadores en 0 |
| T = 200 h (Análisis → Parámetros) | Ninguna rama elegible | «No existe una rama elegible para archivo.» |

## Ráfaga de reportes (`07_rafaga_reportes.json`, topología)

**Estado inicial:** eventos 701 (M 5.0) y 702 (M 3.5). El evento 703 fue eliminado y su id quedó retirado. La cola tiene 8 reportes.

Procesándolos en modo automático se obtiene, en orden: `alta` (704), `confirmacion` (704, otra estación), `correccion` (701 rev. 2), `conflicto` (701 rev. 2 con otros datos), `reporte_antiguo` (701 rev. 1), `identificador_retirado` (703) y `confirmacion` (702). El último reporte se descarta con "Descartar como ruido".

Contadores: correcciones_aceptadas = 1, conflictos = 1 y reportes_descartados = 3 (antiguo, retirado y ruido). Al deshacer el descarte, el reporte vuelve a la cola.

## 6. Persistencia y consistencia

1. Cargar `05_topologia_normal.json` (10 eventos y 1 reporte en cola), que se carga en modo normal. `05_topologia_estres.json` es la topología en estrés (caso 4).
2. Cargar cada archivo con error. Todos se rechazan y **el estado actual no cambia** (misma huella de estado antes y después):

| Archivo | Mensaje obtenido |
|---|---|
| `08_error_desbalanceada_sin_estres.json` | Una topología desbalanceada requiere modo estrés. |
| `09_error_altura_inconsistente.json` | Altura inconsistente para la clave [3, 4.7, 804]. |
| `10_error_orden_bst.json` | Las claves de la topología no tienen orden global BST. |
| `11_error_prioridad_inconsistente.json` | Metadatos inconsistentes para el evento 801. |

3. **Versión después de reiniciar:** guardar la versión `demo-sustentacion` (Persistencia → Versiones). Luego detener Flask (Ctrl+C), iniciarlo de nuevo y recargar la página. La versión sigue en la lista (se guarda en `data/versiones.json`). Restaurarla, y deshacer la restauración con «Deshacer».
4. **Deshacer una corrección y un paso de cola:** ver el caso 2.

Exportar (Persistencia → Descargar JSON) y volver a cargar ese archivo por topología recupera el mismo escenario operativo.
