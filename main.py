import os
from typing import Annotated, List
from fastapi import FastAPI, Form, Response, HTTPException, status
from fastapi.responses import PlainTextResponse
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

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
supabase: Client | None = None

if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
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

# ENDPOINTS - GESTIÓN DE EMPLEADOS (RF-1)

@app.get("/empleados/", response_model=List[Empleado])
def listar_empleados():
    if supabase:
        try:
            res = supabase.table("empleado").select("*").execute()
            return res.data
        except Exception:
            pass  
    return fake_empleados_db


@app.get("/empleados/{cedula}", response_model=Empleado)
def obtener_empleado(cedula: str):
    if supabase:
        try:
            res = supabase.table("empleado").select("*").eq("cedula", cedula).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    for emp in fake_empleados_db:
        if emp["cedula"] == cedula:
            return emp
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


@app.post("/empleados/", response_model=Empleado)
def crear_empleado_json(empleado: Empleado):
    emp_dict = empleado.model_dump()

    if empleado.sueldo_basico < 0:
        raise HTTPException(status_code=400, detail="El sueldo básico no puede ser negativo")
        
    if supabase:
        try:
            res = supabase.table("empleado").insert(emp_dict).execute()
            return res.data[0]
        except Exception:
            pass

    if any(emp["cedula"] == empleado.cedula for emp in fake_empleados_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El empleado con cédula '{empleado.cedula}' ya existe."
        )
    fake_empleados_db.append(emp_dict)
    return emp_dict


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
    fondos_reserva: Annotated[bool, Form()] = True
):
    if sueldo_basico < 460.0:  
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El sueldo no puede ser menor al Salario Básico Unificado ($460)."
        )

    if any(emp["cedula"] == cedula for emp in fake_empleados_db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El empleado con cédula '{cedula}' ya existe."
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

    if supabase:
        try:
            res = supabase.table("empleado").insert(emp_dict).execute()
            return Response(
                content=f"Empleado '{nombres}' creado exitosamente en la base de datos.",
                status_code=status.HTTP_201_CREATED
            )
        except Exception:
            pass

    fake_empleados_db.append(emp_dict)
    return Response(
        content=f"Empleado '{nombres}' creado exitosamente en memoria.",
        status_code=status.HTTP_201_CREATED
    )


@app.put("/empleados/{cedula}", response_model=Empleado)
def actualizar_empleado(cedula: str, empleado: Empleado):
    emp_dict = empleado.model_dump()
    if supabase:
        try:
            res = supabase.table("empleado").update(emp_dict).eq("cedula", cedula).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    for i, emp in enumerate(fake_empleados_db):
        if emp["cedula"] == cedula:
            fake_empleados_db[i] = emp_dict
            return emp_dict
    raise HTTPException(status_code=404, detail="Empleado no encontrado")


@app.delete("/empleados/{cedula}")
def eliminar_empleado(cedula: str):
    if supabase:
        try:
            res = supabase.table("empleado").delete().eq("cedula", cedula).execute()
            if res.data:
                return {"status": "success", "message": f"Empleado {cedula} eliminado"}
        except Exception:
            pass

    for i, emp in enumerate(fake_empleados_db):
        if emp["cedula"] == cedula:
            fake_empleados_db.pop(i)
            return {"status": "success", "message": f"Empleado {cedula} eliminado de memoria"}
    raise HTTPException(status_code=404, detail="Empleado no encontrado")

# ENDPOINTS - NOVEDADES DE NÓMINA (RF-2)

@app.get("/novedades/", response_model=List[Novedad])
def listar_novedades():
    if supabase:
        try:
            res = supabase.table("novedad").select("*").execute()
            return res.data
        except Exception:
            pass
    return fake_novedades_db


@app.post("/novedades/", response_model=Novedad)
def registrar_novedad(novedad: Novedad):
    empleado_existe = False
    if supabase:
        try:
            res = supabase.table("empleado").select("*").eq("cedula", novedad.empleado_cedula).execute()
            if res.data:
                empleado_existe = True
        except Exception:
            pass
    
    if not empleado_existe:
        empleado_existe = any(emp["cedula"] == novedad.empleado_cedula for emp in fake_empleados_db)

    if not empleado_existe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede registrar novedad. El empleado con cédula '{novedad.empleado_cedula}' no existe."
        )

    nov_dict = novedad.model_dump()
    if supabase:
        try:
            res = supabase.table("novedad").insert(nov_dict).execute()
            return res.data[0]
        except Exception:
            pass

    new_id = max([n["id"] for n in fake_novedades_db], default=0) + 1
    nov_dict["id"] = new_id
    fake_novedades_db.append(nov_dict)
    return nov_dict

