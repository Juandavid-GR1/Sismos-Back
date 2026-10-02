# Backend - Sistema de Observación Sísmica

Backend desarrollado en **Python** utilizando **Flask**, encargado de proporcionar los servicios y endpoints necesarios para el Sistema de Observación Sísmica.

---

## 📋 Requerimientos previos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

* **Python 3.x**
* **pip**

Puedes verificar las versiones instaladas con:

```bash
python --version
pip --version
```

---

## 📦 Dependencias

El proyecto utiliza las siguientes dependencias principales:

* **Flask**
* **Flask-CORS**

Las dependencias se encuentran especificadas en el archivo:

```text
requirements.txt
```

---

## 🚀 Guía de inicio rápido

### 1. Clonar el repositorio

Clona el repositorio y navega hasta la carpeta del backend:

```bash
git clone <URL_DEL_REPOSITORIO>
cd backend
```

---

### 2. Crear el entorno virtual

Ejecuta:

```bash
python -m venv venv
```

Esto creará un entorno virtual llamado `venv`.

### Activar el entorno virtual

#### Windows

En CMD:

```cmd
venv\Scripts\activate
```

En PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
source venv/bin/activate
```

Una vez activado, deberías ver `(venv)` al inicio de la terminal.

---

### 3. Instalar las dependencias

Con el entorno virtual activo, ejecuta:

```bash
pip install -r requirements.txt
```

---

## ▶️ Ejecutar el servidor

Para iniciar el backend, ejecuta:

```bash
python app.py
```

Si el servidor se inicia correctamente, estará disponible en:

```text
http://localhost:5000
```

También puedes acceder mediante:

```text
http://127.0.0.1:5000
```

---

# 🔌 Endpoints

## 📡 Estaciones

Endpoint principal para la gestión de las estaciones sísmicas.

**Ruta:**

```text
/estaciones
```

**URL:**

```text
http://127.0.0.1:5000/estaciones
```

### Métodos disponibles

| Método   | Endpoint           | Descripción                     |
| -------- | ------------------ | ------------------------------- |
| `GET`    | `/estaciones`      | Obtener todas las estaciones    |
| `GET`    | `/estaciones/<id>` | Obtener una estación específica |
| `POST`   | `/estaciones`      | Registrar una nueva estación    |
| `PUT`    | `/estaciones/<id>` | Actualizar una estación         |
| `DELETE` | `/estaciones/<id>` | Eliminar una estación           |

---

## 🌎 Sismos

Endpoint para la gestión de los registros de sismos.

**Ruta:**

```text
/sismos
```

**URL:**

```text
http://127.0.0.1:5000/sismos
```

### Métodos disponibles

| Método   | Endpoint       | Descripción                     |
| -------- | -------------- | ------------------------------- |
| `GET`    | `/sismos`      | Obtener los registros de sismos |
| `GET`    | `/sismos/<id>` | Obtener un sismo específico     |
| `POST`   | `/sismos`      | Registrar un nuevo sismo        |
| `PUT`    | `/sismos/<id>` | Actualizar un registro de sismo |
| `DELETE` | `/sismos/<id>` | Eliminar un registro de sismo   |

GET	/	Verificar que el servidor está funcionando
GET	/zonas	Obtener todas las zonas geográficas en GeoJSON
POST	/zonas/comprobar	Comprobar si unas coordenadas están dentro de una zona poblada
POST	/reportes	Procesar un reporte de una estación sobre un sismo existente

GET /reportes/cola

> **Nota:** Los endpoints y métodos indicados deben coincidir con las rutas realmente implementadas en `app.py`.

---

## 🌐 URL del servidor

Una vez ejecutado el proyecto, el servidor estará disponible en:

**http://localhost:5000**

También puedes utilizar:

**http://127.0.0.1:5000**

---

## 📁 Estructura básica del proyecto

Una estructura recomendada sería:

```text
backend/
│---src
├── app.py
├── requirements.txt
├── README.md
│
└── venv/
```

> El directorio `venv/` normalmente no debe subirse al repositorio. Se recomienda agregarlo al archivo `.gitignore`.

## Persistencia del catálogo sísmico

La fase inicial de eliminación separa el catálogo activo del histórico:

Todos los archivos JSON de ejecución se guardan bajo `data/`:

* `data/sismos.json`: eventos activos que se cargan en el AVL al iniciar el servidor.
* `data/historico_sismos.json`: eventos que ya no pertenecen al AVL, incluyendo los
  retirados por una eliminación individual.
* `data/retirados.json`: identificadores que no pueden reutilizarse ni aceptarse en
  reportes posteriores hasta que una futura acción de deshacer los libere.
* `data/referencias_sismo.json`: asociaciones seleccionadas y configuración de
  ventana temporal `W` y radio `R`.
* `data/configuracion_escenario.json`: límite de profundidad `L` y antigüedad
  mínima `T` para las fases de acceso costoso y archivo de ramas.

Los registros antiguos que no tengan `estado_persistencia` se interpretan como
activos para conservar compatibilidad con los datos existentes.

### Operaciones AVL preparadas para archivo

La estructura AVL permite capturar una rama por identificador mediante
`AvlService.capturar_subarbol(id)`. La lista devuelta es una instantánea tomada
antes de modificar el árbol. `AvlService.eliminar_subarbol(id)` utiliza esa
misma lista para retirar los nodos, aunque las eliminaciones intermedias
produzcan rotaciones. El servicio también evalúa automáticamente todos los
subárboles activos: una rama es elegible cuando todos sus eventos tienen
prioridad baja y antigüedad estrictamente mayor que `T`. Se selecciona la rama
con más nodos; los empates se resuelven por profundidad de la raíz y luego por
identificador numérico descendente. La captura de identificadores se realiza
antes de retirar la rama.

### Acciones atómicas y deshacer

La eliminación individual y el archivo de una rama se registran como una sola
acción en el historial unificado, aunque internamente afecten varios nodos.
Cada acción conserva snapshots completos para permitir restaurar el catálogo
activo, el histórico, los identificadores retirados y el AVL.

Endpoints disponibles:

* `DELETE /sismos/<id>`: eliminación individual.
* `POST /sismos/<id>/archivar`: archiva la rama completa capturada desde el AVL.
* `GET /sismos/archivo-rama/elegible`: muestra la rama seleccionada por las
  reglas automáticas, sus identificadores, cantidad, profundidad y criterios.
* `POST /sismos/archivo-rama/elegible`: archiva la rama seleccionada
  automáticamente. Si no existe una rama elegible, devuelve esa situación sin
  modificar el estado.
* `GET /sismos/historico`: lista eventos archivados o retirados.
* `POST /historial/deshacer`: deshace la última acción modificadora.
* `POST /sismos/acciones/deshacer`: alias de la misma pila unificada.

* `data/historial_acciones.json`: pila persistente de acciones deshacibles. Se
  guarda en orden cronológico, desde la acción más antigua hasta la más reciente
  (base → cima). Al iniciar el servidor se reconstruye la pila, por lo que
  `deshacer` siempre consume primero la última acción guardada, incluso después
  de reiniciar el proceso.

La pila unificada registra una sola acción por cambio efectivo, incluyendo
creaciones, correcciones, marcado como revisado, eliminación individual,
archivo de ramas y procesamiento de reportes. Las dos rutas de deshacer
consultan el mismo `HistorialService`.

### Profundidad y presupuesto de acceso

La configuración se consulta en `GET /arbol/configuracion` y se modifica con
`PUT /arbol/configuracion`. Los valores iniciales son `L = 3` y `T = 72` horas.
El cuerpo acepta `limite_profundidad` y `antiguedad_archivo_horas`, o sus
abreviaturas `L` y `T`. `L` debe ser un entero no negativo y `T` debe ser
positivo.

`GET /arbol/metricas` conserva el parámetro opcional `L` por compatibilidad.
Cada nodo del árbol informa por separado su prioridad (`P`) y `accesoCostoso`;
esta marca se determina para eventos de prioridad alta cuando su profundidad
es estrictamente mayor que `L`, y el costo simulado es `profundidad + 1`.

### Asociaciones entre eventos

Las rutas `/referencias-sismo` muestran los candidatos y la asociación actual.
Los candidatos consideran eventos activos y archivados, excluyen retirados y
se ordenan de forma determinista por distancia, magnitud y luego identificador.
La asociación se recalcula después de cada operación modificadora. La distancia
conserva el cálculo geográfico Haversine usado por el proyecto para sus
coordenadas de latitud y longitud. La configuración inicial es `W = 48` horas
y `R = 40` km; puede consultarse con `GET /referencias-sismo/configuracion` y
modificarse con `PUT /referencias-sismo/configuracion` enviando
`{"ventana_horas": 48, "radio_km": 40}`.

La fase 4 amplía las consultas de asociaciones:

* `GET /referencias-sismo/<id>` mantiene `referencias` por compatibilidad y
  ahora también devuelve `candidatos`, la `referencia` elegida y
  `eventos_que_lo usan_como_referencia`.
* `GET /referencias-sismo/<id>/detalle` devuelve la consulta completa,
  incluyendo el estado `activo` o `archivado` de cada evento y la configuración
  vigente de `W` y `R`.
* `GET /referencias-sismo/<id>/usos` lista los eventos que tienen al evento
  indicado como referencia.

Los eventos retirados no aparecen en estas consultas. Las asociaciones siguen
siendo deterministas y cada evento receptor conserva como máximo una referencia,
mientras que una referencia puede ser utilizada por varios receptores.

### Consultas de eventos

La fase 3 expone las consultas del catálogo activo:

* `GET /sismos/consultas/pendientes?k=3`: devuelve hasta `k` eventos
  pendientes en orden descendente de `K=(P,M,I)`.
* `GET /sismos/consultas/magnitud?min=4.0&max=5.5`: devuelve eventos dentro
  del intervalo inclusivo de magnitud.
* `GET /sismos/consultas/profundidad-fecha?profundidad_max=30&fecha_desde=2026-01-01T00:00:00&fecha_hasta=2026-12-31T23:59:59`:
  devuelve eventos cuya profundidad del hipocentro es menor o igual al límite
  y cuya fecha está dentro del intervalo inclusivo.

Las respuestas incluyen `nodos_avl_examinados`. La consulta de pendientes puede
detenerse al encontrar `k` eventos; las consultas por magnitud y por
profundidad/fecha examinan todos los nodos porque esos atributos no permiten
descartar ramas del AVL de forma segura en todos los casos.

### Comparación AVL contra BST

La fase 5 usa árboles temporales y no modifica el AVL operativo. Ambos árboles
reciben las mismas claves `K=(P,M,I)` y se comparan con distintos órdenes de
inserción:

* `GET /arbol/comparacion`: evalúa `original`, `ascendente` y `descendente`.
* `GET /arbol/comparacion?orden=ascendente`: evalúa un orden específico.
* `POST /arbol/comparacion`: acepta opcionalmente:

```json
{
  "ids": [910001, 910002, 910003],
  "ordenes": ["original", "ascendente", "descendente"]
}
```

El resultado informa para cada orden la altura, cantidad de hojas,
comparaciones de inserción, total/promedio/máximo de comparaciones de búsqueda
y el detalle de cada clave buscada. El conjunto de búsqueda es el mismo en AVL
y BST, por lo que la comparación estructural es reproducible.

### Reportes sobre eventos archivados

Un reporte consulta primero los eventos activos y luego el histórico:

* Una revisión menor se rechaza como antigua y el evento permanece archivado.
* La misma revisión con los mismos datos confirma el evento y agrega la estación
  sin duplicarla; el evento permanece archivado.
* La misma revisión con datos distintos se rechaza por conflicto.
* Una revisión mayor válida reactiva el evento, lo devuelve al AVL, conserva su
  identidad y asociaciones, y lo deja `Pendiente`.
* Un identificador retirado individualmente se rechaza antes de consultar el
  histórico y no puede reactivarse mediante reportes.

### Fases 5 y 6: validación integral y reinicio

Las pruebas de integración de las fases 1 a 4 están en
`tests/test_phase5.py` y usan únicamente `unittest` de la biblioteca estándar.
Se pueden ejecutar desde la raíz del proyecto con:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

La suite cubre eliminación individual y deshacer, archivo de rama y deshacer,
reglas de reportes sobre eventos archivados, IDs retirados y altas con revisión
inicial mayor que uno. La fase 6 también valida que una acción pendiente de deshacer se
recupere después de crear una nueva instancia del servicio, simulando el
reinicio del servidor.

---

## 👨‍💻 Desarrollo

Para trabajar en el proyecto, se recomienda mantener el entorno virtual activo mientras se ejecuta o desarrolla el backend.

```bash
venv\Scripts\activate
python app.py
```
