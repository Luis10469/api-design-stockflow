import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path al ejecutar directamente como script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from scalar_fastapi import get_scalar_api_reference
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker, get_session, init_db
from app.routers import api_router
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


async def probar_routers() -> dict:
    """T-37: Prueba integral de la Capa 5 (routers HTTP).

    Ejercita los cuatro recursos en ``/api/v1`` con ``httpx.ASGITransport``
    sobre la app real, comprobando los códigos del README (201, 204, 400,
    404, 405, 409) y las reglas de negocio visibles por HTTP: el stock solo
    cambia con movimientos y los borrados con dependencias se rechazan.
    """
    from httpx import ASGITransport, AsyncClient

    base = settings.API_V1_STR
    sufijo = uuid.uuid4().hex[:6].upper()
    pruebas: dict[str, str] = {}

    def verificar(nombre: str, condicion: bool, detalle: str = "") -> None:
        if not condicion:
            raise AssertionError(f"{nombre} -> {detalle or 'sin detalle'}")
        pruebas[nombre] = "OK"
        print(f"[OK] {nombre}{f' -> {detalle}' if detalle else ''}")

    print(f"\n========== T-37 ROUTERS ({sufijo}) ==========")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as cliente:

        async def stock_actual() -> int:
            respuesta = await cliente.get(f"{base}/productos/{id_producto}")
            return respuesta.json()["stock_actual"]

        # PRUEBA 1: SALUD
        r = await cliente.get("/health")
        verificar("GET /health -> 200", r.status_code == 200, str(r.status_code))

        # PRUEBA 2: CATEGORÍAS
        r = await cliente.post(
            f"{base}/categorias/",
            json={"nombre": f"Cat-T37-{sufijo}", "descripcion": "Prueba T-37"},
        )
        verificar("POST /categorias/ -> 201", r.status_code == 201, str(r.status_code))
        id_categoria = r.json()["id_categoria"]

        r = await cliente.post(
            f"{base}/categorias/", json={"nombre": f"Cat-T37-{sufijo}"}
        )
        verificar(
            "POST /categorias/ con nombre repetido -> 409",
            r.status_code == 409,
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/categorias/")
        verificar(
            "GET /categorias/ -> 200",
            r.status_code == 200 and isinstance(r.json(), list),
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/categorias/{id_categoria}")
        verificar(
            "GET /categorias/{id} -> 200", r.status_code == 200, str(r.status_code)
        )

        r = await cliente.get(f"{base}/categorias/999999")
        verificar(
            "GET /categorias/{id} inexistente -> 404",
            r.status_code == 404,
            str(r.status_code),
        )

        r = await cliente.patch(
            f"{base}/categorias/{id_categoria}", json={"descripcion": "Editada T-37"}
        )
        verificar(
            "PATCH /categorias/{id} -> 200", r.status_code == 200, str(r.status_code)
        )

        # PRUEBA 3: PROVEEDORES
        r = await cliente.post(
            f"{base}/proveedores/",
            json={
                "nombre": f"Prov-T37-{sufijo}",
                "telefono": "3001234567",
                "correo": f"t37-{sufijo.lower()}@test.com",
                "direccion": "Calle 10 # 20-30",
                "origen": "Medellín",
            },
        )
        verificar("POST /proveedores/ -> 201", r.status_code == 201, str(r.status_code))
        id_proveedor = r.json()["id_proveedor"]

        r = await cliente.get(f"{base}/proveedores/", params={"origen": "Medellín"})
        verificar(
            "GET /proveedores/?origen -> 200", r.status_code == 200, str(r.status_code)
        )

        r = await cliente.patch(
            f"{base}/proveedores/{id_proveedor}", json={"telefono": "3009876543"}
        )
        verificar(
            "PATCH /proveedores/{id} -> 200", r.status_code == 200, str(r.status_code)
        )

        # PRUEBA 4: PRODUCTOS
        producto_in = {
            "sku": f"T37-{sufijo}",
            "nombre": f"Prod-T37-{sufijo}",
            "precio": 45000.0,
            "costo": 25500.0,
            "stock_minimo": 3,
            "id_categoria": id_categoria,
            "id_proveedor": id_proveedor,
        }
        r = await cliente.post(f"{base}/productos/", json=producto_in)
        verificar(
            "POST /productos/ -> 201 con stock 0",
            r.status_code == 201 and r.json()["stock_actual"] == 0,
            str(r.status_code),
        )
        id_producto = r.json()["id_producto"]

        r = await cliente.post(f"{base}/productos/", json=producto_in)
        verificar(
            "POST /productos/ con SKU repetido -> 409",
            r.status_code == 409,
            str(r.status_code),
        )

        r = await cliente.get(
            f"{base}/productos/", params={"id_categoria": id_categoria}
        )
        verificar(
            "GET /productos/?id_categoria -> 200",
            r.status_code == 200 and len(r.json()) == 1,
            str(r.status_code),
        )

        # PRUEBA 5: MOVIMIENTOS Y STOCK
        r = await cliente.post(
            f"{base}/movimientos-stock/",
            json={
                "id_producto": id_producto,
                "tipo": "ENTRADA",
                "cantidad": 10,
                "motivo": "Entrada T-37",
            },
        )
        verificar(
            "POST /movimientos-stock/ ENTRADA -> 201",
            r.status_code == 201,
            str(r.status_code),
        )
        id_movimiento = r.json()["id_movimiento"]
        verificar(
            "ENTRADA suma al stock (0 + 10 = 10)",
            await stock_actual() == 10,
            str(await stock_actual()),
        )

        r = await cliente.post(
            f"{base}/movimientos-stock/",
            json={
                "id_producto": id_producto,
                "tipo": "SALIDA",
                "cantidad": 4,
                "motivo": "Venta T-37",
            },
        )
        verificar(
            "POST movimientos-stock/ SALIDA -> 201 y resta (10 - 4 = 6)",
            r.status_code == 201 and await stock_actual() == 6,
            str(r.status_code),
        )

        r = await cliente.post(
            f"{base}/movimientos-stock/",
            json={
                "id_producto": id_producto,
                "tipo": "SALIDA",
                "cantidad": 999,
                "motivo": "Salida sin stock",
            },
        )
        verificar(
            "SALIDA mayor al stock -> 409 y stock intacto",
            r.status_code == 409 and await stock_actual() == 6,
            str(r.status_code),
        )

        r = await cliente.post(
            f"{base}/movimientos-stock/",
            json={
                "id_producto": id_producto,
                "tipo": "AJUSTE",
                "cantidad": 7,
                "motivo": "Conteo físico T-37",
            },
        )
        verificar(
            "POST movimientos-stock/ AJUSTE -> 201 y corrige a 7",
            r.status_code == 201 and await stock_actual() == 7,
            str(r.status_code),
        )

        r = await cliente.post(
            f"{base}/movimientos-stock/",
            json={
                "id_producto": 999999,
                "tipo": "ENTRADA",
                "cantidad": 1,
                "motivo": "Producto inexistente",
            },
        )
        verificar(
            "POST movimiento de producto inexistente -> 404",
            r.status_code == 404,
            str(r.status_code),
        )

        r = await cliente.post(
            f"{base}/movimientos-stock/",
            json={
                "id_producto": id_producto,
                "tipo": "TRANSFERENCIA",
                "cantidad": 1,
                "motivo": "Tipo inválido",
            },
        )
        verificar(
            "POST movimiento con tipo inválido -> 400",
            r.status_code == 400,
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/movimientos-stock/", params={"tipo": "SALIDA"})
        verificar(
            "GET /movimientos-stock/?tipo=SALIDA -> 200 y solo salidas",
            r.status_code == 200 and all(m["tipo"] == "SALIDA" for m in r.json()),
            str(r.status_code),
        )

        r = await cliente.get(
            f"{base}/movimientos-stock/",
            params={
                "id_producto": id_producto,
                "desde": "2020-01-01",
                "hasta": "2030-12-31",
            },
        )
        verificar(
            "GET /movimientos-stock/ con rango de fechas -> 200",
            r.status_code == 200 and len(r.json()) == 3,
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/movimientos-stock/{id_movimiento}")
        verificar(
            "GET /movimientos-stock/{id} -> 200",
            r.status_code == 200,
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/movimientos-stock/999999")
        verificar(
            "GET /movimientos-stock/{id} inexistente -> 404",
            r.status_code == 404,
            str(r.status_code),
        )

        r = await cliente.patch(
            f"{base}/movimientos-stock/{id_movimiento}", json={"motivo": "editado"}
        )
        verificar(
            "PATCH movimiento -> 405 (inmutable)",
            r.status_code == 405,
            str(r.status_code),
        )

        r = await cliente.delete(f"{base}/movimientos-stock/{id_movimiento}")
        verificar(
            "DELETE movimiento -> 405 (inmutable)",
            r.status_code == 405,
            str(r.status_code),
        )

        # PRUEBA 6: ENDPOINTS ANIDADOS
        r = await cliente.get(f"{base}/categorias/{id_categoria}/productos")
        verificar(
            "GET /categorias/{id}/productos -> 200 con el producto",
            r.status_code == 200
            and [p["id_producto"] for p in r.json()] == [id_producto],
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/proveedores/{id_proveedor}/productos")
        verificar(
            "GET /proveedores/{id}/productos -> 200 con el producto",
            r.status_code == 200 and len(r.json()) == 1,
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/categorias/999999/productos")
        verificar(
            "GET categoría inexistente /productos -> 404",
            r.status_code == 404,
            str(r.status_code),
        )

        # PRUEBA 7: PATCH NO TOCA EL STOCK
        r = await cliente.patch(
            f"{base}/productos/{id_producto}", json={"stock_minimo": 10}
        )
        verificar(
            "PATCH /productos/{id} -> 200 y no cambia el stock",
            r.status_code == 200 and r.json()["stock_actual"] == 7,
            str(r.status_code),
        )

        r = await cliente.get(
            f"{base}/productos/",
            params={"bajo_stock": "true", "id_categoria": id_categoria},
        )
        verificar(
            "GET /productos/?bajo_stock=true incluye el producto (7 <= 10)",
            r.status_code == 200 and len(r.json()) == 1,
            str(r.status_code),
        )

        # stock_actual no es un campo de ProductoUpdate: se ignora, no se escribe
        r = await cliente.patch(
            f"{base}/productos/{id_producto}", json={"stock_actual": 999}
        )
        verificar(
            "PATCH con stock_actual no modifica el stock",
            r.status_code == 200 and await stock_actual() == 7,
            str(r.status_code),
        )

        # PRUEBA 8: BORRADOS PROTEGIDOS
        r = await cliente.delete(f"{base}/categorias/{id_categoria}")
        verificar(
            "DELETE categoría con productos -> 409",
            r.status_code == 409,
            str(r.status_code),
        )

        r = await cliente.delete(f"{base}/proveedores/{id_proveedor}")
        verificar(
            "DELETE proveedor con productos -> 409",
            r.status_code == 409,
            str(r.status_code),
        )

        r = await cliente.delete(f"{base}/productos/{id_producto}")
        verificar(
            "DELETE producto con movimientos -> 409",
            r.status_code == 409,
            str(r.status_code),
        )

        # PRUEBA 9: BORRADO REAL DE UN PRODUCTO SIN MOVIMIENTOS
        r = await cliente.post(
            f"{base}/productos/",
            json={
                "sku": f"T37-B-{sufijo}",
                "nombre": f"Prod-B-T37-{sufijo}",
                "precio": 1000.0,
                "costo": 500.0,
                "stock_minimo": 0,
                "id_categoria": id_categoria,
                "id_proveedor": id_proveedor,
            },
        )
        id_producto_b = r.json()["id_producto"]

        r = await cliente.delete(f"{base}/productos/{id_producto_b}")
        verificar(
            "DELETE producto sin movimientos -> 204",
            r.status_code == 204 and r.content == b"",
            str(r.status_code),
        )

        r = await cliente.get(f"{base}/productos/{id_producto_b}")
        verificar(
            "GET producto borrado -> 404", r.status_code == 404, str(r.status_code)
        )

    print("\n======================================")
    print(f" T-37 FINALIZADA EXITOSAMENTE ({len(pruebas)} pruebas)")
    print("======================================\n")

    return {
        "status": "success",
        "mensaje": "T-37 completada exitosamente",
        "sufijo": sufijo,
        "pruebas": pruebas,
        "datos": {
            "id_categoria": id_categoria,
            "id_proveedor": id_proveedor,
            "id_producto": id_producto,
            "id_movimiento": id_movimiento,
            "stock_final": 7,
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
    docs_url="/swagger",  # Swagger UI pasa a /swagger: /docs muestra Scalar (más abajo)
)

# CORS: el frontend se sirve aparte, desde otro origen; el navegador solo le deja leer las respuestas
# si ese origen está en CORS_ORIGINS. Métodos y encabezado son los que usan las rutas de /api/v1.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

# T-36: Incluir el router central con el prefijo /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(
    "/health",
    tags=["Salud"],
    summary="Verificar el estado del servicio",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# La API va sola (el panel web es un frontend aparte): la raíz lleva a la documentación.
@app.get("/", include_in_schema=False)
async def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")


# Documentación interactiva con Scalar: lee el mismo /openapi.json que Swagger (/swagger) y ReDoc (/redoc).
# El visor se fija en una versión para que no cambie solo; la telemetría de Scalar va apagada.
@app.get("/docs", include_in_schema=False)
async def documentacion_scalar():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{settings.PROJECT_NAME} · Documentación",
        scalar_js_url="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.77.0",
        telemetry=False,
    )


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


@app.post(
    "/test-routers",
    tags=["Pruebas"],
    summary="T-37: Prueba integral de la Capa 5 (routers HTTP)",
)
async def endpoint_test_routers():
    """Recorre los cuatro recursos en /api/v1 y valida códigos y reglas de negocio."""
    return await probar_routers()


if __name__ == "__main__":
    import asyncio

    async def main_cli() -> None:
        await init_db()
        async with async_session_maker() as session:
            await probar_repositorios(session)
            await probar_servicios(session)
            await probar_routers()

    asyncio.run(main_cli())
