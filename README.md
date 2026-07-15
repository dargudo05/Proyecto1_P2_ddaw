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

*   **`POST /nominas/calcular/{periodo}`** (RF-3, RF-4, RF-8)
    *   **Descripción**: Calcula de forma automática la nómina de todos los empleados para un período determinado (ej: `2026-07`). Aplica las fórmulas de ley (décimo tercero, décimo cuarto, aporte personal IESS, fondos de reserva) y resta los anticipos y préstamos correspondientes.
    *   **Validación**: Si el `neto_pagar` de algún empleado resulta menor a $0.00 debido a descuentos excesivos, el endpoint detiene el cálculo y lanza un error `HTTPException 400`.
    *   **Respuesta**: Devuelve una lista con los registros de la entidad `Nomina` generados o actualizados.

*   **`GET /nominas/historico/`** (RF-10)
    *   **Descripción**: Recupera el histórico de todas las nóminas generadas.
    *   **Parámetro de consulta**: `periodo` (opcional). Permite filtrar los registros por un mes/año específico (ej. `?periodo=2026-07`).

*   **`GET /nominas/reporte/{cedula}/{periodo}`** (RF-9)
    *   **Descripción**: Genera el **Rol de Pagos** individual (reporte) de un empleado para un período específico.
    *   **Respuesta**:
        ```json
        {
          "empleado": { ... },
          "nomina": { ... }
        }
        ```

*   **`POST /nominas/conciliar-anticipos/{periodo}`** (RF-5)
    *   **Descripción**: Cruza automáticamente una lista de transacciones bancarias contra los anticipos registrados en el período y devuelve un reporte detallado de conciliación.
    *   **Payload del Request** (`List[TransaccionBancaria]`):
        ```json
        [
          {
            "cuenta_bancaria": "1234567890",
            "monto": 200.0,
            "referencia": "TRANSF-001"
          }
        ]
        ```
    *   **Respuesta (Reporte)**:
        *   `conciliados`: Transacciones que coincidieron en cuenta y monto.
        *   `inconsistencias`: Errores encontrados (cuenta no asociada, montos dispares o empleados sin anticipo programado).
        *   `no_conciliados_sistema`: Anticipos registrados en el sistema que no se vieron reflejados en las transacciones bancarias recibidas.

*   **`GET /nominas/archivo-sat/{periodo}`** (RF-6)
    *   **Descripción**: Genera y descarga un archivo plano (.txt) compatible con el sistema de transferencias bancarias SAT.
    *   **Formato de salida**: Archivo plano separado por punto y coma (`;`):
        ```text
        cuenta_bancaria;monto;cedula;nombres;concepto
        1234567890;594.63;1723456789;Juan Pérez;PAGO_NOMINA_2026-07
        ```

*   **`POST /nominas/{nomina_id}/registrar-pago`** (RF-7)
    *   **Descripción**: Actualiza el estado de la nómina a `procesado` o `fallido`.
    *   **Payload del Request** (`RegistroPagoRequest`):
        ```json
        {
          "estado": "fallido",
          "error_mensaje": "Cuenta de destino inactiva"
        }
        ```
    *   **Simulación de Alertas**: En caso de estado `fallido`, registra e imprime en el sistema un mensaje de advertencia simulando una alerta/notificación inmediata a los administradores.

---


---

## 5. Persistencia y Robustez

El proyecto está diseñado para funcionar en dos modalidades de forma transparente:
1.  **Conexión a Supabase (Producción/Integración)**: Si las credenciales en el archivo `.env` son correctas y las tablas correspondientes (`empleado`, `novedad`, `nomina`) existen en tu instancia de Supabase, la API persistirá y consumirá los datos directamente de allí.
2.  **Fallback en Memoria (Pruebas Locales)**: Si la conexión a Supabase falla o las tablas no están creadas, la API maneja la excepción internamente y utiliza bases de datos locales simuladas en memoria para que puedas probar todos los endpoints sin interrupciones ni caídas del sistema.
