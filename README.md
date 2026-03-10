# 🤖 AI Data Copilot – Text-to-SQL Agent

Bezpečný AI agent, který přeloží tvůj dotaz v přirozeném jazyce do SQL,
spustí ho v lokální PostgreSQL databázi a vrátí výsledek jako interaktivní tabulku.

Využívá **Groq API** (LLaMA model) pro generování SQL a **Streamlit** pro webové rozhraní.

## Jak to funguje

```
Tvůj dotaz (česky) → Groq AI → SQL dotaz → Bezpečnostní kontrola → PostgreSQL → Tabulka
```

## Požadavky

- **Python 3.10+**
- **PostgreSQL** (běžící lokálně)
- **Groq API klíč** ([získej zde](https://console.groq.com))

## Instalace

```bash
# 1. Klonuj repozitář
git clone <url-repozitáře>
cd Space

# 2. Vytvoř virtuální prostředí
python3 -m venv .venv
source .venv/bin/activate

# 3. Nainstaluj závislosti
pip install -r requirements.txt

# 4. Nastav přihlašovací údaje
cp .env.example .env
# Otevři .env a doplň svůj GROQ_API_KEY a heslo k PostgreSQL
```

## Spuštění

### 🖥️ Webové rozhraní (Streamlit)

```bash
source .venv/bin/activate
streamlit run cli.py
```

Otevře se prohlížeč na `http://localhost:8501` s interaktivním UI.

### ⌨️ Terminálový agent

```bash
source .venv/bin/activate
python agent.py
```

Klasický CLI s `while True` smyčkou. Příkazy: `schema`, `exit`, `konec`.

## Struktura projektu

```
Space/
├── cli.py              # Streamlit webové rozhraní
├── agent.py            # Terminálový CLI agent
├── config.py           # Načtení .env + kontrola proměnných
├── database.py         # SQLAlchemy engine + get_schema_ddl()
├── security.py         # SQL guardrails (validate_sql)
├── llm.py              # Groq klient + generate_sql()
├── requirements.txt    # Závislosti (pip install -r)
├── .env                # Přihlašovací údaje (NIKDY necommitovat!)
├── .env.example        # Šablona pro nové vývojáře
├── .gitignore          # Ochrana citlivých souborů
├── LICENSE             # MIT licence
└── .venv/              # Virtuální prostředí (ignorováno gitem)
```

## Bezpečnost

- 🔒 Přihlašovací údaje se **nikdy netisknou** ani nelogují
- 🛡️ Každý SQL dotaz prochází **validací guardrails** před spuštěním
- ✅ Povoleny **pouze SELECT** dotazy
- 🚫 Blokované příkazy: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `CREATE`
- 📁 `.gitignore` chrání `.env` a `.venv` před nahráním na GitHub

## Licence

MIT License – viz [LICENSE](LICENSE).
