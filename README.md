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

Los registros antiguos que no tengan `estado_persistencia` se interpretan como
activos para conservar compatibilidad con los datos existentes.

### Operaciones AVL preparadas para archivo

La estructura AVL permite capturar una rama por identificador mediante
`AvlService.capturar_subarbol(id)`. La lista devuelta es una instantánea tomada
antes de modificar el árbol. `AvlService.eliminar_subarbol(id)` utiliza esa
misma lista para retirar los nodos, aunque las eliminaciones intermedias
produzcan rotaciones. Esta fase solo modifica el AVL; el traslado al histórico,
el registro de la acción y los endpoints se implementarán posteriormente.

### Acciones atómicas y deshacer

La eliminación individual y el archivo de una rama se registran como una sola
acción en el historial unificado, aunque internamente afecten varios nodos.
Cada acción conserva snapshots completos para permitir restaurar el catálogo
activo, el histórico, los identificadores retirados y el AVL.

Endpoints disponibles:

* `DELETE /sismos/<id>`: eliminación individual.
* `POST /sismos/<id>/archivar`: archiva la rama completa capturada desde el AVL.
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
