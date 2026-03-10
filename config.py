"""
config.py – Bezpečné načtení přihlašovacích údajů
===================================================
Načte .env soubor a exportuje konfigurační proměnné.
Hesla se nikdy netisknou ani nelogují.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Přihlašovací údaje (pouze v RAM) ──
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Kontrola, že nic nechybí ──
_required = {
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_NAME": DB_NAME,
    "GROQ_API_KEY": GROQ_API_KEY,
}

_missing = [k for k, v in _required.items() if not v]
if _missing:
    print(f"❌ Chybí povinné proměnné v .env: {', '.join(_missing)}")
    sys.exit(1)
