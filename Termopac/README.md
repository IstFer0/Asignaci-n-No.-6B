# Termopac

## Descripción

Termopac es una pequeña aplicación de ventas que utiliza SQLite como motor de base de datos y Python para la inicialización y demostración de flujo de facturación. El proyecto integra facturación e inventario mediante triggers en la base de datos, lo que garantiza que la lógica de negocio se aplique en el nivel de datos.

## Tecnologías utilizadas

- Python 3
- SQLite
- `sqlite3` (módulo estándar de Python)

## Estructura del proyecto

- `db/init_db.py`: crea el esquema de la base de datos, los triggers, índices y datos de ejemplo.
- `db/Termopac.db`: base de datos SQLite generada (no se debe versionar en el repositorio).
- `tests/test_sales_flow.py`: script de demostración del flujo de venta.
- `.gitignore`: reglas para ignorar archivos generados y entornos locales.

## Diseño de la base de datos

El modelo de datos está compuesto por cuatro tablas principales:

- `Articulos`
- `Inventario`
- `Facturas`
- `Detalle_Factura`

### Tabla `Articulos`

Almacena los datos básicos de cada artículo:

- `articulo_id`: clave primaria.
- `codigo`: identificador único del producto.
- `nombre`: nombre descriptivo.
- `descripcion`: información adicional.
- `precio_unitario`: precio por unidad con validación de valores no negativos.
- `activo`: indicador booleano de disponibilidad.

### Tabla `Inventario`

Mantiene el stock de artículos:

- `inventario_id`: clave primaria.
- `articulo_id`: referencia a `Articulos`.
- `stock_actual`: cantidad disponible en inventario.
- `stock_minimo`: mínimo permitido para control de inventario.

### Tabla `Facturas`

Representa la cabecera de la factura:

- `factura_id`: clave primaria.
- `numero_factura`: número de factura único.
- `fecha`: fecha de la factura.
- `cliente_nombre`: nombre del cliente.
- `total`: suma de los subtotales de los detalles.

### Tabla `Detalle_Factura`

Guarda cada línea de la factura:

- `detalle_id`: clave primaria.
- `factura_id`: referencia a la factura.
- `articulo_id`: referencia al artículo vendido.
- `cantidad`: unidades vendidas.
- `precio_unitario`: precio unitario aplicado.
- `subtotal`: total de la línea, con validación de consistencia (`cantidad * precio_unitario`).

## Explicación de los triggers

La lógica de inventario y facturación se mantiene dentro de la base de datos para garantizar consistencia y evitar que el código Python tenga que replicar reglas críticas.

- `trg_validar_stock_suficiente`
  - `BEFORE INSERT ON Detalle_Factura`
  - Verifica que el artículo exista en `Inventario`.
  - Valida que el stock disponible sea suficiente antes de permitir la inserción.

- `trg_validar_stock_suficiente_update`
  - `BEFORE UPDATE OF cantidad, articulo_id ON Detalle_Factura`
  - Valida existencia y stock cuando se modifica la cantidad o el artículo.

- `trg_descuento_inventario`
  - `AFTER INSERT ON Detalle_Factura`
  - Descarga el inventario restando la cantidad vendida.

- `trg_actualizar_total_factura_insert`
  - `AFTER INSERT ON Detalle_Factura`
  - Recalcula el total de la factura sumando todos los subtotales.

- `trg_reponer_inventario`
  - `AFTER DELETE ON Detalle_Factura`
  - Devuelve al inventario la cantidad eliminada.
  - Recalcula el total de la factura tras eliminar el detalle.

- `trg_ajustar_inventario_y_total_update`
  - `AFTER UPDATE ON Detalle_Factura`
  - Ajusta el inventario si cambia la cantidad o el artículo.
  - Recalcula el total de la factura para mantener consistencia.

## Cómo crear la base de datos

Desde la raíz del proyecto, ejecuta:

```bash
python db/init_db.py
```

Esto crea el archivo de base de datos `db/Termopac.db` y carga datos iniciales.

## Cómo ejecutar los scripts de prueba

El script de demostración se ejecuta con:

```bash
python tests/test_sales_flow.py
```

Este script inicializa la base de datos y realiza una venta de ejemplo para mostrar el cambio en el inventario.

## Ejemplo del flujo completo de una venta

1. Se crea la base de datos y se insertan datos de ejemplo.
2. Se inserta una factura en `Facturas`.
3. Se agrega un detalle de factura en `Detalle_Factura`.
4. El trigger `trg_validar_stock_suficiente` verifica el stock y existencia del artículo.
5. El trigger `trg_descuento_inventario` reduce el stock en `Inventario`.
6. El trigger `trg_actualizar_total_factura_insert` recalcula `Facturas.total`.

Si se borra un detalle de factura, `trg_reponer_inventario` devuelve la cantidad al inventario y actualiza el total.

Si se modifica un detalle, `trg_validar_stock_suficiente_update` y `trg_ajustar_inventario_y_total_update` mantienen la consistencia de inventario y total.

## Justificación del uso de triggers

Utilizar triggers permite mantener la integridad entre inventario y facturación en el nivel de datos. Esto reduce la posibilidad de inconsistencias cuando múltiples procesos o scripts interactúan con la base de datos y centraliza las reglas de negocio en un solo lugar, sin depender del código Python para su ejecución.
