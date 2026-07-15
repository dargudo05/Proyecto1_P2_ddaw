from pydantic import BaseModel

class Nomina(BaseModel):
    id: int | None = None
    empleado_cedula: str
    periodo: str
    sueldo_basico: float
    bonificaciones: float
    reembolsos: float
    decimo_tercero: float
    decimo_cuarto: float
    fondos_reserva: float
    descuento_iess: float
    descuento_prestamos: float
    descuento_prestamo_iess: float
    descuento_anticipos: float
    otros_descuentos: float
    neto_pagar: float
    estado_pago: str = "pendiente"
