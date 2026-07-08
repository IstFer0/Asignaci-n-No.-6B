import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "Termopac.db"


def get_connection() -> sqlite3.Connection:
    """Crea o devuelve una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Crea todas las tablas y los triggers necesarios para el proyecto."""
    cursor = conn.cursor()

    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS Articulos (
            articulo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
            activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
        );

        CREATE TABLE IF NOT EXISTS Inventario (
            inventario_id INTEGER PRIMARY KEY AUTOINCREMENT,
            articulo_id INTEGER NOT NULL UNIQUE,
            stock_actual INTEGER NOT NULL CHECK (stock_actual >= 0),
            stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
            FOREIGN KEY (articulo_id) REFERENCES Articulos(articulo_id)
        );

        CREATE TABLE IF NOT EXISTS Facturas (
            factura_id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_factura TEXT NOT NULL UNIQUE,
            fecha TEXT NOT NULL,
            cliente_nombre TEXT NOT NULL,
            total REAL NOT NULL DEFAULT 0 CHECK (total >= 0)
        );

        CREATE TABLE IF NOT EXISTS Detalle_Factura (
            detalle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER NOT NULL,
            articulo_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
            subtotal REAL NOT NULL CHECK (subtotal >= 0 AND subtotal = cantidad * precio_unitario),
            FOREIGN KEY (factura_id) REFERENCES Facturas(factura_id),
            FOREIGN KEY (articulo_id) REFERENCES Articulos(articulo_id)
        );

        CREATE INDEX IF NOT EXISTS idx_detalle_factura_factura_id
            ON Detalle_Factura(factura_id);

        CREATE INDEX IF NOT EXISTS idx_detalle_factura_articulo_id
            ON Detalle_Factura(articulo_id);

        CREATE INDEX IF NOT EXISTS idx_inventario_articulo_id
            ON Inventario(articulo_id);

        DROP TRIGGER IF EXISTS trg_validar_stock_suficiente;
        DROP TRIGGER IF EXISTS trg_validar_stock_suficiente_update;
        DROP TRIGGER IF EXISTS trg_descuento_inventario;
        DROP TRIGGER IF EXISTS trg_actualizar_total_factura_insert;
        DROP TRIGGER IF EXISTS trg_reponer_inventario;
        DROP TRIGGER IF EXISTS trg_ajustar_inventario_y_total_update;

        CREATE TRIGGER trg_validar_stock_suficiente
        BEFORE INSERT ON Detalle_Factura
        BEGIN
            SELECT CASE
                WHEN (SELECT COUNT(*) FROM Inventario WHERE articulo_id = NEW.articulo_id) = 0 THEN
                    RAISE(ABORT, 'El artículo no existe en Inventario.')
                WHEN (SELECT stock_actual FROM Inventario WHERE articulo_id = NEW.articulo_id) < NEW.cantidad THEN
                    RAISE(ABORT, 'No hay suficiente inventario para realizar la venta.')
            END;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_validar_stock_suficiente_update
        BEFORE UPDATE OF cantidad, articulo_id ON Detalle_Factura
        BEGIN
            SELECT CASE
                WHEN (SELECT COUNT(*) FROM Inventario WHERE articulo_id = NEW.articulo_id) = 0 THEN
                    RAISE(ABORT, 'El artículo no existe en Inventario.')
                WHEN NEW.articulo_id = OLD.articulo_id AND
                     (SELECT stock_actual FROM Inventario WHERE articulo_id = NEW.articulo_id) + OLD.cantidad < NEW.cantidad THEN
                    RAISE(ABORT, 'No hay suficiente inventario para modificar la venta.')
                WHEN NEW.articulo_id != OLD.articulo_id AND
                     (SELECT stock_actual FROM Inventario WHERE articulo_id = NEW.articulo_id) < NEW.cantidad THEN
                    RAISE(ABORT, 'No hay suficiente inventario para modificar la venta.')
            END;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_descuento_inventario
        AFTER INSERT ON Detalle_Factura
        BEGIN
            UPDATE Inventario
            SET stock_actual = stock_actual - NEW.cantidad
            WHERE articulo_id = NEW.articulo_id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_actualizar_total_factura_insert
        AFTER INSERT ON Detalle_Factura
        BEGIN
            UPDATE Facturas
            SET total = COALESCE((
                SELECT SUM(subtotal)
                FROM Detalle_Factura
                WHERE factura_id = NEW.factura_id
            ), 0)
            WHERE factura_id = NEW.factura_id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_reponer_inventario
        AFTER DELETE ON Detalle_Factura
        BEGIN
            UPDATE Inventario
            SET stock_actual = stock_actual + OLD.cantidad
            WHERE articulo_id = OLD.articulo_id;

            UPDATE Facturas
            SET total = COALESCE((
                SELECT SUM(subtotal)
                FROM Detalle_Factura
                WHERE factura_id = OLD.factura_id
            ), 0)
            WHERE factura_id = OLD.factura_id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_ajustar_inventario_update
        AFTER UPDATE OF cantidad, articulo_id ON Detalle_Factura
        BEGIN
            UPDATE Inventario
            SET stock_actual = stock_actual + OLD.cantidad
            WHERE articulo_id = OLD.articulo_id;

            UPDATE Inventario
            SET stock_actual = stock_actual - NEW.cantidad
            WHERE articulo_id = NEW.articulo_id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_actualizar_total_factura_update
        AFTER UPDATE ON Detalle_Factura
        BEGIN
            UPDATE Facturas
            SET total = COALESCE((
                SELECT SUM(subtotal)
                FROM Detalle_Factura
                WHERE factura_id = OLD.factura_id
            ), 0)
            WHERE factura_id = OLD.factura_id;

            UPDATE Facturas
            SET total = COALESCE((
                SELECT SUM(subtotal)
                FROM Detalle_Factura
                WHERE factura_id = NEW.factura_id
            ), 0)
            WHERE factura_id = NEW.factura_id;
        END;
        """
    )


def seed_data(conn: sqlite3.Connection) -> None:
    """Inserta datos iniciales para probar el funcionamiento de la base de datos."""
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO Articulos (codigo, nombre, descripcion, precio_unitario)
        VALUES
            ('ART-001', 'Laptop', 'Laptop de 14 pulgadas', 1200.00),
            ('ART-002', 'Mouse', 'Mouse óptico inalámbrico', 25.50),
            ('ART-003', 'Teclado', 'Teclado mecánico', 89.99)
        """
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO Inventario (articulo_id, stock_actual, stock_minimo)
        VALUES
            ((SELECT articulo_id FROM Articulos WHERE codigo = 'ART-001'), 10, 2),
            ((SELECT articulo_id FROM Articulos WHERE codigo = 'ART-002'), 20, 5),
            ((SELECT articulo_id FROM Articulos WHERE codigo = 'ART-003'), 15, 3)
        """
    )

    conn.commit()


def init_db() -> None:
    """Inicializa la base de datos y carga datos de prueba."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    try:
        create_schema(conn)
        seed_data(conn)
        print(f"Base de datos creada correctamente en: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
