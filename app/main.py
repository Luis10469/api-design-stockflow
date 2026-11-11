import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path al ejecutar directamente como script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker, get_session, init_db
from app.models.movimiento_stock import MovimientoStockCreate
from app.models.categoria import CategoriaCreate
from app.services import (
    CategoriaService,
    ProveedorService,
    ProductoService,
    MovimientoStockService,
)
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




async def probar_servicios(session: AsyncSession) -> dict:
    """T-29: Prueba integral de la capa de servicios."""

    repo_cat = CategoriaRepository(session)
    repo_prov = ProveedorRepository(session)
    repo_prod = ProductoRepository(session)
    repo_mov = MovimientoStockRepository(session)

    servicio_cat = CategoriaService(repo_cat, repo_prod)
    servicio_prov = ProveedorService(repo_prov, repo_prod)
    servicio_prod = ProductoService(
        repo_prod, repo_cat, repo_prov, repo_mov
    )
    servicio_mov = MovimientoStockService(repo_mov, repo_prod)

    sufijo = uuid.uuid4().hex[:6].upper()

    print(f"\n========== T-29 SERVICIOS ({sufijo}) ==========")

    # PRUEBA 1: CREACIÓN COORDINADA
    categoria = await servicio_cat.create(
        CategoriaCreate(
            nombre=f"Categoria-T29-{sufijo}",
            descripcion="Prueba T-29",
        )
    )

    proveedor = await servicio_prov.create(
        ProveedorCreate(
            nombre=f"Proveedor-T29-{sufijo}",
            telefono="3001234567",
            correo=f"t29-{sufijo.lower()}@test.com",
            direccion="Calle de prueba",
            origen="Medellín",
        )
    )

    producto = await servicio_prod.create(
        ProductoCreate(
            sku=f"T29-{sufijo}",
            nombre=f"Producto-T29-{sufijo}",
            precio=50000.0,
            costo=30000.0,
            stock_minimo=5,
            id_categoria=categoria.id_categoria,
            id_proveedor=proveedor.id_proveedor,
        )
    )

    movimiento = await servicio_mov.create(
        MovimientoStockCreate(
            id_producto=producto.id_producto,
            tipo="ENTRADA",
            cantidad=10,
            motivo="Entrada inicial T-29",
        )
    )

    producto = await servicio_prod.get_by_id(producto.id_producto)

    assert producto.stock_actual == 10, "La entrada no actualizó el stock"
    print("[OK] PRUEBA 1: Creación coordinada y entrada de stock")

    # PRUEBA 2: CATEGORÍA DUPLICADA
    try:
        await servicio_cat.create(
            CategoriaCreate(
                nombre=f"Categoria-T29-{sufijo}",
                descripcion="Duplicada",
            )
        )
        raise AssertionError("Se permitió una categoría duplicada")
    except HTTPException as exc:
        assert exc.status_code == 409, f"Se esperaba 409, llegó {exc.status_code}"
        print("[OK] PRUEBA 2: Categoría duplicada = 409")

    # PRUEBA 3: SKU DUPLICADO
    try:
        await servicio_prod.create(
            ProductoCreate(
                sku=f"T29-{sufijo}",
                nombre=f"Duplicado-{sufijo}",
                precio=60000.0,
                costo=35000.0,
                stock_minimo=5,
                id_categoria=categoria.id_categoria,
                id_proveedor=proveedor.id_proveedor,
            )
        )
        raise AssertionError("Se permitió un SKU duplicado")
    except HTTPException as exc:
        assert exc.status_code == 409, f"Se esperaba 409, llegó {exc.status_code}"
        print("[OK] PRUEBA 3: SKU duplicado = 409")

    # PRUEBA 4: SALIDA MAYOR AL STOCK
    stock_anterior = producto.stock_actual

    try:
        await servicio_mov.create(
            MovimientoStockCreate(
                id_producto=producto.id_producto,
                tipo="SALIDA",
                cantidad=stock_anterior + 100,
                motivo="Salida de prueba sin stock",
            )
        )
        raise AssertionError("Se permitió una salida sin stock")
    except HTTPException as exc:
        assert exc.status_code == 409, f"Se esperaba 409, llegó {exc.status_code}"

    producto_despues = await servicio_prod.get_by_id(producto.id_producto)

    assert producto_despues.stock_actual == stock_anterior, (
        "El stock cambió después de rechazar la salida"
    )
    print("[OK] PRUEBA 4: Salida rechazada = 409 y stock intacto")

    # PRUEBA 5: PRODUCTO INEXISTENTE
    try:
        await servicio_prod.get_by_id(999999)
        raise AssertionError("Se encontró un producto inexistente")
    except HTTPException as exc:
        assert exc.status_code == 404, f"Se esperaba 404, llegó {exc.status_code}"
        print("[OK] PRUEBA 5: Producto inexistente = 404")

    # PRUEBA 6A: BORRAR CATEGORÍA VACÍA
    categoria_vacia = await servicio_cat.create(
        CategoriaCreate(
            nombre=f"Categoria-Vacia-{sufijo}",
            descripcion="Prueba de borrado",
        )
    )

    await servicio_cat.delete(categoria_vacia.id_categoria)

    try:
        await servicio_cat.get_by_id(categoria_vacia.id_categoria)
        raise AssertionError("La categoría eliminada todavía existe")
    except HTTPException as exc:
        assert exc.status_code == 404, f"Se esperaba 404, llegó {exc.status_code}"

    print("[OK] PRUEBA 6A: Categoría eliminada = 404")

    # PRUEBA 6B: NO BORRAR CATEGORÍA CON PRODUCTOS
    try:
        await servicio_cat.delete(categoria.id_categoria)
        raise AssertionError("Se permitió borrar una categoría con productos")
    except HTTPException as exc:
        assert exc.status_code == 409, f"Se esperaba 409, llegó {exc.status_code}"

    print("[OK] PRUEBA 6B: Categoría con productos = 409")

    print("\n======================================")
    print(" T-29 FINALIZADA EXITOSAMENTE")
    print(" Se completaron las seis pruebas.")
    print("======================================\n")

    return {
        "status": "success",
        "mensaje": "T-29 completada exitosamente",
        "sufijo": sufijo,
        "pruebas": {
            "creacion_coordinada": "OK",
            "categoria_duplicada_409": "OK",
            "sku_duplicado_409": "OK",
            "stock_insuficiente_409": "OK",
            "producto_inexistente_404": "OK",
            "eliminacion_categoria_404_409": "OK",
        },
        "datos": {
            "id_categoria": categoria.id_categoria,
            "id_proveedor": proveedor.id_proveedor,
            "id_producto": producto.id_producto,
            "id_movimiento": movimiento.id_movimiento,
            "stock_final": producto_despues.stock_actual,
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
    "/health",
    tags=["Salud"],
    summary="Verificar el estado del servicio",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/test-repositories",
    tags=["Pruebas"],
    summary="T-23: Prueba integral de la capa de repositorios",
)
async def endpoint_test_repositories(
    session: AsyncSession = Depends(get_session),
):
    """Ejecuta la prueba de los 4 repositorios (Categoría, Proveedor, Producto, MovimientoStock).

    Verifica creación, búsqueda, edición y borrado respetando la integridad referencial.
    """
    return await probar_repositorios(session)


@app.post(
    "/test-services",
    tags=["Pruebas"],
    summary="T-29: Prueba integral de la capa de servicios",
)
async def endpoint_test_services(
    session: AsyncSession = Depends(get_session),
):
    return await probar_servicios(session)



if __name__ == "__main__":
    import asyncio

    async def main_cli() -> None:
        await init_db()
        async with async_session_maker() as session:
            await probar_repositorios(session)
            await probar_servicios(session)

    asyncio.run(main_cli())
