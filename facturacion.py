import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "Termopac.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def listar_articulos_disponibles() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.codigo, a.nombre, a.precio_unitario, i.stock_actual
        FROM Articulos a
        JOIN Inventario i ON i.articulo_id = a.articulo_id
        WHERE a.activo = 1 AND i.stock_actual > 0
        ORDER BY a.codigo
        """
    )
    articulos = cursor.fetchall()
    conn.close()

    print("\n===== ARTÍCULOS DISPONIBLES PARA VENTA =====")
    print(f"{'CÓDIGO':<10} {'ARTÍCULO':<30} {'PRECIO':<12} {'STOCK'}")
    print("-" * 65)
    for a in articulos:
        print(f"{a['codigo']:<10} {a['nombre']:<30} RD${a['precio_unitario']:<10.2f} {a['stock_actual']}")
    print("-" * 65)
    print(f"Total: {len(articulos)} artículo(s)")


def generar_numero_factura() -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM Facturas")
    total = cursor.fetchone()["total"]
    conn.close()
    return f"FAC-{total + 1:04d}"


def crear_factura(cliente_nombre: str) -> tuple[int, str]:
    numero = generar_numero_factura()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Facturas (numero_factura, fecha, cliente_nombre, total)
        VALUES (?, ?, ?, 0)
        """,
        (numero, date.today().isoformat(), cliente_nombre.strip()),
    )
    factura_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return factura_id, numero


def agregar_detalle(factura_id: int, codigo: str, cantidad: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT a.articulo_id, a.precio_unitario, i.stock_actual
        FROM Articulos a
        JOIN Inventario i ON i.articulo_id = a.articulo_id
        WHERE a.codigo = ? AND a.activo = 1
        """,
        (codigo.strip().upper(),),
    )
    articulo = cursor.fetchone()
    if not articulo:
        conn.close()
        raise ValueError(f"El artículo '{codigo}' no existe o no está activo.")

    if cantidad <= 0:
        conn.close()
        raise ValueError("La cantidad debe ser mayor que cero.")

    if articulo["stock_actual"] < cantidad:
        conn.close()
        raise ValueError(
            f"Stock insuficiente. Disponible: {articulo['stock_actual']}, solicitado: {cantidad}."
        )

    subtotal = cantidad * articulo["precio_unitario"]
    try:
        cursor.execute(
            """
            INSERT INTO Detalle_Factura (factura_id, articulo_id, cantidad, precio_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
            """,
            (factura_id, articulo["articulo_id"], cantidad, articulo["precio_unitario"], subtotal),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError(str(exc)) from exc
    finally:
        conn.close()


def mostrar_factura(numero_factura: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT factura_id, numero_factura, fecha, cliente_nombre, total
        FROM Facturas
        WHERE numero_factura = ?
        """,
        (numero_factura.strip().upper(),),
    )
    factura = cursor.fetchone()
    if not factura:
        conn.close()
        print(f"\nFactura '{numero_factura}' no encontrada.")
        return

    cursor.execute(
        """
        SELECT a.codigo, a.nombre, d.cantidad, d.precio_unitario, d.subtotal
        FROM Detalle_Factura d
        JOIN Articulos a ON a.articulo_id = d.articulo_id
        WHERE d.factura_id = ?
        ORDER BY d.detalle_id
        """,
        (factura["factura_id"],),
    )
    detalles = cursor.fetchall()
    conn.close()

    print("\n===== FACTURA =====")
    print(f"Número:   {factura['numero_factura']}")
    print(f"Fecha:    {factura['fecha']}")
    print(f"Cliente:  {factura['cliente_nombre']}")
    print("-" * 65)
    print(f"{'CÓDIGO':<10} {'ARTÍCULO':<22} {'CANT.':<6} {'PRECIO':<12} {'SUBTOTAL'}")
    print("-" * 65)
    for d in detalles:
        print(
            f"{d['codigo']:<10} {d['nombre']:<22} {d['cantidad']:<6} "
            f"RD${d['precio_unitario']:<10.2f} RD${d['subtotal']:.2f}"
        )
    print("-" * 65)
    print(f"{'TOTAL:':>54} RD${factura['total']:.2f}")


def listar_facturas() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT numero_factura, fecha, cliente_nombre, total
        FROM Facturas
        ORDER BY factura_id DESC
        """
    )
    facturas = cursor.fetchall()
    conn.close()

    print("\n===== FACTURAS REGISTRADAS =====")
    print(f"{'NÚMERO':<12} {'FECHA':<12} {'CLIENTE':<25} {'TOTAL'}")
    print("-" * 65)
    for f in facturas:
        print(
            f"{f['numero_factura']:<12} {f['fecha']:<12} {f['cliente_nombre']:<25} RD${f['total']:.2f}"
        )
    print("-" * 65)
    print(f"Total de facturas: {len(facturas)}")


def registrar_venta() -> None:
    cliente = input("\nNombre del cliente: ").strip()
    if not cliente:
        print("Debe indicar el nombre del cliente.")
        return

    factura_id, numero = crear_factura(cliente)
    print(f"\nFactura {numero} creada. Agregue los artículos (código vacío para terminar).")

    while True:
        listar_articulos_disponibles()
        codigo = input("\nCódigo del artículo (Enter para finalizar): ").strip()
        if not codigo:
            break

        try:
            cantidad = int(input("Cantidad: ").strip())
            agregar_detalle(factura_id, codigo, cantidad)
            print("Línea agregada. El inventario se actualiza automáticamente por trigger.")
        except ValueError as exc:
            print(f"Error: {exc}")

    mostrar_factura(numero)


def menu() -> None:
    opciones = {
        "1": ("Ver artículos disponibles", listar_articulos_disponibles),
        "2": ("Registrar nueva venta", registrar_venta),
        "3": ("Consultar factura", lambda: mostrar_factura(input("Número de factura: ").strip())),
        "4": ("Listar facturas", listar_facturas),
        "0": ("Salir", None),
    }

    while True:
        print("\n===== FACTURACIÓN TERMOPAC =====")
        for clave, (texto, _) in opciones.items():
            print(f"  {clave}. {texto}")

        opcion = input("\nSeleccione una opción: ").strip()
        if opcion == "0":
            print("Saliendo...")
            break

        accion = opciones.get(opcion)
        if not accion:
            print("Opción no válida.")
            continue

        accion[1]()


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"No se encontró la base de datos en: {DB_PATH}")
        print("Ejecute primero: python init_db.py")
    else:
        menu()
