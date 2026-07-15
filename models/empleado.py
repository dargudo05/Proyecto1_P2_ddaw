from pydantic import BaseModel

class Empleado(BaseModel):
    id: int | None = None
    cedula: str
    nombres: str
    sueldo_basico: float
    aporte_iess: float | None = 0.0945
    bonificaciones: float | None = 0.0
    cuenta_bancaria: str
    prestamos: float | None = 0.0
    decimos: bool | None = True
    fondos_reserva: bool | None = True
