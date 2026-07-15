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

