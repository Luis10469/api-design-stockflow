from datetime import date, datetime

from fastapi import APIRouter, status

# 1. Inyección de dependencias (Capa api/deps)
from app.api.deps import MovimientoStockServiceDep

# 2. DTOs de entrada y salida (Capa models)
from app.models.movimiento_stock import MovimientoStockCreate, MovimientoStockPublic

# 3. Router de Movimientos de Stock
# Los movimientos son inmutables (README): no hay PATCH ni DELETE, así que
# FastAPI responde 405 Method Not Allowed si alguien intenta editar o borrar uno.
router = APIRouter(prefix="/movimientos-stock", tags=["Movimientos de Stock"])


@router.post(
    "/",
    response_model=MovimientoStockPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimiento",
    description=(
        "Registra una ENTRADA, SALIDA o AJUSTE y actualiza el stock del producto. "
        "Responde 404 si el producto no existe y 409 si una salida deja el stock en negativo."
    ),
)
async def create_movimiento(
    movimiento_in: MovimientoStockCreate,
    service: MovimientoStockServiceDep,
) -> MovimientoStockPublic:
    return await service.create(movimiento_in)


@router.get(
    "/",
    response_model=list[MovimientoStockPublic],
    summary="Listar movimientos",
    description=(
        "Lista paginada de movimientos, con filtros opcionales por producto, tipo y rango de fechas "
        "(ej. desde=2026-10-01&hasta=2026-10-31; una fecha sin hora cubre el día completo)."
    ),
)
async def list_movimientos(
    service: MovimientoStockServiceDep,
    skip: int = 0,
    limit: int = 100,
    id_producto: int | None = None,
    tipo: str | None = None,
    desde: date | datetime | None = None,
    hasta: date | datetime | None = None,
) -> list[MovimientoStockPublic]:
    return await service.list_all(
        skip=skip,
        limit=limit,
        id_producto=id_producto,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )


@router.get(
    "/{id_movimiento}",
    response_model=MovimientoStockPublic,
    summary="Obtener movimiento por ID",
    description="Busca un movimiento por ID o devuelve 404 si no existe.",
)
async def get_movimiento(
    id_movimiento: int,
    service: MovimientoStockServiceDep,
) -> MovimientoStockPublic:
    return await service.get_by_id(id_movimiento)
