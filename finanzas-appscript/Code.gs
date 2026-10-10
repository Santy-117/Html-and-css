/**
 * Registro de Ingresos vs Gastos — Google Apps Script
 *
 * Funciona con el Google Sheet creado a partir de "Ingreso_vs_gastos.xlsx",
 * que tiene las hojas:
 *   - Movimientos       (A: Fecha, B: Mes (Nº), C: Categoría, D: Descripción, E: Tipo, F: Monto)
 *   - Resumen Mensual   (A4:D15 meses, fila 16 TOTAL AÑO)
 *   - Acumulado         (D3 saldo inicial, A6:F17 meses, E19 saldo a fin de año)
 */

// Si el script está creado DESDE la hoja (Extensiones > Apps Script) déjalo vacío.
// Si es un proyecto independiente, pega aquí el ID del Google Sheet
// (la parte de la URL entre /d/ y /edit).
const SPREADSHEET_ID = '';

// ID del logo en Google Drive (la parte del link entre /d/ y /view).
const LOGO_ID = '1IAKwSst4Xa7TVyRdv-GbXbeak5Czatbn';

const HOJA_MOV = 'Movimientos';
const HOJA_RESUMEN = 'Resumen Mensual';
const HOJA_ACUM = 'Acumulado';

const CATEGORIAS_DEFECTO = [
  'Prestamo', 'Salario', 'Freelance', 'Otros ingresos', 'Arriendo', 'Servicios',
  'Comida', 'Transporte', 'Salud', 'Entretenimiento', 'Educación', 'Deudas',
  'Ahorro', 'Otros gastos'
];
const TIPOS = ['Ingreso', 'Gasto'];

/* ------------------------------------------------------------------ */
/*  Web app                                                            */
/* ------------------------------------------------------------------ */

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Ingresos vs Gastos')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/** Menú dentro del Google Sheet para abrir el formulario como barra lateral. */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('💰 Finanzas')
    .addItem('Abrir registro', 'abrirBarraLateral')
    .addToUi();
}

function abrirBarraLateral() {
  const html = HtmlService.createHtmlOutputFromFile('Index').setTitle('Ingresos vs Gastos');
  SpreadsheetApp.getUi().showSidebar(html);
}

/* ------------------------------------------------------------------ */
/*  Utilidades                                                         */
/* ------------------------------------------------------------------ */

function libro_() {
  return SPREADSHEET_ID
    ? SpreadsheetApp.openById(SPREADSHEET_ID)
    : SpreadsheetApp.getActiveSpreadsheet();
}

function hoja_(nombre) {
  const sh = libro_().getSheetByName(nombre);
  if (!sh) throw new Error('No se encontró la hoja "' + nombre + '".');
  return sh;
}

/** Date -> "yyyy-MM-dd" (google.script.run no puede devolver objetos Date). */
function fechaATexto_(d) {
  if (!(d instanceof Date)) return d ? String(d) : '';
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

/** "yyyy-MM-dd" -> Date local (sin desfase de zona horaria). */
function textoAFecha_(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ''));
  if (!m) throw new Error('Fecha inválida.');
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function numero_(v) {
  return typeof v === 'number' ? v : Number(v) || 0;
}

function validar_(mov) {
  if (!mov) throw new Error('No llegaron datos.');
  const fecha = textoAFecha_(mov.fecha);
  const categoria = String(mov.categoria || '').trim();
  const descripcion = String(mov.descripcion || '').trim();
  const tipo = String(mov.tipo || '').trim();
  const monto = Number(mov.monto);

  if (!categoria) throw new Error('Selecciona una categoría.');
  if (TIPOS.indexOf(tipo) === -1) throw new Error('El tipo debe ser Ingreso o Gasto.');
  if (!isFinite(monto) || monto <= 0) throw new Error('El monto debe ser mayor a 0.');

  return [fecha, categoria, descripcion, tipo, monto];
}

/** Escribe un movimiento en la fila indicada (A y C:F) y la fórmula del mes en B. */
function escribirFila_(sh, fila, datos) {
  sh.getRange(fila, 1).setValue(datos[0]).setNumberFormat('dd/mm/yyyy');
  sh.getRange(fila, 2).setFormulaR1C1('=IF(RC[-1]="","",MONTH(RC[-1]))');
  sh.getRange(fila, 3, 1, 4).setValues([datos.slice(1)]);
  sh.getRange(fila, 6).setNumberFormat('#,##0');
}

/** Primera fila vacía (columna A vacía) desde la fila 2. */
function siguienteFila_(sh) {
  const ultima = Math.max(sh.getLastRow(), 2);
  const colA = sh.getRange(2, 1, ultima - 1, 1).getValues();
  for (let i = 0; i < colA.length; i++) {
    if (colA[i][0] === '' || colA[i][0] === null) return i + 2;
  }
  return ultima + 1;
}

/**
 * Las fórmulas originales del Excel solo llegan a la fila 201.
 * Si se pasa de ahí, las convierte en rangos abiertos (F2:F) para que
 * el Resumen y el Acumulado sigan sumando todo.
 */
function ampliarFormulasResumen_() {
  const rango = hoja_(HOJA_RESUMEN).getRange('B4:C15');
  const formulas = rango.getFormulas();
  let cambio = false;
  const nuevas = formulas.map(fila => fila.map(f => {
    if (/\$201\b/.test(f)) {
      cambio = true;
      return f.replace(/(\$[A-Z]+\$2:\$[A-Z]+)\$201/g, '$1');
    }
    return f;
  }));
  if (cambio) rango.setFormulas(nuevas);
}

/* ------------------------------------------------------------------ */
/*  API llamada desde Index.html (google.script.run)                   */
/* ------------------------------------------------------------------ */

/** Categorías tomadas de la validación de datos de la hoja (o la lista por defecto). */
function obtenerCategorias() {
  try {
    const sh = hoja_(HOJA_MOV);
    const regla = sh.getRange('C12').getDataValidation() || sh.getRange('C2').getDataValidation();
    if (regla && regla.getCriteriaType() === SpreadsheetApp.DataValidationCriteria.VALUE_IN_LIST) {
      const lista = regla.getCriteriaValues()[0];
      if (lista && lista.length) return lista;
    }
  } catch (e) {
    console.warn(e);
  }
  return CATEGORIAS_DEFECTO;
}

function agregarMovimiento(mov) {
  const datos = validar_(mov);
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = hoja_(HOJA_MOV);
    const fila = siguienteFila_(sh);
    escribirFila_(sh, fila, datos);
    if (fila > 201) ampliarFormulasResumen_();
    SpreadsheetApp.flush();
    return { ok: true, fila: fila };
  } finally {
    lock.releaseLock();
  }
}

function editarMovimiento(fila, mov) {
  fila = Number(fila);
  if (!fila || fila < 2) throw new Error('Fila inválida.');
  const datos = validar_(mov);
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    escribirFila_(hoja_(HOJA_MOV), fila, datos);
    SpreadsheetApp.flush();
    return { ok: true, fila: fila };
  } finally {
    lock.releaseLock();
  }
}

/**
 * Borra el contenido del movimiento (no elimina la fila) para no romper
 * los rangos $F$2:$F$201 de las fórmulas. La fila libre se reutiliza
 * en el siguiente registro.
 */
function eliminarMovimiento(fila) {
  fila = Number(fila);
  if (!fila || fila < 2) throw new Error('Fila inválida.');
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = hoja_(HOJA_MOV);
    sh.getRange(fila, 1).clearContent();
    sh.getRange(fila, 3, 1, 4).clearContent();
    SpreadsheetApp.flush();
    return { ok: true };
  } finally {
    lock.releaseLock();
  }
}

function guardarSaldoInicial(valor) {
  const n = Number(valor);
  if (!isFinite(n)) throw new Error('Saldo inicial inválido.');
  hoja_(HOJA_ACUM).getRange('D3').setValue(n);
  SpreadsheetApp.flush();
  return { ok: true };
}

/**
 * Devuelve el logo como data URL (base64). Se lee desde Drive con los permisos
 * de quien implementa la app, así que el archivo no necesita ser público.
 * Respuesta: { id, url } si todo bien, o { id, error } si algo falló.
 */
function obtenerLogo() {
  if (!LOGO_ID) return { id: '', error: 'LOGO_ID está vacío en Code.gs.' };
  const cache = CacheService.getScriptCache();
  const enCache = cache.get('logo_' + LOGO_ID);
  if (enCache) return { id: LOGO_ID, url: enCache };
  try {
    const archivo = DriveApp.getFileById(LOGO_ID);
    let blob = archivo.getBlob();
    if (!/^image\//.test(blob.getContentType())) {
      // Si no es imagen (p. ej. PDF), intenta con la miniatura que genera Drive.
      blob = archivo.getThumbnail();
      if (!blob) throw new Error('El archivo "' + archivo.getName() + '" no es una imagen (' + archivo.getMimeType() + ').');
    }
    const url = 'data:' + blob.getContentType() + ';base64,' + Utilities.base64Encode(blob.getBytes());
    if (url.length < 100000) cache.put('logo_' + LOGO_ID, url, 21600); // máx. 100 KB en caché, 6 h
    return { id: LOGO_ID, url: url };
  } catch (e) {
    console.warn('No se pudo cargar el logo: ' + e);
    return { id: LOGO_ID, error: String(e && e.message || e) };
  }
}

/**
 * Ejecuta esta función desde el editor (botón ▶ Ejecutar) para:
 *  1) autorizar el permiso de Google Drive, y
 *  2) ver en el "Registro de ejecución" si el logo se puede leer.
 */
function probarLogo() {
  CacheService.getScriptCache().remove('logo_' + LOGO_ID);
  const archivo = DriveApp.getFileById(LOGO_ID);
  console.log('Archivo: ' + archivo.getName() + ' | Tipo: ' + archivo.getMimeType() + ' | Tamaño: ' + archivo.getSize() + ' bytes');
  const r = obtenerLogo();
  console.log(r.url ? 'OK: logo listo (' + r.url.length + ' caracteres en base64).' : 'ERROR: ' + r.error);
}

/** Devuelve la información de las 3 hojas en un solo llamado. */
function obtenerDatos() {
  // --- Movimientos ---
  const shMov = hoja_(HOJA_MOV);
  const ultima = shMov.getLastRow();
  const movimientos = [];
  if (ultima >= 2) {
    const valores = shMov.getRange(2, 1, ultima - 1, 6).getValues();
    valores.forEach((r, i) => {
      if (r[0] === '' || r[0] === null) return;
      const fecha = r[0] instanceof Date ? r[0] : null;
      movimientos.push({
        fila: i + 2,
        fecha: fechaATexto_(r[0]),
        mes: fecha ? fecha.getMonth() + 1 : numero_(r[1]),
        anio: fecha ? fecha.getFullYear() : null,
        categoria: String(r[2]),
        descripcion: String(r[3]),
        tipo: String(r[4]),
        monto: numero_(r[5])
      });
    });
  }

  // --- Resumen Mensual ---
  const shRes = hoja_(HOJA_RESUMEN);
  const resumen = shRes.getRange('A4:D15').getValues().map(r => ({
    mes: String(r[0]),
    ingresos: numero_(r[1]),
    gastos: numero_(r[2]),
    ahorro: numero_(r[3])
  }));
  const tot = shRes.getRange('B16:D16').getValues()[0];
  const totalAnio = { ingresos: numero_(tot[0]), gastos: numero_(tot[1]), ahorro: numero_(tot[2]) };

  // --- Acumulado ---
  const shAc = hoja_(HOJA_ACUM);
  const saldoInicial = numero_(shAc.getRange('D3').getValue());
  const acumulado = shAc.getRange('A6:F17').getValues().map(r => ({
    mes: String(r[0]),
    ingresos: numero_(r[1]),
    gastos: numero_(r[2]),
    ahorro: numero_(r[3]),
    acumulado: numero_(r[4]),
    variacion: r[5] === '' ? null : numero_(r[5])
  }));
  const saldoFinal = numero_(shAc.getRange('E19').getValue());

  return {
    movimientos: movimientos,
    resumen: resumen,
    totalAnio: totalAnio,
    saldoInicial: saldoInicial,
    acumulado: acumulado,
    saldoFinal: saldoFinal,
    categorias: obtenerCategorias(),
    urlHoja: libro_().getUrl()
  };
}
