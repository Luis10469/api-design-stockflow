from fastapi import APIRouter

from app.routers import proveedores

api_router = APIRouter()

# T-32: Router de Proveedores
api_router.include_router(proveedores.router)

# T-31: Router de Categorías (acepta tanto 'categorias' como 'categoria')
try:
    from app.routers import categorias

    api_router.include_router(categorias.router)
except ImportError:
    try:
        from app.routers import categoria

        api_router.include_router(categoria.router)
    except ImportError:
        pass

# T-33: Router de Productos (acepta tanto 'productos' como 'producto')
try:
    from app.routers import productos

    api_router.include_router(productos.router)
except ImportError:
    try:
        from app.routers import producto

        api_router.include_router(producto.router)
    except ImportError:
        pass

# T-34: Router de Movimientos de Stock
try:
    from app.routers import movimientos_stock

    api_router.include_router(movimientos_stock.router)
except ImportError:
    pass

__all__ = ["api_router"]
