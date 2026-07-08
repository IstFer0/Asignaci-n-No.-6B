import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from db.init_db import get_connection, init_db


def run_demo() -> None:
    """Ejecuta una demostración de venta y muestra el estado del inventario."""
    init_db()

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO Facturas (numero_factura, fecha, cliente_nombre, total)
            VALUES (?, ?, ?, ?)
            """,
            ("FAC-0001", "2026-07-07", "Cliente Demo", 0.0),
        )
        factura_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Detalle_Factura (factura_id, articulo_id, cantidad, precio_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
            """,
            (factura_id, 1, 2, 1200.0, 2400.0),
        )

        conn.commit()

        print("Factura insertada correctamente.")

        row = cursor.execute(
            "SELECT stock_actual FROM Inventario WHERE articulo_id = 1"
        ).fetchone()
        print(f"Stock actual del artículo 1 después de la venta: {row['stock_actual']}")

    except sqlite3.IntegrityError as exc:
        conn.rollback()
        print(f"Error de integridad: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_demo()
