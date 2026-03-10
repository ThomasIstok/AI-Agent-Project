"""
security.py – Bezpečnostní guardrails
=======================================
Validace SQL dotazů před spuštěním v databázi.
Povoleny pouze SELECT dotazy, zakázány destruktivní příkazy.
"""

import re


# ── Zakázaná klíčová slova ──
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
