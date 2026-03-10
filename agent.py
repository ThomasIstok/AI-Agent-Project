"""
Text-to-SQL Agent
=================
AI agent, který přeloží text dotaz do SQL pomocí Groq API (LLaMA),
ověří jeho bezpečnost a spustí ho v lokální PostgreSQL databázi.

"""

import os
import re
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from groq import Groq


# ──────────────────────────────────────────────
# 1. Načtení přihlašovacích údajů (pouze do RAM)
# ──────────────────────────────────────────────

load_dotenv()

_db_user = os.getenv("DB_USER")
_db_password = os.getenv("DB_PASSWORD")

_db_host = os.getenv("DB_HOST")
_db_port = os.getenv("DB_PORT")
_db_name = os.getenv("DB_NAME")
_groq_key = os.getenv("GROQ_API_KEY")

# Kontrola, že všechny proměnné existují (bez výpisu hodnot!)
_required = {
    "DB_USER": _db_user,
    "DB_PASSWORD": _db_password,
    "DB_HOST": _db_host,
    "DB_PORT": _db_port,
    "DB_NAME": _db_name,
    "GROQ_API_KEY": _groq_key,
}

_missing = [k for k, v in _required.items() if not v]
if _missing:
    print(f"❌ Chybí povinné proměnné v .env: {', '.join(_missing)}")
    sys.exit(1)


# ──────────────────────────────────────────────
# 2. Připojení k databázi (SQLAlchemy + psycopg2)
# ──────────────────────────────────────────────

_connection_url = (
    f"postgresql+psycopg2://{_db_user}:{_db_password}"
    f"@{_db_host}:{_db_port}/{_db_name}"
)
engine = create_engine(_connection_url)

# Ověření připojení
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Připojení k databázi bylo úspěšné.\n")
except Exception as e:
    print(f"❌ Nepodařilo se připojit k databázi: {e}")
    sys.exit(1)


# ──────────────────────────────────────────────
# 3. Konfigurace Groq API
# ──────────────────────────────────────────────

client = Groq(api_key=_groq_key)


# ──────────────────────────────────────────────
# 4. Pomocné funkce
# ──────────────────────────────────────────────

def get_schema_ddl(eng) -> str:
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
    with eng.connect() as conn:
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


def generate_sql(user_question: str, ddl_context: str) -> str:
    """
    Odešle dotaz a DDL kontext do Groq API (LLaMA model).
    Systémový prompt přikazuje vrátit VÝHRADNĚ čistý SQL.
    """
    system_prompt = (
        "Jsi SQL expert. Na základě následující struktury databáze "
        "a uživatelova dotazu vygeneruj SQL dotaz.\n\n"
        "PRAVIDLA:\n"
        "1. Vrať VÝHRADNĚ čistý SQL dotaz.\n"
        "2. Žádný markdown, žádné vysvětlování, žádné komentáře.\n"
        "3. Dotaz MUSÍ začínat slovem SELECT.\n"
        "4. Nepoužívej žádné destruktivní příkazy (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE).\n\n"
        f"STRUKTURA DATABÁZE:\n{ddl_context}"
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
        temperature=0.0,
        max_tokens=1024,
    )

    # Vyčistit případné markdown backticks
    sql = response.choices[0].message.content.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip()


# ──────────────────────────────────────────────
# 5. Bezpečnostní guardrails
# ──────────────────────────────────────────────

_FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT",
    "ALTER", "TRUNCATE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE", "CREATE", "--", "/*",
]


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Přísná validace SQL dotazu:
    - Musí začínat slovem SELECT.
    - Nesmí obsahovat zakázaná klíčová slova.
    Vrací (je_bezpečný, důvod).
    """
    normalized = sql.upper().strip()

    if not normalized.startswith("SELECT"):
        return False, "Dotaz nezačíná slovem SELECT – zablokováno."

    for keyword in _FORBIDDEN_KEYWORDS:
        # Hledáme celá slova (word boundary) pro SQL klíčová slova,
        # nebo přesný řetězec pro komentáře (-- a /*)
        if keyword in ("--", "/*"):
            if keyword in normalized:
                return False, f"Dotaz obsahuje zakázaný vzor '{keyword}' – zablokováno."
        else:
            pattern = rf"\b{keyword}\b"
            if re.search(pattern, normalized):
                return False, f"Dotaz obsahuje zakázané klíčové slovo '{keyword}' – zablokováno."

    return True, "OK"


# ──────────────────────────────────────────────
# 6. Hlavní smyčka
# ──────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  🤖  Text-to-SQL Agent  (Groq + PostgreSQL)")
    print("=" * 55)
    print("Zadej svůj dotaz v přirozeném jazyce.")
    print("Pro ukončení napiš: exit / quit / konec\n")

    # Načtení DDL jednou na začátku (struktura se nemění často)
    ddl_context = get_schema_ddl(engine)

    while True:
        try:
            user_input = input("🗂️  Zeptej se databáze: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Ukončuji agenta. Nashledanou!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "konec"):
            print("\n👋 Ukončuji agenta. Nashledanou!")
            break

        # Speciální příkaz pro zobrazení struktury
        if user_input.lower() in ("schema", "tabulky", "struktura"):
            print("\n📋 Struktura databáze:")
            print(ddl_context)
            print()
            continue

        # ── Generování SQL ──
        print("\n⏳ Generuji SQL dotaz...")
        try:
            generated_sql = generate_sql(user_input, ddl_context)
        except Exception as e:
            print(f"❌ Chyba při komunikaci s Groq API: {e}\n")
            continue

        print(f"📝 Vygenerovaný SQL:\n   {generated_sql}\n")

        # ── Bezpečnostní kontrola ──
        is_safe, reason = validate_sql(generated_sql)
        if not is_safe:
            print(f"🛑 BEZPEČNOSTNÍ BLOKACE: {reason}\n")
            continue

        # ── Spuštění dotazu ──
        print("⚡ Spouštím dotaz...")
        try:
            df = pd.read_sql(generated_sql, engine)
            if df.empty:
                print("ℹ️  Dotaz nevrátil žádná data.\n")
            else:
                print(f"\n✅ Výsledek ({len(df)} řádků):\n")
                # Nastavení pandas pro hezký výpis
                with pd.option_context(
                    "display.max_rows", 50,
                    "display.max_columns", None,
                    "display.width", None,
                    "display.max_colwidth", 60,
                ):
                    print(df.to_string(index=False))
                print()
        except Exception as e:
            print(f"❌ Chyba při spuštění SQL dotazu: {e}\n")


if __name__ == "__main__":
    main()
