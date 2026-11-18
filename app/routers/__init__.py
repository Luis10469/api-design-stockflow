from fastapi import APIRouter

from app.routers import categoria, movimientos_stock, producto, proveedores

api_router = APIRouter()
api_router.include_router(categoria.router)
api_router.include_router(proveedores.router)
api_router.include_router(producto.router)
api_router.include_router(movimientos_stock.router)

__all__ = ["api_router"]
