# Registro de Ingresos vs Gastos (Google Apps Script)

Página web para registrar ingresos y gastos que se guardan en Google Sheets y
muestra las 3 hojas del Excel `Ingreso_vs_gastos.xlsx`:

| Pestaña web       | Hoja de Google Sheets | Qué hace |
|-------------------|-----------------------|----------|
| Registrar         | Movimientos           | Formulario: agrega movimientos (A, C:F y la fórmula del mes en B) |
| Movimientos       | Movimientos           | Tabla con filtros por mes, tipo, categoría y texto; editar / eliminar |
| Resumen Mensual   | Resumen Mensual       | Tabla del año + gráfico mensual + gastos por categoría |
| Acumulado         | Acumulado             | Saldo inicial editable (D3), acumulado mes a mes y gráfico |

## Instalación

1. Sube `Ingreso_vs_gastos.xlsx` a Google Drive y ábrelo con **Google Sheets**
   (Archivo → Guardar como Hojas de cálculo de Google). Los nombres de las hojas
   deben seguir siendo `Movimientos`, `Resumen Mensual` y `Acumulado`.
2. En el Google Sheet: **Extensiones → Apps Script**.
3. Reemplaza el contenido de `Código.gs` por `Code.gs`.
4. Crea un archivo HTML (**+ → HTML**) llamado exactamente `Index` y pega `Index.html`.
5. (Opcional) En ⚙ Configuración del proyecto marca *Mostrar el archivo de manifiesto
   "appsscript.json"* y pega `appsscript.json` (zona horaria de Bogotá).
6. **Implementar → Nueva implementación → Aplicación web**
   - Ejecutar como: *Yo*
   - Quién tiene acceso: *Solo yo* (o quien quieras)
7. Autoriza los permisos y abre la URL que termina en `/exec`.

También aparece el menú **💰 Finanzas → Abrir registro** dentro del Google Sheet
(barra lateral) al recargar la hoja.

> Si creaste el script como proyecto independiente (no desde la hoja), pega el ID
> del Google Sheet en la constante `SPREADSHEET_ID` de `Code.gs`.

> Cada vez que cambies el código, ve a **Implementar → Gestionar implementaciones →
> Editar → Nueva versión** para que la URL `/exec` use la versión nueva.

## Notas

- Eliminar un movimiento borra su contenido sin borrar la fila, para no romper los
  rangos `$F$2:$F$201` de las fórmulas; el siguiente registro reutiliza ese espacio.
- Si los registros pasan de la fila 201, el script cambia automáticamente las
  fórmulas del Resumen Mensual a rangos abiertos (`$F$2:$F`).
- Las categorías se leen de la validación de datos de la columna C; si agregas una
  categoría a esa lista en la hoja, aparece sola en el formulario.
