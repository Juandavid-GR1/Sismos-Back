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

---

## 👨‍💻 Desarrollo

Para trabajar en el proyecto, se recomienda mantener el entorno virtual activo mientras se ejecuta o desarrolla el backend.

```bash
venv\Scripts\activate
python app.py
```
