"""
llm.py – Integrace s Groq API (LLaMA)
=======================================
Inicializace Groq klienta a funkce pro generování SQL
z přirozeného jazyka pomocí LLM.
"""

import re
from groq import Groq
from config import GROQ_API_KEY


# ── Groq klient ──
_client = Groq(api_key=GROQ_API_KEY)


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

    response = _client.chat.completions.create(
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
