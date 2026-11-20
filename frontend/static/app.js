// Panel web de StockFlow: usa la API REST (/api/v1) del mismo servidor.
// Sin dependencias ni compilación: FastAPI sirve estos archivos tal cual.

const API = '/api/v1';
const LOTE = 100; // las listas de la API aceptan hasta 100 por página
const TIPOS = ['ENTRADA', 'SALIDA', 'AJUSTE'];

const estado = {
  cargado: false,
  categorias: [],
  proveedores: [],
  productos: [],
  movimientos: [],
  filtrosProductos: { texto: '', id_categoria: '', id_proveedor: '', bajo_stock: false },
  filtrosMovimientos: { id_producto: '', tipo: '', desde: '', hasta: '' },
};

const $ = (selector, raiz = document) => raiz.querySelector(selector);
const contenido = $('#contenido');
const dialogo = $('#dialogo');

// Cada pintura o consulta toma un turno; una respuesta vieja no pisa una pantalla nueva.
let turno = 0;

/* ---------- Formato ---------- */

const esc = (valor) =>
  String(valor ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

const formatoPesos = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0, maximumFractionDigits: 2 });
const formatoEntero = new Intl.NumberFormat('es-CO');
const formatoFecha = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' });

const pesos = (n) => formatoPesos.format(n ?? 0);
const entero = (n) => formatoEntero.format(n ?? 0);
const plural = (n, uno, varios) => `${entero(n)} ${n === 1 ? uno : varios}`;

// La API guarda las fechas en UTC; si llegan sin zona (SQLite), se leen como UTC.
function verFecha(texto) {
  if (!texto) return '—';
  const conZona = /([zZ]|[+-]\d{2}:?\d{2})$/.test(texto) ? texto : `${texto}Z`;
  const fecha = new Date(conZona);
  return Number.isNaN(fecha.getTime()) ? texto : formatoFecha.format(fecha);
}

// Un día elegido en el calendario va de 00:00 a 23:59 de la hora local; la API recibe UTC.
const inicioDelDia = (dia) => (dia ? new Date(`${dia}T00:00:00`).toISOString() : '');
const finDelDia = (dia) => (dia ? new Date(`${dia}T23:59:59.999`).toISOString() : '');

// Misma regla que la API (README): stock bajo cuando stock_actual <= stock_minimo.
const esBajoStock = (p) => p.stock_actual <= p.stock_minimo;

/* ---------- Íconos ---------- */

const TRAZOS = {
  mas: '<path d="M12 5v14M5 12h14"/>',
  editar: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  borrar: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m19 6-1 14H6L5 6"/>',
  historial: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  mover: '<path d="M7 20V4m0 0L3 8m4-4 4 4M17 4v16m0 0-4-4m4 4 4-4"/>',
  lista: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  alerta: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  listo: '<path d="M20 6 9 17l-5-5"/>',
  cerrar: '<path d="M18 6 6 18M6 6l12 12"/>',
  recargar: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
};

const icono = (nombre) => `<svg class="icono" viewBox="0 0 24 24" aria-hidden="true">${TRAZOS[nombre]}</svg>`;

/* ---------- Conexión con la API ---------- */

class ErrorApi extends Error {
  constructor(mensaje, status) {
    super(mensaje);
    this.status = status;
  }
}

function mensajeDeError(datos, status) {
  const detalle = datos?.detail;
  if (typeof detalle === 'string') return detalle;
  if (Array.isArray(detalle)) {
    return detalle
      .map((e) => `${(e.loc ?? []).filter((parte) => parte !== 'body').join('.') || 'Dato'}: ${e.msg}`)
      .join(' · ');
  }
  return `La API respondió con el código ${status}.`;
}

async function api(ruta, { metodo = 'GET', cuerpo, params } = {}) {
  const url = new URL(API + ruta, window.location.origin);
  for (const [clave, valor] of Object.entries(params ?? {})) {
    if (valor !== '' && valor !== null && valor !== undefined && valor !== false) url.searchParams.set(clave, valor);
  }
  let respuesta;
  try {
    respuesta = await fetch(url, {
      method: metodo,
      headers: cuerpo === undefined ? {} : { 'Content-Type': 'application/json' },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  } catch {
    throw new ErrorApi('No hay conexión con la API. Revisa que el servidor esté encendido.', 0);
  }
  if (respuesta.status === 204) return null;
  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) throw new ErrorApi(mensajeDeError(datos, respuesta.status), respuesta.status);
  return datos;
}

// Las listas van por páginas: se piden en orden hasta que llega una incompleta.
async function traerTodo(ruta, params = {}) {
  const todos = [];
  for (let skip = 0; ; skip += LOTE) {
    const pagina = await api(ruta, { params: { ...params, skip, limit: LOTE } });
    todos.push(...pagina);
    if (pagina.length < LOTE || skip >= 50000) return todos;
  }
}

async function cargarDatos() {
  const [categorias, proveedores, productos, movimientos] = await Promise.all([
    traerTodo('/categorias/'),
    traerTodo('/proveedores/'),
    traerTodo('/productos/'),
    traerTodo('/movimientos-stock/'),
  ]);
  Object.assign(estado, { categorias, proveedores, productos, movimientos, cargado: true });
}

const buscar = (lista, campo, id) => lista.find((x) => x[campo] === Number(id));
const categoriaPorId = (id) => buscar(estado.categorias, 'id_categoria', id);
const proveedorPorId = (id) => buscar(estado.proveedores, 'id_proveedor', id);
const productoPorId = (id) => buscar(estado.productos, 'id_producto', id);
const nombreCategoria = (id) => categoriaPorId(id)?.nombre ?? `Categoría ${id}`;
const nombreProveedor = (id) => proveedorPorId(id)?.nombre ?? `Proveedor ${id}`;
const nombreProducto = (id) => productoPorId(id)?.nombre ?? `Producto ${id}`;

// Los id crecen con el tiempo: el más alto es el movimiento más reciente.
const recientesPrimero = (movimientos) => [...movimientos].sort((a, b) => b.id_movimiento - a.id_movimiento);

function contarPor(campo) {
  const cuenta = {};
  for (const p of estado.productos) cuenta[p[campo]] = (cuenta[p[campo]] ?? 0) + 1;
  return cuenta;
}

/* ---------- Piezas de interfaz ---------- */

const vacio = (texto) => `<p class="vacio">${esc(texto)}</p>`;
const errorHtml = (texto) => `<p class="formulario__error" role="alert">${esc(texto)}</p>`;

const boton = (accion, texto, nombreIcono = '', clase = '', id = '') =>
  `<button type="button" class="boton ${clase}" data-accion="${accion}"${id !== '' ? ` data-id="${esc(id)}"` : ''}>${nombreIcono ? icono(nombreIcono) : ''}${esc(texto)}</button>`;

const botonIcono = (accion, nombreIcono, etiqueta, id, clase = '') =>
  `<button type="button" class="boton boton--icono ${clase}" data-accion="${accion}" data-id="${esc(id)}" title="${esc(etiqueta)}" aria-label="${esc(etiqueta)}">${icono(nombreIcono)}</button>`;

const encabezado = (titulo, texto, ruta, botones = '') => `
  <section class="encabezado">
    <div><h1>${esc(titulo)}</h1><p>${esc(texto)}</p>${ruta ? `<code class="ruta">${esc(ruta)}</code>` : ''}</div>
    ${botones ? `<div class="encabezado__acciones">${botones}</div>` : ''}
  </section>`;

const etiquetaTipo = (tipo) =>
  `<span class="insignia insignia--${TIPOS.includes(tipo) ? tipo.toLowerCase() : 'otro'}">${esc(tipo)}</span>`;

const cantidadMovimiento = (m) =>
  ({ ENTRADA: `+${entero(m.cantidad)}`, SALIDA: `−${entero(m.cantidad)}`, AJUSTE: `= ${entero(m.cantidad)}` })[m.tipo] ?? entero(m.cantidad);

const insigniaStock = (p) =>
  esBajoStock(p)
    ? `<span class="stock stock--bajo" title="En o por debajo del mínimo (${entero(p.stock_minimo)})">${icono('alerta')}${entero(p.stock_actual)} <small>bajo</small></span>`
    : `<span class="stock">${entero(p.stock_actual)}</span>`;

const opcionesHtml = (pares, elegido) =>
  pares.map(([valor, texto]) => `<option value="${esc(valor)}"${String(valor) === String(elegido ?? '') ? ' selected' : ''}>${esc(texto)}</option>`).join('');

const paresDe = (lista, campoId) => lista.map((x) => [x[campoId], x.nombre]);
const paresProductos = () => estado.productos.map((p) => [p.id_producto, `${p.nombre} (${p.sku})`]);

/* ---------- Avisos ---------- */

function aviso(texto, tipo = 'ok') {
  const elemento = document.createElement('div');
  elemento.className = `aviso aviso--${tipo}`;
  elemento.setAttribute('role', tipo === 'error' ? 'alert' : 'status');
  elemento.innerHTML = `${icono(tipo === 'error' ? 'alerta' : 'listo')}<span></span>`;
  elemento.querySelector('span').textContent = texto;
  $('#avisos').append(elemento);
  const duracion = tipo === 'error' ? 7000 : 3500;
  setTimeout(() => elemento.classList.add('aviso--saliendo'), duracion);
  setTimeout(() => elemento.remove(), duracion + 400);
}

/* ---------- Ventanas ---------- */

function abrirDialogo(html, { angosto = false } = {}) {
  dialogo.className = angosto ? 'dialogo dialogo--angosto' : 'dialogo';
  dialogo.innerHTML = html;
  if (!dialogo.open) dialogo.showModal();
}

dialogo.addEventListener('click', (evento) => {
  const fuera = evento.target === dialogo && !dialogo.querySelector('form'); // un formulario no se cierra por un clic suelto
  if (fuera || evento.target.closest('[data-cerrar]')) dialogo.close();
});

const cabeceraDialogo = (titulo, subtitulo) => `
  <header class="dialogo__cabecera">
    <div><h2>${esc(titulo)}</h2>${subtitulo ? `<p>${esc(subtitulo)}</p>` : ''}</div>
    <button type="button" class="boton boton--icono boton--fantasma" data-cerrar aria-label="Cerrar">${icono('cerrar')}</button>
  </header>`;

function confirmar(titulo, mensaje, textoBoton = 'Borrar') {
  return new Promise((resolver) => {
    abrirDialogo(`
      <div class="dialogo__caja">
        <h2>${esc(titulo)}</h2>
        <p class="dialogo__texto">${esc(mensaje)}</p>
        <footer class="dialogo__acciones">
          <button type="button" class="boton" data-cerrar>Cancelar</button>
          <button type="button" class="boton boton--peligro" data-confirmar>${esc(textoBoton)}</button>
        </footer>
      </div>`, { angosto: true });
    let respuesta = false;
    $('[data-confirmar]', dialogo).addEventListener('click', () => { respuesta = true; dialogo.close(); });
    dialogo.addEventListener('close', () => resolver(respuesta), { once: true });
    $('[data-cerrar]', dialogo).focus();
  });
}

async function dialogoLista(titulo, subtitulo, cargar, filaHtml, textoVacio) {
  abrirDialogo(`<div class="dialogo__caja">${cabeceraDialogo(titulo, subtitulo)}<div class="dialogo__cuerpo"><p class="cargando">Cargando…</p></div></div>`);
  const cuerpo = $('.dialogo__cuerpo', dialogo);
  try {
    const filas = await cargar();
    cuerpo.innerHTML = filas.length ? `<ul class="lista">${filas.map(filaHtml).join('')}</ul>` : vacio(textoVacio);
  } catch (error) {
    cuerpo.innerHTML = errorHtml(error.message);
  }
}

/* ---------- Formularios ---------- */

function campoHtml(c) {
  const id = `campo-${c.nombre}`;
  const extra = Object.entries(c.attrs ?? {}).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');
  const base = `id="${id}" name="${c.nombre}"${c.requerido ? ' required' : ''}${extra}`;
  let control;
  if (c.tipo === 'select') {
    control = `<select ${base}>${c.vacio ? `<option value="">${esc(c.vacio)}</option>` : ''}${opcionesHtml(c.opciones, c.valor)}</select>`;
  } else if (c.tipo === 'textarea') {
    control = `<textarea ${base} rows="3">${esc(c.valor ?? '')}</textarea>`;
  } else {
    control = `<input ${base} type="${c.tipo ?? 'text'}" value="${esc(c.valor ?? '')}">`;
  }
  return `
    <label class="campo${c.ancho === 'medio' ? ' campo--medio' : ''}" for="${id}">
      <span class="campo__etiqueta">${esc(c.etiqueta)}${c.requerido ? '' : ' <small>(opcional)</small>'}</span>
      ${control}
      ${c.ayuda ? `<small class="campo__ayuda">${esc(c.ayuda)}</small>` : ''}
    </label>`;
}

function leerFormulario(form, campos) {
  const datos = {};
  for (const c of campos) {
    const crudo = form.elements[c.nombre].value.trim();
    if (crudo === '') datos[c.nombre] = null;
    else if (c.conv === 'entero') datos[c.nombre] = Number.parseInt(crudo, 10);
    else if (c.conv === 'decimal') datos[c.nombre] = Number(crudo);
    else datos[c.nombre] = crudo;
  }
  return datos;
}

// PATCH solo con lo que cambió: así no se reenvían SKU o nombres que la API revisa por duplicados.
const soloCambios = (datos, original) =>
  Object.fromEntries(Object.entries(datos).filter(([clave, valor]) => (original[clave] ?? null) !== valor));

function formulario({ titulo, subtitulo = '', campos, textoBoton = 'Guardar', alEnviar, extra = '', alCambiar }) {
  abrirDialogo(`
    <form class="dialogo__caja">
      ${cabeceraDialogo(titulo, subtitulo)}
      <div class="formulario">${campos.map(campoHtml).join('')}</div>
      ${extra}
      <p class="formulario__error" role="alert" hidden></p>
      <footer class="dialogo__acciones">
        <button type="button" class="boton" data-cerrar>Cancelar</button>
        <button type="submit" class="boton boton--primario">${esc(textoBoton)}</button>
      </footer>
    </form>`);
  const form = $('form', dialogo);
  const error = $('.formulario__error', form);
  const enviar = $('[type="submit"]', form);
  if (alCambiar) {
    form.addEventListener('input', () => alCambiar(form));
    alCambiar(form);
  }
  form.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    enviar.disabled = true;
    enviar.textContent = 'Guardando…';
    error.hidden = true;
    try {
      const mensaje = await alEnviar(leerFormulario(form, campos));
      dialogo.close();
      if (mensaje) aviso(mensaje);
      await refrescar();
    } catch (fallo) {
      error.textContent = fallo.message;
      error.hidden = false;
      enviar.disabled = false;
      enviar.textContent = textoBoton;
    }
  });
  $('.formulario input, .formulario select, .formulario textarea', form)?.focus();
}

function formularioCategoria(categoria) {
  const campos = [
    { nombre: 'nombre', etiqueta: 'Nombre', requerido: true, valor: categoria?.nombre, attrs: { maxlength: 100, placeholder: 'Camisas' } },
    { nombre: 'descripcion', etiqueta: 'Descripción', tipo: 'textarea', valor: categoria?.descripcion, attrs: { maxlength: 255 } },
  ];
  formulario({
    titulo: categoria ? 'Editar categoría' : 'Nueva categoría',
    subtitulo: categoria ? '' : 'El nombre no se puede repetir.',
    campos,
    alEnviar: async (datos) => {
      if (!categoria) {
        await api('/categorias/', { metodo: 'POST', cuerpo: datos });
        return 'Categoría creada';
      }
      const cambios = soloCambios(datos, categoria);
      if (!Object.keys(cambios).length) return 'Sin cambios';
      await api(`/categorias/${categoria.id_categoria}`, { metodo: 'PATCH', cuerpo: cambios });
      return 'Categoría actualizada';
    },
  });
}

function formularioProveedor(proveedor) {
  const v = proveedor ?? {};
  const campos = [
    { nombre: 'nombre', etiqueta: 'Nombre o razón social', requerido: true, valor: v.nombre, attrs: { maxlength: 150 } },
    { nombre: 'telefono', etiqueta: 'Teléfono', requerido: true, tipo: 'tel', valor: v.telefono, ancho: 'medio', attrs: { maxlength: 20, autocomplete: 'off' } },
    { nombre: 'correo', etiqueta: 'Correo', requerido: true, tipo: 'email', valor: v.correo, ancho: 'medio', attrs: { autocomplete: 'off' } },
    { nombre: 'direccion', etiqueta: 'Dirección', requerido: true, valor: v.direccion, attrs: { maxlength: 255 } },
    { nombre: 'origen', etiqueta: 'Origen', requerido: true, valor: v.origen, attrs: { maxlength: 100, placeholder: 'Ciudad o país' } },
  ];
  formulario({
    titulo: proveedor ? 'Editar proveedor' : 'Nuevo proveedor',
    campos,
    alEnviar: async (datos) => {
      if (!proveedor) {
        await api('/proveedores/', { metodo: 'POST', cuerpo: datos });
        return 'Proveedor creado';
      }
      const cambios = soloCambios(datos, proveedor);
      if (!Object.keys(cambios).length) return 'Sin cambios';
      await api(`/proveedores/${proveedor.id_proveedor}`, { metodo: 'PATCH', cuerpo: cambios });
      return 'Proveedor actualizado';
    },
  });
}

function formularioProducto(producto) {
  if (!estado.categorias.length || !estado.proveedores.length) {
    aviso('Primero crea al menos una categoría y un proveedor.', 'error');
    return;
  }
  const v = producto ?? { stock_minimo: 0 };
  const campos = [
    { nombre: 'nombre', etiqueta: 'Nombre', requerido: true, valor: v.nombre, attrs: { maxlength: 150 } },
    { nombre: 'sku', etiqueta: 'SKU', requerido: true, valor: v.sku, ancho: 'medio', ayuda: 'Código único del producto.', attrs: { maxlength: 50, placeholder: 'CAM-001' } },
    { nombre: 'stock_minimo', etiqueta: 'Stock mínimo', requerido: true, conv: 'entero', tipo: 'number', valor: v.stock_minimo, ancho: 'medio', ayuda: 'Con este número o menos sale como bajo stock.', attrs: { min: 0, step: 1 } },
    { nombre: 'precio', etiqueta: 'Precio de venta', requerido: true, conv: 'decimal', tipo: 'number', valor: v.precio, ancho: 'medio', attrs: { min: 0.01, step: 'any' } },
    { nombre: 'costo', etiqueta: 'Costo', requerido: true, conv: 'decimal', tipo: 'number', valor: v.costo, ancho: 'medio', attrs: { min: 0, step: 'any' } },
    { nombre: 'id_categoria', etiqueta: 'Categoría', requerido: true, conv: 'entero', tipo: 'select', vacio: 'Elige una categoría', opciones: paresDe(estado.categorias, 'id_categoria'), valor: v.id_categoria, ancho: 'medio' },
    { nombre: 'id_proveedor', etiqueta: 'Proveedor', requerido: true, conv: 'entero', tipo: 'select', vacio: 'Elige un proveedor', opciones: paresDe(estado.proveedores, 'id_proveedor'), valor: v.id_proveedor, ancho: 'medio' },
  ];
  if (!producto) {
    campos.push({ nombre: 'stock_inicial', etiqueta: 'Stock inicial', conv: 'entero', tipo: 'number', ayuda: 'Si pones una cantidad, se registra como movimiento de ENTRADA.', attrs: { min: 0, step: 1 } });
  }
  formulario({
    titulo: producto ? 'Editar producto' : 'Nuevo producto',
    subtitulo: producto ? `${producto.sku} · stock actual ${entero(producto.stock_actual)} (cambia solo con movimientos)` : 'El producto empieza con stock 0.',
    campos,
    alEnviar: async (datos) => {
      if (producto) {
        const cambios = soloCambios(datos, producto);
        if (!Object.keys(cambios).length) return 'Sin cambios';
        await api(`/productos/${producto.id_producto}`, { metodo: 'PATCH', cuerpo: cambios });
        return 'Producto actualizado';
      }
      const { stock_inicial: inicial, ...nuevo } = datos;
      const creado = await api('/productos/', { metodo: 'POST', cuerpo: nuevo });
      if (inicial > 0) {
        try {
          await api(`/productos/${creado.id_producto}/movimientos-stock`, {
            metodo: 'POST',
            cuerpo: { tipo: 'ENTRADA', cantidad: inicial, motivo: 'Stock inicial' },
          });
        } catch (fallo) {
          aviso(`El producto se creó, pero el stock inicial no se registró: ${fallo.message}`, 'error');
          return null;
        }
      }
      return 'Producto creado';
    },
  });
}

function formularioMovimiento({ producto = null, tipo = 'ENTRADA' } = {}) {
  if (!estado.productos.length) {
    aviso('Primero crea un producto.', 'error');
    return;
  }
  const campos = [];
  if (!producto) {
    campos.push({ nombre: 'id_producto', etiqueta: 'Producto', requerido: true, conv: 'entero', tipo: 'select', vacio: 'Elige un producto', opciones: paresProductos() });
  }
  campos.push(
    { nombre: 'tipo', etiqueta: 'Tipo', requerido: true, tipo: 'select', valor: tipo, ancho: 'medio', opciones: [['ENTRADA', 'ENTRADA (suma)'], ['SALIDA', 'SALIDA (resta)'], ['AJUSTE', 'AJUSTE (conteo físico)']] },
    { nombre: 'cantidad', etiqueta: 'Cantidad', requerido: true, conv: 'entero', tipo: 'number', ancho: 'medio', attrs: { min: 1, step: 1 } },
    { nombre: 'motivo', etiqueta: 'Motivo', requerido: true, attrs: { maxlength: 255, placeholder: 'Compra al proveedor, venta, conteo físico…' } },
  );
  formulario({
    titulo: 'Registrar movimiento',
    subtitulo: producto ? `${producto.nombre} · ${producto.sku}` : 'ENTRADA suma, SALIDA resta y AJUSTE deja el stock en la cantidad indicada.',
    campos,
    textoBoton: 'Registrar',
    extra: '<p class="vista-previa" aria-live="polite"></p>',
    alCambiar: (form) => {
      const previa = $('.vista-previa', form);
      const elegido = producto ?? productoPorId(form.elements.id_producto?.value);
      if (!elegido) {
        previa.textContent = '';
        return;
      }
      const actual = elegido.stock_actual;
      const cantidad = Number.parseInt(form.elements.cantidad.value, 10);
      const tipoElegido = form.elements.tipo.value;
      previa.dataset.alerta = '';
      if (!(cantidad > 0)) {
        previa.textContent = `Stock actual: ${entero(actual)} (mínimo ${entero(elegido.stock_minimo)}).`;
        return;
      }
      const final = tipoElegido === 'ENTRADA' ? actual + cantidad : tipoElegido === 'SALIDA' ? actual - cantidad : cantidad;
      if (final < 0) {
        previa.dataset.alerta = 'si';
        previa.textContent = `No alcanza: hay ${entero(actual)} y quieres sacar ${entero(cantidad)}. La API lo va a rechazar (409).`;
        return;
      }
      if (final <= elegido.stock_minimo) previa.dataset.alerta = 'si';
      previa.textContent = `Stock: ${entero(actual)} → ${entero(final)}${final <= elegido.stock_minimo ? ` (queda en bajo stock, mínimo ${entero(elegido.stock_minimo)})` : ''}.`;
    },
    alEnviar: async (datos) => {
      if (producto) {
        await api(`/productos/${producto.id_producto}/movimientos-stock`, { metodo: 'POST', cuerpo: datos });
      } else {
        await api('/movimientos-stock/', { metodo: 'POST', cuerpo: datos });
      }
      return `Movimiento de ${datos.tipo} registrado`;
    },
  });
}

async function borrar(ruta, titulo, mensaje, exito) {
  if (!(await confirmar(titulo, mensaje))) return;
  try {
    await api(ruta, { metodo: 'DELETE' });
    aviso(exito);
    await refrescar();
  } catch (fallo) {
    aviso(fallo.message, 'error');
  }
}

/* ---------- Vistas ---------- */

const filaProductoCorta = (p) => `
  <li class="lista__fila">
    <div><strong>${esc(p.nombre)}</strong><small>${esc(p.sku)} · ${pesos(p.precio)}</small></div>
    <div class="lista__fin">${insigniaStock(p)}</div>
  </li>`;

const filaMovimientoCorta = (m, conProducto = true) => `
  <li class="lista__fila">
    <div><strong>${esc(conProducto ? nombreProducto(m.id_producto) : m.motivo)}</strong><small>${conProducto ? `${esc(m.motivo)} · ` : ''}${esc(verFecha(m.fecha))}</small></div>
    <div class="lista__fin">${etiquetaTipo(m.tipo)}<span class="cantidad">${cantidadMovimiento(m)}</span></div>
  </li>`;

const cifra = (titulo, valor, nota, alerta = false) => `
  <article class="cifra${alerta ? ' cifra--alerta' : ''}">
    <h3>${esc(titulo)}</h3>
    <p class="cifra__valor">${esc(valor)}</p>
    <p class="cifra__nota">${alerta ? icono('alerta') : ''}${esc(nota)}</p>
  </article>`;

function vistaResumen() {
  const productos = estado.productos;
  const unidades = productos.reduce((suma, p) => suma + p.stock_actual, 0);
  const valor = productos.reduce((suma, p) => suma + p.stock_actual * p.costo, 0);
  const bajos = productos.filter(esBajoStock);
  const ultimos = recientesPrimero(estado.movimientos).slice(0, 8);
  contenido.innerHTML = `
    ${encabezado('Resumen del inventario', 'Datos en vivo de la API de StockFlow.', 'GET /api/v1/productos/ · /categorias/ · /proveedores/ · /movimientos-stock/',
      boton('recargar', 'Actualizar', 'recargar') + boton('nuevo-movimiento', 'Registrar movimiento', 'mover', 'boton--primario'))}
    <section class="cifras" aria-label="Cifras generales">
      ${cifra('Productos', entero(productos.length), `${plural(estado.categorias.length, 'categoría', 'categorías')} · ${plural(estado.proveedores.length, 'proveedor', 'proveedores')}`)}
      ${cifra('Unidades en stock', entero(unidades), 'Suma del stock actual')}
      ${cifra('Valor del inventario', pesos(valor), 'Stock actual × costo')}
      ${cifra('Bajo stock', entero(bajos.length), bajos.length ? 'Necesitan reposición' : 'Todo sobre el mínimo', bajos.length > 0)}
    </section>
    <div class="columnas">
      <section class="panel">
        <header class="panel__cabecera"><h2>Productos con bajo stock</h2><a href="#productos" data-accion="ver-bajos">Ver todos</a></header>
        ${bajos.length
          ? `<ul class="lista">${bajos.slice(0, 8).map((p) => `
              <li class="lista__fila">
                <div><strong>${esc(p.nombre)}</strong><small>${esc(p.sku)} · mínimo ${entero(p.stock_minimo)}</small></div>
                <div class="lista__fin">${insigniaStock(p)}${boton('reponer', 'Reponer', '', 'boton--chico', p.id_producto)}</div>
              </li>`).join('')}</ul>`
          : vacio('Ningún producto está en su stock mínimo o por debajo.')}
      </section>
      <section class="panel">
        <header class="panel__cabecera"><h2>Últimos movimientos</h2><a href="#movimientos">Ver todos</a></header>
        ${ultimos.length ? `<ul class="lista">${ultimos.map((m) => filaMovimientoCorta(m)).join('')}</ul>` : vacio('Todavía no hay movimientos.')}
      </section>
    </div>`;
}

let listaProductos = [];

function vistaProductos() {
  const f = estado.filtrosProductos;
  contenido.innerHTML = `
    ${encabezado('Productos', 'El stock solo cambia con movimientos: la API no deja editarlo directo.', '/api/v1/productos/ · GET, POST, PATCH, DELETE y /{id}/movimientos-stock',
      boton('nuevo-producto', 'Nuevo producto', 'mas', 'boton--primario'))}
    <form class="filtros" id="filtros-productos" role="search">
      <label class="campo"><span class="campo__etiqueta">Buscar</span><input type="search" name="texto" value="${esc(f.texto)}" placeholder="Nombre o SKU"></label>
      <label class="campo"><span class="campo__etiqueta">Categoría</span><select name="id_categoria"><option value="">Todas</option>${opcionesHtml(paresDe(estado.categorias, 'id_categoria'), f.id_categoria)}</select></label>
      <label class="campo"><span class="campo__etiqueta">Proveedor</span><select name="id_proveedor"><option value="">Todos</option>${opcionesHtml(paresDe(estado.proveedores, 'id_proveedor'), f.id_proveedor)}</select></label>
      <label class="interruptor"><input type="checkbox" name="bajo_stock"${f.bajo_stock ? ' checked' : ''}><span>Solo bajo stock</span></label>
    </form>
    <div id="resultado"><p class="cargando">Cargando…</p></div>`;
  const form = $('#filtros-productos');
  form.addEventListener('submit', (evento) => evento.preventDefault());
  form.addEventListener('input', (evento) => {
    if (evento.target.name !== 'texto') return;
    f.texto = evento.target.value;
    pintarTablaProductos();
  });
  form.addEventListener('change', (evento) => {
    if (evento.target.name === 'texto') return;
    f.id_categoria = form.elements.id_categoria.value;
    f.id_proveedor = form.elements.id_proveedor.value;
    f.bajo_stock = form.elements.bajo_stock.checked;
    tablaProductos();
  });
  return tablaProductos();
}

// Categoría, proveedor y bajo stock los filtra la API; el texto se busca aquí mismo.
async function tablaProductos() {
  const mio = ++turno;
  const f = estado.filtrosProductos;
  const conFiltro = f.id_categoria || f.id_proveedor || f.bajo_stock;
  let lista;
  try {
    lista = conFiltro
      ? await traerTodo('/productos/', { id_categoria: f.id_categoria, id_proveedor: f.id_proveedor, bajo_stock: f.bajo_stock })
      : estado.productos;
  } catch (fallo) {
    if (mio === turno) $('#resultado').innerHTML = errorHtml(fallo.message);
    return;
  }
  if (mio !== turno) return;
  listaProductos = lista;
  pintarTablaProductos();
}

function pintarTablaProductos() {
  const resultado = $('#resultado');
  if (!resultado) return;
  const texto = estado.filtrosProductos.texto.trim().toLowerCase();
  const lista = texto ? listaProductos.filter((p) => `${p.nombre} ${p.sku}`.toLowerCase().includes(texto)) : listaProductos;
  if (!lista.length) {
    resultado.innerHTML = vacio(estado.productos.length ? 'Ningún producto coincide con los filtros.' : 'Todavía no hay productos. Crea primero una categoría y un proveedor.');
    return;
  }
  resultado.innerHTML = `
    <p class="conteo">${entero(lista.length)} de ${plural(estado.productos.length, 'producto', 'productos')}</p>
    <div class="tabla-envoltura">
      <table class="tabla">
        <thead><tr>
          <th>SKU</th><th>Producto</th><th>Categoría</th><th>Proveedor</th>
          <th class="num">Precio</th><th class="num">Costo</th><th class="num">Stock</th><th class="num">Mínimo</th>
          <th><span class="oculto">Acciones</span></th>
        </tr></thead>
        <tbody>${lista.map((p) => `
          <tr>
            <td data-etiqueta="SKU"><code>${esc(p.sku)}</code></td>
            <td data-etiqueta="Producto" class="celda-titulo">${esc(p.nombre)}</td>
            <td data-etiqueta="Categoría">${esc(nombreCategoria(p.id_categoria))}</td>
            <td data-etiqueta="Proveedor">${esc(nombreProveedor(p.id_proveedor))}</td>
            <td data-etiqueta="Precio" class="num">${pesos(p.precio)}</td>
            <td data-etiqueta="Costo" class="num">${pesos(p.costo)}</td>
            <td data-etiqueta="Stock" class="num">${insigniaStock(p)}</td>
            <td data-etiqueta="Mínimo" class="num">${entero(p.stock_minimo)}</td>
            <td class="celda-acciones"><div class="acciones">
              ${boton('movimiento-producto', 'Movimiento', 'mover', 'boton--chico', p.id_producto)}
              ${botonIcono('historial-producto', 'historial', `Historial de ${p.nombre}`, p.id_producto)}
              ${botonIcono('editar-producto', 'editar', `Editar ${p.nombre}`, p.id_producto)}
              ${botonIcono('borrar-producto', 'borrar', `Borrar ${p.nombre}`, p.id_producto, 'boton--peligro-suave')}
            </div></td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

function vistaMovimientos() {
  const f = estado.filtrosMovimientos;
  contenido.innerHTML = `
    ${encabezado('Movimientos de stock', 'Historial de solo lectura: un movimiento no se edita ni se borra (la API responde 405).', '/api/v1/movimientos-stock/ · GET con filtros y POST',
      boton('nuevo-movimiento', 'Registrar movimiento', 'mas', 'boton--primario'))}
    <form class="filtros" id="filtros-movimientos">
      <label class="campo"><span class="campo__etiqueta">Producto</span><select name="id_producto"><option value="">Todos</option>${opcionesHtml(paresProductos(), f.id_producto)}</select></label>
      <label class="campo"><span class="campo__etiqueta">Tipo</span><select name="tipo"><option value="">Todos</option>${opcionesHtml(TIPOS.map((t) => [t, t]), f.tipo)}</select></label>
      <label class="campo"><span class="campo__etiqueta">Desde</span><input type="date" name="desde" value="${esc(f.desde)}"></label>
      <label class="campo"><span class="campo__etiqueta">Hasta</span><input type="date" name="hasta" value="${esc(f.hasta)}"></label>
      ${boton('limpiar-movimientos', 'Limpiar filtros', '', 'boton--fantasma')}
    </form>
    <div id="resultado"><p class="cargando">Cargando…</p></div>`;
  const form = $('#filtros-movimientos');
  form.addEventListener('submit', (evento) => evento.preventDefault());
  form.addEventListener('change', () => {
    for (const clave of Object.keys(f)) f[clave] = form.elements[clave].value;
    tablaMovimientos();
  });
  return tablaMovimientos();
}

async function tablaMovimientos() {
  const mio = ++turno;
  const f = estado.filtrosMovimientos;
  let lista;
  try {
    lista = recientesPrimero(await traerTodo('/movimientos-stock/', {
      id_producto: f.id_producto,
      tipo: f.tipo,
      desde: inicioDelDia(f.desde),
      hasta: finDelDia(f.hasta),
    }));
  } catch (fallo) {
    if (mio === turno) $('#resultado').innerHTML = errorHtml(fallo.message);
    return;
  }
  if (mio !== turno) return;
  $('#resultado').innerHTML = lista.length
    ? `<p class="conteo">${plural(lista.length, 'movimiento', 'movimientos')}</p>
      <div class="tabla-envoltura">
        <table class="tabla">
          <thead><tr><th>Fecha</th><th>Producto</th><th>Tipo</th><th class="num">Cantidad</th><th>Motivo</th></tr></thead>
          <tbody>${lista.map((m) => `
            <tr>
              <td data-etiqueta="Fecha">${esc(verFecha(m.fecha))}</td>
              <td data-etiqueta="Producto" class="celda-titulo">${esc(nombreProducto(m.id_producto))}</td>
              <td data-etiqueta="Tipo">${etiquetaTipo(m.tipo)}</td>
              <td data-etiqueta="Cantidad" class="num"><span class="cantidad">${cantidadMovimiento(m)}</span></td>
              <td data-etiqueta="Motivo">${esc(m.motivo)}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>`
    : vacio(estado.movimientos.length ? 'No hay movimientos con esos filtros.' : 'Todavía no hay movimientos.');
}

function vistaCategorias() {
  const cuenta = contarPor('id_categoria');
  contenido.innerHTML = `
    ${encabezado('Categorías', 'Agrupan los productos. Una categoría con productos no se puede borrar.', '/api/v1/categorias/ · GET, POST, PATCH, DELETE y /{id}/productos',
      boton('nueva-categoria', 'Nueva categoría', 'mas', 'boton--primario'))}
    ${estado.categorias.length
      ? `<div class="tarjetas">${estado.categorias.map((c) => `
          <article class="tarjeta">
            <header><h2>${esc(c.nombre)}</h2><span class="pastilla">${plural(cuenta[c.id_categoria] ?? 0, 'producto', 'productos')}</span></header>
            <p class="tarjeta__texto">${c.descripcion ? esc(c.descripcion) : '<span class="tenue">Sin descripción</span>'}</p>
            <footer class="tarjeta__acciones">
              ${boton('productos-categoria', 'Ver productos', 'lista', 'boton--chico', c.id_categoria)}
              ${botonIcono('editar-categoria', 'editar', `Editar ${c.nombre}`, c.id_categoria)}
              ${botonIcono('borrar-categoria', 'borrar', `Borrar ${c.nombre}`, c.id_categoria, 'boton--peligro-suave')}
            </footer>
          </article>`).join('')}</div>`
      : vacio('Todavía no hay categorías.')}`;
}

function vistaProveedores() {
  const cuenta = contarPor('id_proveedor');
  const telefono = (t) => String(t).replace(/[^\d+]/g, '');
  contenido.innerHTML = `
    ${encabezado('Proveedores', 'Quién abastece cada producto. Un proveedor con productos no se puede borrar.', '/api/v1/proveedores/ · GET, POST, PATCH, DELETE y /{id}/productos',
      boton('nuevo-proveedor', 'Nuevo proveedor', 'mas', 'boton--primario'))}
    ${estado.proveedores.length
      ? `<div class="tarjetas">${estado.proveedores.map((p) => `
          <article class="tarjeta">
            <header><h2>${esc(p.nombre)}</h2><span class="pastilla">${plural(cuenta[p.id_proveedor] ?? 0, 'producto', 'productos')}</span></header>
            <dl class="datos">
              <div><dt>Origen</dt><dd>${esc(p.origen)}</dd></div>
              <div><dt>Teléfono</dt><dd><a href="tel:${esc(telefono(p.telefono))}">${esc(p.telefono)}</a></dd></div>
              <div><dt>Correo</dt><dd><a href="mailto:${esc(p.correo)}">${esc(p.correo)}</a></dd></div>
              <div><dt>Dirección</dt><dd>${esc(p.direccion)}</dd></div>
            </dl>
            <footer class="tarjeta__acciones">
              ${boton('productos-proveedor', 'Ver productos', 'lista', 'boton--chico', p.id_proveedor)}
              ${botonIcono('editar-proveedor', 'editar', `Editar ${p.nombre}`, p.id_proveedor)}
              ${botonIcono('borrar-proveedor', 'borrar', `Borrar ${p.nombre}`, p.id_proveedor, 'boton--peligro-suave')}
            </footer>
          </article>`).join('')}</div>`
      : vacio('Todavía no hay proveedores.')}`;
}

const VISTAS = { resumen: vistaResumen, productos: vistaProductos, movimientos: vistaMovimientos, categorias: vistaCategorias, proveedores: vistaProveedores };
const TITULOS = { resumen: 'Resumen', productos: 'Productos', movimientos: 'Movimientos', categorias: 'Categorías', proveedores: 'Proveedores' };

const vistaActual = () => {
  const vista = window.location.hash.slice(1);
  return VISTAS[vista] ? vista : 'resumen';
};

async function pintar() {
  if (!estado.cargado) return;
  turno += 1;
  const vista = vistaActual();
  for (const enlace of document.querySelectorAll('.pestanas a')) {
    if (enlace.dataset.vista === vista) enlace.setAttribute('aria-current', 'page');
    else enlace.removeAttribute('aria-current');
  }
  document.title = `${TITULOS[vista]} · StockFlow`;
  await VISTAS[vista]();
}

async function refrescar() {
  try {
    await cargarDatos();
  } catch (fallo) {
    aviso(fallo.message, 'error');
  }
  await pintar();
}

/* ---------- Acciones de los botones ---------- */

const ACCIONES = {
  recargar: async () => {
    await refrescar();
    aviso('Datos actualizados');
  },
  reintentar: () => iniciar(),
  'ver-bajos': () => {
    estado.filtrosProductos = { texto: '', id_categoria: '', id_proveedor: '', bajo_stock: true };
    if (vistaActual() === 'productos') pintar();
  },
  'nuevo-movimiento': () => formularioMovimiento(),
  'movimiento-producto': (id) => formularioMovimiento({ producto: productoPorId(id) }),
  reponer: (id) => formularioMovimiento({ producto: productoPorId(id), tipo: 'ENTRADA' }),
  'limpiar-movimientos': () => {
    estado.filtrosMovimientos = { id_producto: '', tipo: '', desde: '', hasta: '' };
    pintar();
  },
  'nuevo-producto': () => formularioProducto(),
  'editar-producto': (id) => formularioProducto(productoPorId(id)),
  'historial-producto': (id) => {
    const p = productoPorId(id);
    dialogoLista(`Historial de ${p.nombre}`, `${p.sku} · stock actual ${entero(p.stock_actual)} · GET /productos/${p.id_producto}/movimientos-stock`,
      async () => recientesPrimero(await traerTodo(`/productos/${p.id_producto}/movimientos-stock`)),
      (m) => filaMovimientoCorta(m, false), 'Este producto todavía no tiene movimientos.');
  },
  'borrar-producto': (id) => {
    const p = productoPorId(id);
    return borrar(`/productos/${p.id_producto}`, 'Borrar producto', `Se borrará «${p.nombre}» (${p.sku}). Si ya tiene movimientos, la API no lo permite.`, 'Producto borrado');
  },
  'nueva-categoria': () => formularioCategoria(),
  'editar-categoria': (id) => formularioCategoria(categoriaPorId(id)),
  'productos-categoria': (id) => {
    const c = categoriaPorId(id);
    dialogoLista(`Productos de ${c.nombre}`, `GET /categorias/${c.id_categoria}/productos`,
      () => traerTodo(`/categorias/${c.id_categoria}/productos`), filaProductoCorta, 'Esta categoría no tiene productos.');
  },
  'borrar-categoria': (id) => {
    const c = categoriaPorId(id);
    return borrar(`/categorias/${c.id_categoria}`, 'Borrar categoría', `Se borrará la categoría «${c.nombre}». Si tiene productos, la API no lo permite.`, 'Categoría borrada');
  },
  'nuevo-proveedor': () => formularioProveedor(),
  'editar-proveedor': (id) => formularioProveedor(proveedorPorId(id)),
  'productos-proveedor': (id) => {
    const p = proveedorPorId(id);
    dialogoLista(`Productos de ${p.nombre}`, `GET /proveedores/${p.id_proveedor}/productos`,
      () => traerTodo(`/proveedores/${p.id_proveedor}/productos`), filaProductoCorta, 'Este proveedor no tiene productos.');
  },
  'borrar-proveedor': (id) => {
    const p = proveedorPorId(id);
    return borrar(`/proveedores/${p.id_proveedor}`, 'Borrar proveedor', `Se borrará el proveedor «${p.nombre}». Si tiene productos, la API no lo permite.`, 'Proveedor borrado');
  },
};

document.addEventListener('click', (evento) => {
  const elemento = evento.target.closest('[data-accion]');
  const accion = elemento && ACCIONES[elemento.dataset.accion];
  if (!accion) return;
  if (elemento.tagName === 'BUTTON') evento.preventDefault();
  accion(elemento.dataset.id);
});

/* ---------- Estado de la API y tema ---------- */

async function revisarSalud() {
  const indicador = $('#estado-api');
  if (!indicador) return;
  const texto = $('span', indicador);
  try {
    const respuesta = await fetch('/health', { cache: 'no-store' });
    const datos = await respuesta.json();
    const enLinea = respuesta.ok && datos.status === 'ok';
    indicador.dataset.estado = enLinea ? 'ok' : 'error';
    texto.textContent = enLinea ? 'API en línea' : 'API con fallas';
  } catch {
    indicador.dataset.estado = 'error';
    texto.textContent = 'API sin conexión';
  }
  indicador.title = texto.textContent;
}

$('#cambiar-tema').addEventListener('click', () => {
  const raiz = document.documentElement;
  const oscuro = raiz.dataset.theme ? raiz.dataset.theme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  raiz.dataset.theme = oscuro ? 'light' : 'dark';
  try {
    localStorage.setItem('stockflow-tema', raiz.dataset.theme);
  } catch {
    // Sin almacenamiento del navegador: el tema dura hasta recargar.
  }
});

/* ---------- Arranque ---------- */

async function iniciar() {
  contenido.innerHTML = '<p class="cargando">Cargando datos de la API…</p>';
  revisarSalud();
  try {
    await cargarDatos();
  } catch (fallo) {
    contenido.innerHTML = `
      <section class="panel panel--error" role="alert">
        <h1>No se pudieron cargar los datos</h1>
        <p>${esc(fallo.message)}</p>
        ${boton('reintentar', 'Reintentar', 'recargar', 'boton--primario')}
      </section>`;
    return;
  }
  await pintar();
}

window.addEventListener('hashchange', () => {
  window.scrollTo(0, 0);
  pintar();
});

setInterval(revisarSalud, 60000);
iniciar();
