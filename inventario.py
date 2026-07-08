import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "Termopac.db"

def mostrar_inventario():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.codigo, a.nombre, i.stock_actual, i.stock_minimo
        FROM Inventario i
        JOIN Articulos a ON a.articulo_id = i.articulo_id
        ORDER BY a.codigo
    """)
    articulos = cursor.fetchall()

    print("\n===== INVENTARIO TERMOPAC =====")
    print(f"{'CÓDIGO':<10} {'ARTÍCULO':<30} {'STOCK ACTUAL':<15} {'STOCK MÍNIMO'}")
    print("-" * 70)
    for a in articulos:
        alerta = " ⚠ STOCK BAJO" if a["stock_actual"] <= a["stock_minimo"] else ""
        print(f"{a['codigo']:<10} {a['nombre']:<30} {a['stock_actual']:<15} {a['stock_minimo']}{alerta}")
    print("-" * 70)
    print(f"Total de artículos: {len(articulos)}")
    conn.close()

def verificar_articulo(codigo):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.codigo, a.nombre, a.descripcion, a.precio_unitario, i.stock_actual, i.stock_minimo
        FROM Inventario i
        JOIN Articulos a ON a.articulo_id = i.articulo_id
        WHERE a.codigo = ?
    """, (codigo,))
    a = cursor.fetchone()

    if a:
        print(f"\nArtículo: {a['nombre']}")
        print(f"Código: {a['codigo']}")
        print(f"Descripción: {a['descripcion']}")
        print(f"Precio unitario: RD${a['precio_unitario']:.2f}")
        print(f"Stock actual: {a['stock_actual']}")
        print(f"Stock mínimo: {a['stock_minimo']}")
    else:
        print(f"\nArtículo {codigo} no encontrado.")
    conn.close()

if __name__ == "__main__":
    mostrar_inventario()
    print("\n--- Consulta de artículo específico ---")
    verificar_articulo("ART-001")