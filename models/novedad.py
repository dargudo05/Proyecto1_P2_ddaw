from pydantic import BaseModel

class Novedad(BaseModel):
    id: int | None = None
    empleado_cedula: str
    anticipos: float | None = 0.0
    prestamo_iess: float | None = 0.0
    descuentos: float | None = 0.0
    reembolsos: float | None = 0.0
    periodo: str
