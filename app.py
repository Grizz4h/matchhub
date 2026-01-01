import os
import sqlite3
import streamlit as st

DB_PATH = os.getenv("MATCHHUB_DB_PATH", "data/matchhub.db")

st.set_page_config(page_title="MatchHub", page_icon="🏒", layout="centered")
st.title("🏒 MatchHub")
st.caption("Pre-Match Hub (DEL) – Stats + Mood + Lern-Impulse")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Minimal-Tabellen, damit nichts crasht
cur.execute("""
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS martin_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  context_id TEXT,
  submitted_at TEXT,
  nervousness INTEGER,
  expectation TEXT,
  mood INTEGER,
  importance INTEGER,
  focus TEXT,
  one_liner TEXT
)
""")
conn.commit()

st.success("App läuft. Nächster Schritt: Collector + Match-Overview + Stats.")

with st.expander("Debug", expanded=False):
    st.write("DB Path:", DB_PATH)
    st.write("Tables:")
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    st.write([t[0] for t in tables])

conn.close()
