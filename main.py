import os
from typing import Annotated, List
from fastapi import FastAPI, Form, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

from models.empleado import Empleado
from models.novedad import Novedad
from models.nomina import Nomina

app = FastAPI(
    title="Sistema de Nómina API",
    description="API para la gestión de empleados, novedades y cálculo de nómina bajo normativa ecuatoriana.",
    version="1.0.0"
)

load_dotenv()

class AuthRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

security = HTTPBearer(auto_error=False)

supabase_url = os.getenv("SUPABASE_URL")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
supabase: Client | None = None


def create_supabase_client(access_token: str | None = None) -> Client:
    if not supabase_url or not supabase_anon_key:
        raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_ANON_KEY en el archivo .env")

    client = create_client(supabase_url, supabase_anon_key)
    if access_token:
        client.postgrest.auth(access_token)
    return client


def get_authenticated_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]
):
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere un token Bearer")

    try:
        client = create_supabase_client(creds.credentials)
        user_response = client.auth.get_user(creds.credentials)
        user = getattr(user_response, "user", None)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return {"user": user, "client": client}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado") from exc


if supabase_url and supabase_anon_key:
    try:
        supabase = create_supabase_client()
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")

fake_empleados_db = [
    {
        "cedula": "1723456789",
        "nombres": "Juan Pérez",
        "sueldo_basico": 800.0,
        "aporte_iess": 0.0945,
        "bonificaciones": 50.0,
        "cuenta_bancaria": "1234567890",
        "prestamos": 100.0,
        "decimos": True,
        "fondos_reserva": True
    },
    {
        "cedula": "0912345678",
        "nombres": "María López",
        "sueldo_basico": 1200.0,
        "aporte_iess": 0.0945,
        "bonificaciones": 150.0,
        "cuenta_bancaria": "0987654321",
        "prestamos": 0.0,
        "decimos": False,
        "fondos_reserva": False
    }
]

fake_novedades_db = [
    {
        "id": 1,
        "empleado_cedula": "1723456789",
        "anticipos": 200.0,
        "prestamo_iess": 50.0,
        "descuentos": 20.0,
        "reembolsos": 15.0,
        "periodo": "2026-07"
    }
]

fake_nominas_db = []

# ENDPOINTS - AUTENTICACIÓN

@app.post("/auth/signup", response_model=AuthResponse)
def signup(payload: AuthRequest):
    try:
        client = create_supabase_client()
        response = client.auth.sign_up({"email": payload.email, "password": payload.password})
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if not user:
            raise HTTPException(status_code=400, detail="No se pudo crear el usuario")
        user_data = user.model_dump() if hasattr(user, "model_dump") else user
        access_token = session.access_token if session else ""
        return AuthResponse(access_token=access_token, user=user_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest):
    try:
        client = create_supabase_client()
        response = client.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if not session or not user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        user_data = user.model_dump() if hasattr(user, "model_dump") else user
        return AuthResponse(access_token=session.access_token, user=user_data)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/me")
def get_me(auth: Annotated[dict, Depends(get_authenticated_user)]):
    return {"user": auth["user"]}


# ENDPOINTS - GESTIÓN DE EMPLEADOS (RF-1)

@app.get("/empleados/", response_model=List[Empleado])
def listar_empleados(auth: Annotated[dict, Depends(get_authenticated_user)]):
    try:
        res = auth["client"].table("empleado").select("*").execute()
        return res.data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo consultar Supabase: {exc}") from exc


@app.get("/empleados/{cedula}", response_model=Empleado)
def obtener_empleado(cedula: str, auth: Annotated[dict, Depends(get_authenticated_user)]):
    try:
        res = auth["client"].table("empleado").select("*").eq("cedula", cedula).execute()
        if res.data:
            return res.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo consultar Supabase: {exc}") from exc
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


@app.post("/empleados/", response_model=Empleado)
def crear_empleado_json(empleado: Empleado, auth: Annotated[dict, Depends(get_authenticated_user)]):
    emp_dict = empleado.model_dump()

    if empleado.sueldo_basico < 0:
        raise HTTPException(status_code=400, detail="El sueldo básico no puede ser negativo")

    try:
        res = auth["client"].table("empleado").insert(emp_dict).execute()
        return res.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el empleado en Supabase: {exc}") from exc


@app.post("/empleados_form/")
def crear_empleado_formulario(
    cedula: Annotated[str, Form()],
    nombres: Annotated[str, Form()],
    sueldo_basico: Annotated[float, Form()],
    cuenta_bancaria: Annotated[str, Form()],
    aporte_iess: Annotated[float, Form()] = 0.0945,
    bonificaciones: Annotated[float, Form()] = 0.0,
    prestamos: Annotated[float, Form()] = 0.0,
    decimos: Annotated[bool, Form()] = True,
    fondos_reserva: Annotated[bool, Form()] = True,
    auth: Annotated[dict, Depends(get_authenticated_user)] = None
):
    if sueldo_basico < 460.0:  
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El sueldo no puede ser menor al Salario Básico Unificado ($460)."
        )

    emp_dict = {
        "cedula": cedula,
        "nombres": nombres,
        "sueldo_basico": sueldo_basico,
        "aporte_iess": aporte_iess,
        "bonificaciones": bonificaciones,
        "cuenta_bancaria": cuenta_bancaria,
        "prestamos": prestamos,
        "decimos": decimos,
        "fondos_reserva": fondos_reserva
    }

    try:
        auth["client"].table("empleado").insert(emp_dict).execute()
        return Response(
            content=f"Empleado '{nombres}' creado exitosamente en la base de datos.",
            status_code=status.HTTP_201_CREATED
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el empleado en Supabase: {exc}") from exc


@app.put("/empleados/{cedula}", response_model=Empleado)
def actualizar_empleado(cedula: str, empleado: Empleado, auth: Annotated[dict, Depends(get_authenticated_user)]):
    emp_dict = empleado.model_dump()
    try:
        res = auth["client"].table("empleado").update(emp_dict).eq("cedula", cedula).execute()
        if res.data:
            return res.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo actualizar el empleado en Supabase: {exc}") from exc
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


@app.delete("/empleados/{cedula}")
def eliminar_empleado(cedula: str, auth: Annotated[dict, Depends(get_authenticated_user)]):
    try:
        res = auth["client"].table("empleado").delete().eq("cedula", cedula).execute()
        if res.data:
            return {"status": "success", "message": f"Empleado {cedula} eliminado"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar el empleado en Supabase: {exc}") from exc
    raise HTTPException(status_code=404, detail="Empleado no encontrado")

# ENDPOINTS - NOVEDADES DE NÓMINA (RF-2)

@app.get("/novedades/", response_model=List[Novedad])
def listar_novedades(auth: Annotated[dict, Depends(get_authenticated_user)]):
    try:
        res = auth["client"].table("novedad").select("*").execute()
        return res.data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo consultar las novedades en Supabase: {exc}") from exc


@app.post("/novedades/", response_model=Novedad)
def registrar_novedad(novedad: Novedad, auth: Annotated[dict, Depends(get_authenticated_user)]):
    empleado_existe = False
    try:
        res = auth["client"].table("empleado").select("*").eq("cedula", novedad.empleado_cedula).execute()
        if res.data:
            empleado_existe = True
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo validar el empleado en Supabase: {exc}") from exc

    if not empleado_existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede registrar novedad. El empleado con cédula '{novedad.empleado_cedula}' no existe."
        )

    nov_dict = novedad.model_dump()
    try:
        res = auth["client"].table("novedad").insert(nov_dict).execute()
        return res.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear la novedad en Supabase: {exc}") from exc


# ENDPOINTS - PROCESAMIENTO DE NÓMINA (RF-3 a RF-10)

class TransaccionBancaria(BaseModel):
    cuenta_bancaria: str
    monto: float
    referencia: str


class RegistroPagoRequest(BaseModel):
    estado: str
    error_mensaje: str | None = None


@app.post("/nominas/calcular/{periodo}", response_model=List[Nomina])
def calcular_nomina(periodo: str):
    # 1. Fetch all employees
    empleados = []
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            empleados = res.data
        except Exception as e:
            print(f"Error fetching employees from Supabase: {e}")
            empleados = fake_empleados_db
    else:
        empleados = fake_empleados_db

    # 2. Fetch all novelties for the period
    novedades = []
    if supabase:
        try:
            res = supabase.table("novedad").select("*").eq("periodo", periodo).execute()
            novedades = res.data
        except Exception as e:
            print(f"Error fetching novelties from Supabase: {e}")
            novedades = [n for n in fake_novedades_db if n.get("periodo") == periodo]
    else:
        novedades = [n for n in fake_novedades_db if n.get("periodo") == periodo]

    novedades_map = {n["empleado_cedula"]: n for n in novedades}
    resultados = []

    for emp in empleados:
        cedula = emp["cedula"]
        sueldo_basico = float(emp["sueldo_basico"])
        aporte_iess_pct = float(emp.get("aporte_iess") if emp.get("aporte_iess") is not None else 0.0945)
        bonificaciones = float(emp.get("bonificaciones") if emp.get("bonificaciones") is not None else 0.0)
        prestamos = float(emp.get("prestamos") if emp.get("prestamos") is not None else 0.0)
        decimos_enabled = bool(emp.get("decimos", True))
        fondos_reserva_enabled = bool(emp.get("fondos_reserva", True))

        # Get novelty details
        nov = novedades_map.get(cedula, {})
        anticipos = float(nov.get("anticipos") if nov.get("anticipos") is not None else 0.0)
        prestamo_iess = float(nov.get("prestamo_iess") if nov.get("prestamo_iess") is not None else 0.0)
        descuentos_nov = float(nov.get("descuentos") if nov.get("descuentos") is not None else 0.0)
        reembolsos = float(nov.get("reembolsos") if nov.get("reembolsos") is not None else 0.0)

        # Calculations under Ecuadorian law
        ingresos_gravables = sueldo_basico + bonificaciones
        descuento_iess = round(ingresos_gravables * aporte_iess_pct, 2)
        decimo_tercero = round(ingresos_gravables / 12.0, 2) if decimos_enabled else 0.0
        decimo_cuarto = round(460.00 / 12.0, 2) if decimos_enabled else 0.0
        fondos_reserva = round(ingresos_gravables * 0.0833, 2) if fondos_reserva_enabled else 0.0

        # Egresos/Descuentos
        descuento_prestamos = prestamos
        descuento_prestamo_iess = prestamo_iess
        descuento_anticipos = anticipos
        otros_descuentos = descuentos_nov

        total_ingresos = sueldo_basico + bonificaciones + decimo_tercero + decimo_cuarto + fondos_reserva + reembolsos
        total_egresos = descuento_iess + descuento_prestamos + descuento_prestamo_iess + descuento_anticipos + otros_descuentos
        neto_pagar = round(total_ingresos - total_egresos, 2)

        if neto_pagar < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cálculo de nómina fallido para el empleado '{emp['nombres']}' ({cedula}): El neto a pagar no puede ser negativo ({neto_pagar})."
            )

        nomina_data = {
            "empleado_cedula": cedula,
            "periodo": periodo,
            "sueldo_basico": sueldo_basico,
            "bonificaciones": bonificaciones,
            "reembolsos": reembolsos,
            "decimo_tercero": decimo_tercero,
            "decimo_cuarto": decimo_cuarto,
            "fondos_reserva": fondos_reserva,
            "descuento_iess": descuento_iess,
            "descuento_prestamos": descuento_prestamos,
            "descuento_prestamo_iess": descuento_prestamo_iess,
            "descuento_anticipos": descuento_anticipos,
            "otros_descuentos": otros_descuentos,
            "neto_pagar": neto_pagar,
            "estado_pago": "pendiente"
        }
        
        resultados.append(nomina_data)

    saved_resultados = []
    if supabase:
        for nom in resultados:
            try:
                # Check if already exists in Supabase
                res_check = supabase.table("nomina").select("*").eq("empleado_cedula", nom["empleado_cedula"]).eq("periodo", periodo).execute()
                if res_check.data:
                    existing_id = res_check.data[0]["id"]
                    res_upd = supabase.table("nomina").update(nom).eq("id", existing_id).execute()
                    saved_resultados.append(res_upd.data[0])
                else:
                    res_ins = supabase.table("nomina").insert(nom).execute()
                    saved_resultados.append(res_ins.data[0])
            except Exception as e:
                print(f"Error saving nomina to Supabase: {e}")
                # Fallback to memory
                existing_idx = None
                for idx, fn in enumerate(fake_nominas_db):
                    if fn["empleado_cedula"] == nom["empleado_cedula"] and fn["periodo"] == periodo:
                        existing_idx = idx
                        break
                if existing_idx is not None:
                    nom["id"] = fake_nominas_db[existing_idx].get("id")
                    fake_nominas_db[existing_idx] = nom
                else:
                    new_id = max([n.get("id", 0) for n in fake_nominas_db], default=0) + 1
                    nom["id"] = new_id
                    fake_nominas_db.append(nom)
                saved_resultados.append(nom)
    else:
        for nom in resultados:
            existing_idx = None
            for idx, fn in enumerate(fake_nominas_db):
                if fn["empleado_cedula"] == nom["empleado_cedula"] and fn["periodo"] == periodo:
                    existing_idx = idx
                    break
            if existing_idx is not None:
                nom["id"] = fake_nominas_db[existing_idx].get("id")
                fake_nominas_db[existing_idx] = nom
            else:
                new_id = max([n.get("id", 0) for n in fake_nominas_db], default=0) + 1
                nom["id"] = new_id
                fake_nominas_db.append(nom)
            saved_resultados.append(nom)

    return saved_resultados


@app.get("/nominas/historico/", response_model=List[Nomina])
def obtener_historico_nominas(periodo: str | None = None):
    if supabase:
        try:
            query = supabase.table("nomina").select("*")
            if periodo:
                query = query.eq("periodo", periodo)
            res = query.execute()
            return res.data
        except Exception as e:
            print(f"Error fetching historical nominas from Supabase: {e}")

    if periodo:
        return [n for n in fake_nominas_db if n["periodo"] == periodo]
    return fake_nominas_db


@app.get("/nominas/reporte/{cedula}/{periodo}")
def obtener_reporte_rol_pagos(cedula: str, periodo: str):
    empleado = None
    if supabase:
        try:
            res = supabase.table("empleado").select("*").eq("cedula", cedula).execute()
            if res.data:
                empleado = res.data[0]
        except Exception:
            pass
    if not empleado:
        for emp in fake_empleados_db:
            if emp["cedula"] == cedula:
                empleado = emp
                break
    
    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con cédula '{cedula}' no encontrado."
        )

    nomina = None
    if supabase:
        try:
            res = supabase.table("nomina").select("*").eq("empleado_cedula", cedula).eq("periodo", periodo).execute()
            if res.data:
                nomina = res.data[0]
        except Exception:
            pass
    if not nomina:
        for nom in fake_nominas_db:
            if nom["empleado_cedula"] == cedula and nom["periodo"] == periodo:
                nomina = nom
                break
                
    if not nomina:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nómina no encontrada para el empleado '{cedula}' en el período '{periodo}'."
        )

    return {
        "empleado": empleado,
        "nomina": nomina
    }


@app.post("/nominas/conciliar-anticipos/{periodo}")
def conciliar_anticipos(periodo: str, transacciones: List[TransaccionBancaria]):
    empleados = []
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            empleados = res.data
        except Exception:
            pass
    if not empleados:
        empleados = fake_empleados_db

    novedades = []
    if supabase:
        try:
            res = supabase.table("novedad").select("*").eq("periodo", periodo).execute()
            novedades = res.data
        except Exception:
            pass
    if not novedades:
        novedades = [n for n in fake_novedades_db if n.get("periodo") == periodo]

    empleados_by_cuenta = {emp["cuenta_bancaria"]: emp for emp in empleados}
    novedades_by_cedula = {n["empleado_cedula"]: n for n in novedades}

    conciliados = []
    inconsistencias = []
    cuentas_procesadas = set()

    for tx in transacciones:
        cuenta = tx.cuenta_bancaria
        monto = tx.monto
        ref = tx.referencia

        emp = empleados_by_cuenta.get(cuenta)
        if not emp:
            inconsistencias.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "tipo_error": "Cuenta bancaria no asociada a ningún empleado"
            })
            continue

        cedula = emp["cedula"]
        nombres = emp["nombres"]
        cuentas_procesadas.add(cuenta)

        nov = novedades_by_cedula.get(cedula)
        anticipo_registrado = float(nov["anticipos"]) if (nov and nov.get("anticipos") is not None) else 0.0

        if anticipo_registrado == 0.0:
            inconsistencias.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "empleado_cedula": cedula,
                "empleado_nombres": nombres,
                "tipo_error": f"El empleado no tiene anticipos registrados para el período {periodo}"
            })
        elif round(anticipo_registrado, 2) == round(monto, 2):
            conciliados.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "empleado_cedula": cedula,
                "empleado_nombres": nombres
            })
        else:
            inconsistencias.append({
                "cuenta_bancaria": cuenta,
                "monto": monto,
                "referencia": ref,
                "empleado_cedula": cedula,
                "empleado_nombres": nombres,
                "tipo_error": f"El monto de la transacción ({monto}) no coincide con el anticipo registrado ({anticipo_registrado})"
            })

    no_conciliados_sistema = []
    for nov in novedades:
        cedula = nov["empleado_cedula"]
        anticipos = float(nov.get("anticipos", 0.0) or 0.0)
        if anticipos > 0.0:
            emp_for_nov = None
            for e in empleados:
                if e["cedula"] == cedula:
                    emp_for_nov = e
                    break
            
            if emp_for_nov:
                cuenta = emp_for_nov["cuenta_bancaria"]
                if cuenta not in cuentas_procesadas:
                    no_conciliados_sistema.append({
                        "empleado_cedula": cedula,
                        "empleado_nombres": emp_for_nov["nombres"],
                        "cuenta_bancaria": cuenta,
                        "anticipo_registrado": anticipos
                    })

    return {
        "periodo": periodo,
        "total_transacciones_recibidas": len(transacciones),
        "conciliados": conciliados,
        "inconsistencias": inconsistencias,
        "no_conciliados_sistema": no_conciliados_sistema
    }


@app.get("/nominas/archivo-sat/{periodo}")
def descargar_archivo_sat(periodo: str):
    nominas = []
    if supabase:
        try:
            res = supabase.table("nomina").select("*").eq("periodo", periodo).execute()
            nominas = res.data
        except Exception:
            pass
    if not nominas:
        nominas = [n for n in fake_nominas_db if n["periodo"] == periodo]

    if not nominas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron registros de nómina para el período '{periodo}'. Calcule la nómina primero."
        )

    empleados = []
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            empleados = res.data
        except Exception:
            pass
    if not empleados:
        empleados = fake_empleados_db

    emp_map = {emp["cedula"]: emp for emp in empleados}

    lines = []
    for nom in nominas:
        cedula = nom["empleado_cedula"]
        neto_pagar = nom["neto_pagar"]
        emp = emp_map.get(cedula)
        
        cuenta = emp["cuenta_bancaria"] if emp else "SIN_CUENTA"
        nombres = emp["nombres"] if emp else "Empleado Desconocido"
        
        line = f"{cuenta};{neto_pagar:.2f};{cedula};{nombres};PAGO_NOMINA_{periodo}"
        lines.append(line)

    content = "\n".join(lines)
    
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=archivo_sat_{periodo}.txt"
        }
    )


@app.post("/nominas/{nomina_id}/registrar-pago")
def registrar_pago_nomina(nomina_id: int, req: RegistroPagoRequest):
    if req.estado not in ["procesado", "fallido"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estado de pago debe ser 'procesado' o 'fallido'."
        )

    updated_nomina = None
    alerta = None

    if supabase:
        try:
            res_check = supabase.table("nomina").select("*").eq("id", nomina_id).execute()
            if res_check.data:
                res_upd = supabase.table("nomina").update({"estado_pago": req.estado}).eq("id", nomina_id).execute()
                if res_upd.data:
                    updated_nomina = res_upd.data[0]
        except Exception as e:
            print(f"Error updating payment state in Supabase: {e}")

    if not updated_nomina:
        for idx, nom in enumerate(fake_nominas_db):
            if nom.get("id") == nomina_id:
                fake_nominas_db[idx]["estado_pago"] = req.estado
                updated_nomina = fake_nominas_db[idx]
                break

    if not updated_nomina:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro de nómina con ID {nomina_id} no encontrado."
        )

    if req.estado == "fallido":
        alerta = f"ALERTA DEL SISTEMA: El pago de la nómina con ID {nomina_id} (Empleado: {updated_nomina.get('empleado_cedula')}) ha fallado. Detalle del error: {req.error_mensaje or 'Sin especificar'}"
        print(alerta)

    response_data = {
        "status": "success",
        "message": f"Estado de pago de nómina {nomina_id} actualizado a '{req.estado}'.",
        "nomina": updated_nomina
    }
    if alerta:
        response_data["alerta_simulada"] = alerta

    return response_data


