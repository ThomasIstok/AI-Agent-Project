"""
app.py – Streamlit frontend pro Text-to-SQL Agent
===================================================
Webové rozhraní nahrazující terminálový while cyklus.
Spuštění: streamlit run app.py
"""

import streamlit as st
import pandas as pd

from database import engine, test_connection, get_schema_ddl
from llm import generate_sql
from security import validate_sql


# ──────────────────────────────────────────────
# Konfigurace stránky
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="AI Data Copilot",
    page_icon="🤖",
    layout="wide",
)

# Custom CSS pro premium vzhled
st.markdown("""
<style>
    /* Hlavní nadpis */
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .subtitle {
        color: #888;
        font-size: 1.1rem;
        margin-top: -10px;
    }
    /* Metriky */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 15px;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%);
    }
    /* SQL blok */
    .sql-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Sidebar – stav připojení a schéma
# ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Stav systému")

    # Test DB připojení
    db_ok = test_connection()
    if db_ok:
        st.success("🐘 PostgreSQL – připojeno")
    else:
        st.error("🐘 PostgreSQL – nelze se připojit")

    st.success("🤖 Groq API – nakonfigurováno")

    st.divider()

    # Zobrazení schématu
    st.markdown("## 📋 Schéma databáze")
    if db_ok:
        with st.expander("Zobrazit strukturu tabulek", expanded=False):
            ddl = get_schema_ddl()
            st.code(ddl, language="sql")
    else:
        st.warning("Schéma nelze načíst – DB není dostupná.")

    st.divider()
    st.caption("🔒 Povoleny pouze SELECT dotazy")
    st.caption("🛡️ SQL guardrails aktivní")


# ──────────────────────────────────────────────
# Hlavní oblast
# ──────────────────────────────────────────────

st.markdown('<p class="main-title">🤖 AI Data Copilot</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Zeptej se databáze v přirozeném jazyce – AI přeloží do SQL a vrátí výsledky.</p>', unsafe_allow_html=True)

st.markdown("")  # spacing

# ── Vstupní pole ──
user_query = st.text_input(
    "💬 Tvůj dotaz:",
    placeholder="Např.: Ukaž mi top 5 nejdražších produktů...",
    label_visibility="visible",
)

# ── Tlačítko pro odeslání ──
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    run_button = st.button("🚀 Spustit dotaz", type="primary", use_container_width=True)
with col2:
    show_schema = st.button("📋 Schéma", use_container_width=True)

# ── Zobrazení schématu v hlavní oblasti ──
if show_schema:
    if db_ok:
        st.code(get_schema_ddl(), language="sql")
    else:
        st.error("Databáze není dostupná.")

# ── Zpracování dotazu ──
if run_button and user_query:

    if not db_ok:
        st.error("❌ Nelze se připojit k databázi. Zkontroluj PostgreSQL a .env soubor.")
        st.stop()

    # Načtení DDL pro kontext
    ddl_context = get_schema_ddl()

    # 1. Generování SQL
    with st.spinner("⏳ Generuji SQL dotaz z tvého textu..."):
        try:
            generated_sql = generate_sql(user_query, ddl_context)
        except Exception as e:
            st.error(f"❌ Chyba při komunikaci s Groq API: {e}")
            st.stop()

    # 2. Zobrazení vygenerovaného SQL
    st.markdown("### 📝 Vygenerovaný SQL")
    st.code(generated_sql, language="sql")

    # 3. Bezpečnostní validace
    is_safe, reason = validate_sql(generated_sql)

    if not is_safe:
        st.error(f"🛑 **BEZPEČNOSTNÍ BLOKACE:** {reason}")
        st.warning("Dotaz nebyl spuštěn. Zkus jinak formulovat svůj požadavek.")
        st.stop()

    st.success("✅ Bezpečnostní kontrola prošla")

    # 4. Spuštění dotazu
    with st.spinner("⚡ Spouštím dotaz v databázi..."):
        try:
            df = pd.read_sql(generated_sql, engine)
        except Exception as e:
            st.error(f"❌ Chyba při spuštění SQL dotazu: {e}")
            st.stop()

    # 5. Zobrazení výsledků
    if df.empty:
        st.info("ℹ️ Dotaz nevrátil žádná data.")
    else:
        st.markdown(f"### ✅ Výsledek ({len(df)} řádků)")

        # Metriky
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("📊 Řádků", len(df))
        col_b.metric("📋 Sloupců", len(df.columns))
        col_c.metric("📐 Celkem buněk", len(df) * len(df.columns))

        # Interaktivní tabulka
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Stažení jako CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Stáhnout jako CSV",
            data=csv,
            file_name="vysledek.csv",
            mime="text/csv",
        )

elif run_button and not user_query:
    st.warning("⚠️ Zadej prosím dotaz do textového pole.")
