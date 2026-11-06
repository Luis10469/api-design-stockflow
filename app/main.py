import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path al ejecutar directamente como script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker, get_session, init_db
from app.models.movimiento_stock import MovimientoStockCreate
from app.models.producto import ProductoCreate, ProductoUpdate
from app.models.proveedor import ProveedorCreate, ProveedorUpdate
from app.repositories import (
    CategoriaRepository,
    MovimientoStockRepository,
    ProductoRepository,
    ProveedorRepository,
)


async def probar_repositorios(session: AsyncSession) -> dict:
    """Ejecuta la prueba integral de la capa de repositorios (Tarea T-23).

    Fases:
      1. Crear: Categoría, Proveedor, 2 Productos y un Movimiento de ENTRADA.
      2. Buscar: Por ID, Nombre, SKU y Filtros.
      3. Editar: Categoría, Proveedor y un Producto.
      4. Borrar: Producto sin movimientos y comprobar que ya no existe,
         manteniendo intactos el Producto 1 y su Movimiento de entrada.
    """
    repo_cat = CategoriaRepository(session)
    repo_prov = ProveedorRepository(session)
    repo_prod = ProductoRepository(session)
    repo_mov = MovimientoStockRepository(session)

    sufijo = uuid.uuid4().hex[:6].upper()
    print(f"\n=======================================================")
    print(f"  EJECUTANDO PRUEBA DE REPOSITORIOS (Sufijo: {sufijo})")
    print(f"=======================================================\n")

    # ------------------------------------------------------------------
    # FASE 1: CREAR
    # ------------------------------------------------------------------
    print("--- FASE 1: CREAR ---")

    # 1. Crear Categoría
    cat_data = {
        "nombre": f"Cat-{sufijo}",
        "descripcion": f"Categoría de prueba {sufijo}",
    }
    cat = await repo_cat.create(cat_data)
    print(f"[OK] Categoría creada: ID={cat.id_categoria}, Nombre='{cat.nombre}'")

    # 2. Crear Proveedor
    prov_in = ProveedorCreate(
        nombre=f"Proveedor-{sufijo}",
        telefono="3001234567",
        correo=f"prov_{sufijo.lower()}@test.com",
        direccion=f"Calle 10 # {sufijo}",
        origen="Medellín",
    )
    prov = await repo_prov.create(prov_in)
    print(f"[OK] Proveedor creado: ID={prov.id_proveedor}, Nombre='{prov.nombre}'")

    # 3. Crear 2 Productos asociados
    prod1_in = ProductoCreate(
        sku=f"SKU-1-{sufijo}",
        nombre=f"Prod-Mov-{sufijo}",
        precio=45000.0,
        costo=25000.0,
        stock_minimo=5,
        id_categoria=cat.id_categoria,
        id_proveedor=prov.id_proveedor,
    )
    prod1 = await repo_prod.create(prod1_in)
    print(f"[OK] Producto 1 (con movimiento) creado: ID={prod1.id_producto}, SKU='{prod1.sku}'")

    prod2_in = ProductoCreate(
        sku=f"SKU-2-{sufijo}",
        nombre=f"Prod-SinMov-{sufijo}",
        precio=15000.0,
        costo=8000.0,
        stock_minimo=2,
        id_categoria=cat.id_categoria,
        id_proveedor=prov.id_proveedor,
    )
    prod2 = await repo_prod.create(prod2_in)
    print(f"[OK] Producto 2 (sin movimiento) creado: ID={prod2.id_producto}, SKU='{prod2.sku}'")

    # 4. Crear un Movimiento de Entrada para Producto 1
    mov_in = MovimientoStockCreate(
        id_producto=prod1.id_producto,
        tipo="ENTRADA",
        cantidad=25,
        motivo=f"Entrada inicial lote {sufijo}",
    )
    mov = await repo_mov.create(mov_in)
    print(f"[OK] Movimiento creado: ID={mov.id_movimiento}, Tipo='{mov.tipo}', Cantidad={mov.cantidad}, ID Producto={mov.id_producto}")

    # ------------------------------------------------------------------
    # FASE 2: BUSCAR
    # ------------------------------------------------------------------
    print("\n--- FASE 2: BUSCAR ---")

    # 1. Por ID
    b_cat_id = await repo_cat.get_by_id(cat.id_categoria)
    assert b_cat_id is not None, "Error: Categoría no encontrada por ID"
    print(f"[OK] Categoría encontrada por ID: {b_cat_id.nombre}")

    b_prov_id = await repo_prov.get_by_id(prov.id_proveedor)
    assert b_prov_id is not None, "Error: Proveedor no encontrado por ID"
    print(f"[OK] Proveedor encontrado por ID: {b_prov_id.nombre}")

    b_prod1_id = await repo_prod.get_by_id(prod1.id_producto)
    assert b_prod1_id is not None, "Error: Producto 1 no encontrado por ID"
    print(f"[OK] Producto 1 encontrado por ID: {b_prod1_id.nombre}")

    b_prod2_id = await repo_prod.get_by_id(prod2.id_producto)
    assert b_prod2_id is not None, "Error: Producto 2 no encontrado por ID"
    print(f"[OK] Producto 2 encontrado por ID: {b_prod2_id.nombre}")

    b_mov_id = await repo_mov.get_by_id(mov.id_movimiento)
    assert b_mov_id is not None, "Error: Movimiento no encontrado por ID"
    print(f"[OK] Movimiento encontrado por ID: {b_mov_id.motivo}")

    # 2. Por Nombre
    b_cat_nom = await repo_cat.get_by_nombre(cat.nombre)
    assert b_cat_nom is not None and b_cat_nom.id_categoria == cat.id_categoria, "Error al buscar categoría por nombre"
    print(f"[OK] Categoría encontrada por Nombre: {b_cat_nom.nombre}")

    b_prov_nom = await repo_prov.get_by_nombre(prov.nombre)
    assert b_prov_nom is not None and b_prov_nom.id_proveedor == prov.id_proveedor, "Error al buscar proveedor por nombre"
    print(f"[OK] Proveedor encontrado por Nombre: {b_prov_nom.nombre}")

    # 3. Por SKU
    b_prod1_sku = await repo_prod.get_by_sku(prod1.sku)
    assert b_prod1_sku is not None and b_prod1_sku.id_producto == prod1.id_producto, "Error al buscar producto 1 por SKU"
    print(f"[OK] Producto 1 encontrado por SKU: {b_prod1_sku.sku}")

    b_prod2_sku = await repo_prod.get_by_sku(prod2.sku)
    assert b_prod2_sku is not None and b_prod2_sku.id_producto == prod2.id_producto, "Error al buscar producto 2 por SKU"
    print(f"[OK] Producto 2 encontrado por SKU: {b_prod2_sku.sku}")

    # 4. Por Filtros
    prods_filtrados = await repo_prod.get_multi(
        id_categoria=cat.id_categoria,
        id_proveedor=prov.id_proveedor,
    )
    assert len(prods_filtrados) >= 2, "Error: Filtro de productos no devolvió los productos creados"
    print(f"[OK] Filtro productos (por categoría y proveedor): {len(prods_filtrados)} encontrados")

    movs_filtrados = await repo_mov.get_multi(
        id_producto=prod1.id_producto,
        tipo="ENTRADA",
    )
    assert len(movs_filtrados) >= 1, "Error: Filtro de movimientos no devolvió el movimiento"
    print(f"[OK] Filtro movimientos (por producto y tipo ENTRADA): {len(movs_filtrados)} encontrados")

    provs_filtrados = await repo_prov.get_multi(origen="Medellín")
    assert any(p.id_proveedor == prov.id_proveedor for p in provs_filtrados), "Error: Filtro de proveedor no devolvió el proveedor"
    print(f"[OK] Filtro proveedores (por origen Medellín): {len(provs_filtrados)} encontrados")

    # ------------------------------------------------------------------
    # FASE 3: EDITAR
    # ------------------------------------------------------------------
    print("\n--- FASE 3: EDITAR ---")

    # 1. Editar Categoría
    cat_edit_nom = f"Cat-Editada-{sufijo}"
    cat_editada = await repo_cat.update(
        cat.id_categoria,
        {"nombre": cat_edit_nom, "descripcion": "Descripción actualizada"},
    )
    assert cat_editada is not None and cat_editada.nombre == cat_edit_nom, "Error al editar categoría"
    print(f"[OK] Categoría editada: Nuevo Nombre='{cat_editada.nombre}'")

    # 2. Editar Proveedor
    prov_edit_tel = "3119876543"
    prov_editado = await repo_prov.update(
        prov,
        ProveedorUpdate(telefono=prov_edit_tel, direccion="Calle 100 Editada"),
    )
    assert prov_editado is not None and prov_editado.telefono == prov_edit_tel, "Error al editar proveedor"
    print(f"[OK] Proveedor editado: Nuevo Teléfono='{prov_editado.telefono}'")

    # 3. Editar Producto 1
    prod1_edit_precio = 52000.0
    prod1_editado = await repo_prod.update(
        prod1,
        ProductoUpdate(precio=prod1_edit_precio, stock_minimo=10),
    )
    assert prod1_editado is not None and prod1_editado.precio == prod1_edit_precio, "Error al editar producto 1"
    print(f"[OK] Producto 1 editado: Nuevo Precio={prod1_editado.precio}")

    # ------------------------------------------------------------------
    # FASE 4: BORRAR
    # ------------------------------------------------------------------
    print("\n--- FASE 4: BORRAR ---")

    # 1. Borrar Producto 2 (el producto sin movimientos)
    await repo_prod.delete(prod2)
    print(f"[OK] Producto 2 (ID={prod2.id_producto}, sin movimientos) eliminado del repositorio")

    # 2. Comprobar que ya no está
    prod2_verif = await repo_prod.get_by_id(prod2.id_producto)
    assert prod2_verif is None, "Error: Producto 2 todavía existe en la base de datos"
    prod2_sku_verif = await repo_prod.get_by_sku(prod2.sku)
    assert prod2_sku_verif is None, "Error: Producto 2 todavía se encuentra por SKU"
    print("[OK] Comprobado: Producto 2 ya no existe en la base de datos (get_by_id retornó None)")

    # 3. Comprobar que Producto 1 y su Movimiento siguen existiendo (integridad referencial)
    prod1_sigue = await repo_prod.get_by_id(prod1.id_producto)
    assert prod1_sigue is not None, "Error: Producto 1 desapareció"
    mov_sigue = await repo_mov.get_by_id(mov.id_movimiento)
    assert mov_sigue is not None, "Error: Movimiento desapareció"
    print(f"[OK] Integridad preservada: Producto 1 (ID={prod1_sigue.id_producto}) y su Movimiento (ID={mov_sigue.id_movimiento}) se mantienen intactos")

    print(f"\n=======================================================")
    print(f"  PRUEBA T-23 FINALIZADA EXITOSAMENTE (Sufijo: {sufijo})")
    print(f"=======================================================\n")

    return {
        "status": "success",
        "mensaje": f"Prueba de los 4 repositorios completada exitosamente (Sufijo: {sufijo})",
        "datos": {
            "sufijo": sufijo,
            "categoria": {"id": cat.id_categoria, "nombre": cat_editada.nombre},
            "proveedor": {"id": prov.id_proveedor, "nombre": prov.nombre, "telefono": prov_editado.telefono},
            "producto_1_conservado": {"id": prod1.id_producto, "sku": prod1.sku, "precio": prod1_editado.precio},
            "movimiento_entrada": {"id": mov.id_movimiento, "tipo": mov.tipo, "cantidad": mov.cantidad},
            "producto_2_eliminado": {"id": prod2.id_producto, "sku": prod2.sku, "comprobacion_borrado": "get_by_id retornó None"},
        },
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)


@app.get(
    "/test-repositorios",
    tags=["Pruebas"],
    summary="T-23: Prueba integral de la capa de repositorios",
)
async def endpoint_test_repositorios(
    session: AsyncSession = Depends(get_session),
):
    """Ejecuta la prueba de los 4 repositorios (Categoría, Proveedor, Producto, MovimientoStock).

    Verifica creación, búsqueda, edición y borrado respetando la integridad referencial.
    """
    return await probar_repositorios(session)


if __name__ == "__main__":
    import asyncio

    async def main_cli() -> None:
        await init_db()
        async with async_session_maker() as session:
            await probar_repositorios(session)

    asyncio.run(main_cli())
