"""
database.py – Připojení k PostgreSQL
=====================================
Vytvoří SQLAlchemy engine a poskytuje funkci get_schema_ddl()
pro stažení struktury databáze (metadata, nikoliv data).
"""

from sqlalchemy import create_engine, text
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME


# ── SQLAlchemy engine ──
_connection_url = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
engine = create_engine(_connection_url)


def test_connection() -> bool:
    """Ověří, že se lze připojit k databázi. Vrací True/False."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_schema_ddl() -> str:
    """
    Stáhne z databáze pouze DDL – seznam tabulek a jejich sloupců
    z information_schema. NIKDY nestahuje samotná data.
    """
    query = text("""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        return "Databáze neobsahuje žádné tabulky ve schématu 'public'."

    # Sestavení čitelného DDL popisu
    ddl_lines: list[str] = []
    current_table = None
    for table_name, column_name, data_type, is_nullable in rows:
        if table_name != current_table:
            current_table = table_name
            ddl_lines.append(f"\nTabulka: {table_name}")
            ddl_lines.append("-" * (len(table_name) + 10))
        nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
        ddl_lines.append(f"  {column_name}  {data_type}  {nullable}")

    return "\n".join(ddl_lines)
