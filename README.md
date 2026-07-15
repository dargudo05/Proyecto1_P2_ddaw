# Documentación del Proyecto de Nómina - FastAPI

Este proyecto es una API REST desarrollada con **FastAPI** para gestionar empleados, registrar novedades mensuales y automatizar el cálculo de la nómina bajo la **normativa laboral y tributaria de Ecuador**.

## 1. Estructura del Proyecto

La estructura del proyecto es idéntica a la del proyecto de referencia, organizada de la siguiente manera:

*   [main.py](main.py): Archivo principal que arranca la aplicación FastAPI, inicializa el cliente de **Supabase** como persistencia principal y define todos los endpoints.
*   **models/**: Modelos de Pydantic para la validación y tipado de datos.
    *   [models/empleado.py](models/empleado.py): Representa la entidad Empleado (cédula, nombres, sueldo básico, cuenta bancaria, etc.).
    *   [models/novedad.py](models/novedad.py): Registra las novedades del mes (anticipos, préstamos IESS, reembolsos, etc.).
    *   [models/nomina.py](models/nomina.py): Almacena los resultados del cálculo de la nómina y rol de pagos.
*   [requirements.txt](requirements.txt): Declaración de dependencias del proyecto.
*   [pyproject.toml](pyproject.toml): Configuración del proyecto en formato PEP 621.
*   [.env](.env): Archivo de variables de entorno para la integración con Supabase.
*   [.vscode/settings.json](.vscode/settings.json): Configuración del entorno de Python.

---

## 2. Requisitos Previos e Instalación

Para ejecutar este proyecto necesitas:

1.  Python 3.10 o superior.
2.  Instalar las dependencias:
    ```bash
    pip install -r requirements.txt
    ```

3.  Iniciar el servidor de desarrollo:
    ```bash
    uvicorn main:app --reload
    ```

La API y su documentación interactiva estarán disponibles en:
*   **API**: http://127.0.0.1:8000
*   **Swagger UI (Docs)**: http://127.0.0.1:8000/docs
*   **ReDoc**: http://127.0.0.1:8000/redoc

---

## 3. Normativa Laboral Ecuatoriana Aplicada

El cálculo de nómina aplica de forma automática las siguientes fórmulas legales y beneficios del Ecuador:

1.  **Sueldo Básico Unificado (SBU)**: Configurado en **$460.00** (vigente para el año 2026).
2.  **Aporte Personal al IESS**: Se deduce el **9.45%** de los ingresos gravables (Sueldo Básico + Bonificaciones).
3.  **Décimo Tercer Sueldo (Aguinaldo)**: Equivalente a la doceava parte de las remuneraciones del mes (`(Sueldo Básico + Bonificaciones) / 12`), si el empleado tiene habilitado el pago mensualizado.
4.  **Décimo Cuarto Sueldo (Bono Escolar)**: Equivalente a la doceava parte del SBU (`460.00 / 12 = $38.33`), si el empleado tiene habilitado el pago mensualizado.
5.  **Fondos de Reserva**: Equivalente al **8.33%** de los ingresos gravables, si el empleado tiene habilitado el pago mensualizado.

---

## 4. Endpoints Disponibles

### 4.1 Gestión de Empleados (RF-1)
*   `GET /empleados/`: Obtiene la lista completa de empleados (de Supabase o fallback local).
*   `GET /empleados/{cedula}`: Obtiene el detalle de un empleado mediante su cédula.
*   `POST /empleados/`: Registra un nuevo empleado (recibe formato JSON).
*   `POST /empleados_form/`: Registra un nuevo empleado recibiendo campos desde un formulario HTML. Valida que el sueldo no sea menor al SBU y evita cédulas duplicadas.
*   `PUT /empleados/{cedula}`: Actualiza los datos de un empleado.
*   `DELETE /empleados/{cedula}`: Elimina a un empleado del sistema.

### 4.2 Registro de Novedades (RF-2)
*   `GET /novedades/`: Obtiene todas las novedades registradas.
*   `POST /novedades/`: Registra novedades mensuales (anticipos, préstamos IESS, descuentos, reembolsos) para un empleado específico en un período. Valida que el empleado exista previamente.

### 4.3 Procesamiento de Nómina (RF-3 a RF-10)
*   `POST /nominas/calcular/{periodo}`: Calcula de forma automática la nómina de todos los empleados para un período (ej: `2026-07`). Aplica las fórmulas legales, aplica los descuentos correspondientes (verificando que no den valores negativos) e inserta/actualiza los registros de nómina. **(RF-3, RF-4, RF-8)**
*   `GET /nominas/historico/`: Recupera el histórico de nóminas generadas. Permite filtrar por parámetro de consulta `periodo`. **(RF-10)**
*   `GET /nominas/reporte/{cedula}/{periodo}`: Genera el **Rol de Pagos** individual (reporte) de un empleado para un período específico. **(RF-9)**
*   `POST /nominas/conciliar-anticipos/{periodo}`: Cruza automáticamente una lista de transacciones bancarias (cuenta bancaria, monto, referencia) contra los anticipos registrados en el período y devuelve el reporte de conciliación. **(RF-5)**
*   `GET /nominas/archivo-sat/{periodo}`: Genera y descarga un archivo plano (.txt) compatible con el sistema de transferencias bancarias SAT. **(RF-6)**
*   `POST /nominas/{nomina_id}/registrar-pago`: Actualiza el estado de la nómina a `procesado` o `fallido`. En caso de fallo, registra el error y simula una alerta/notificación en el sistema. **(RF-7)**

---

## 5. Persistencia y Robustez

El proyecto está diseñado para funcionar en dos modalidades de forma transparente:
1.  **Conexión a Supabase (Producción/Integración)**: Si las credenciales en el archivo `.env` son correctas y las tablas correspondientes (`empleado`, `novedad`, `nomina`) existen en tu instancia de Supabase, la API persistirá y consumirá los datos directamente de allí.
2.  **Fallback en Memoria (Pruebas Locales)**: Si la conexión a Supabase falla o las tablas no están creadas, la API maneja la excepción internamente y utiliza bases de datos locales simuladas en memoria para que puedas probar todos los endpoints sin interrupciones ni caídas del sistema.
