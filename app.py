import streamlit as st
from pathlib import Path

from del_fetch import (
    fetch_table,
    fetch_fixtures,
    fetch_team_recent_games,
    read_cache,
    pick_next_erc_game,
    find_team_row,
    ERC_NAME,
    TEAM_MAPPING,
)
from storage import save_submission, list_submissions, load_json

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
SUBMISSIONS_DIR = DATA_DIR / "submissions"

TABLE_CACHE = CACHE_DIR / "del_table.json"
FIXTURES_CACHE = CACHE_DIR / "del_fixtures.json"

st.set_page_config(page_title="MatchHub", page_icon="🏒", layout="wide")
st.title("🏒 MatchHub – ERC Pre-Match")
st.caption("DEL Daten: Tabelle + Spielplan (on-demand Cache). Pre-Match-Inputs werden als JSON gespeichert.")


def refresh():
    with st.spinner("Hole DEL-Daten (Tabelle + Spielplan + Recent Games)…"):
        fetch_table(CACHE_DIR)
        fetch_fixtures(CACHE_DIR)
        
        # Fetch recent games for ERC
        try:
            fetch_team_recent_games(CACHE_DIR, ERC_NAME)
        except Exception as e:
            st.warning(f"Konnte Recent Games für ERC nicht laden: {e}")
        
        # Get opponent and fetch their recent games too
        fixtures_wrap = read_cache(FIXTURES_CACHE)
        if fixtures_wrap:
            next_game = pick_next_erc_game(fixtures_wrap["data"])
            if next_game:
                home = next_game["home"]
                away = next_game["away"]
                opponent = away if home == ERC_NAME else home
                try:
                    fetch_team_recent_games(CACHE_DIR, opponent)
                except Exception as e:
                    st.warning(f"Konnte Recent Games für {opponent} nicht laden: {e}")
    
    st.success("Cache aktualisiert.")


with st.sidebar:
    st.subheader("Admin")
    st.button("DEL-Daten aktualisieren", on_click=refresh)
    st.caption("Kein Cron. Nur per Button.")

    st.divider()
    st.subheader("User")
    user = st.selectbox("Wer füllt aus?", ["martin", "christoph"], index=0)

table_wrap = read_cache(TABLE_CACHE)
fixtures_wrap = read_cache(FIXTURES_CACHE)

if not table_wrap or not fixtures_wrap:
    st.warning("Cache ist leer. Links im Sidebar auf **DEL-Daten aktualisieren** klicken.")
    st.stop()

table = table_wrap["data"]
fixtures = fixtures_wrap["data"]

next_game = pick_next_erc_game(fixtures)
if not next_game:
    st.error("Kein nächstes ERC-Spiel im Spielplan gefunden (oder Parser greift nicht).")
    st.stop()

home = next_game["home"]
away = next_game["away"]
opponent = away if home == ERC_NAME else home

erc_row = find_team_row(table, ERC_NAME)
opp_row = find_team_row(table, opponent)

tabs = st.tabs(["Heute", "Pre-Match Check", "Historie", "Wiki"])

with tabs[0]:
    colA, colB = st.columns([2, 1], gap="large")

    with colA:
        st.subheader("Nächstes Spiel")
        st.markdown(
            f"**{home}** vs **{away}**\n\n"
            f"📅 **{next_game.get('date')}**  ⏱ **{next_game.get('time') or '—'}**  · Spieltag: **{next_game.get('matchday') or '—'}**"
        )
        st.caption("Das ist der Anker für Formular und alles weitere.")

    with colB:
        st.subheader("Tabelle – ERC vs Gegner")
        rows = []
        if erc_row:
            rows.append(erc_row)
        else:
            st.warning("ERC nicht in Tabelle gefunden (Teamname-Mismatch).")
        if opp_row:
            rows.append(opp_row)
        else:
            st.warning(f"Gegner nicht in Tabelle gefunden: {opponent} (Teamname-Mismatch).")

        if rows:
            import pandas as pd
            df = pd.DataFrame(rows)
            # Zeige relevante Spalten für bessere Übersicht
            display_cols = ["#", "Team", "GP", "W", "L", "P", "P/GP", "GF", "GA", "GDIFF"]
            available_cols = [col for col in display_cols if col in df.columns]
            if available_cols:
                df_display = df[available_cols]
            else:
                df_display = df
            st.dataframe(df_display, use_container_width=True, height=160, hide_index=True)
    
    st.divider()
    
    # Last Five / Recent Form
    st.subheader("🔥 Form & Letzte Spiele")
    st.caption("Basis: Letzte 10 Spiele (angezeigt: Top 5)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**{ERC_NAME}**")
        erc_short = TEAM_MAPPING.get(ERC_NAME, ERC_NAME.replace(" ", "_"))
        erc_recent_cache = CACHE_DIR / f"recent_{erc_short.lower()}.json"
        erc_recent = read_cache(erc_recent_cache)
        
        if erc_recent:
            data = erc_recent["data"]
            st.metric("Form (W-L)", data.get("last_10_form", "—"))
            
            # Show recent games
            if data.get("recent_games"):
                recent_df = pd.DataFrame(data["recent_games"][:5])  # Top 5
                if not recent_df.empty:
                    display_df = recent_df[["date", "score", "result"]].copy()
                    display_df.columns = ["Datum", "Ergebnis", "W/L"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("Noch keine Daten. Klicke auf 'DEL-Daten aktualisieren'")
    
    with col2:
        st.markdown(f"**{opponent}**")
        opp_short = TEAM_MAPPING.get(opponent, opponent.replace(" ", "_"))
        opp_recent_cache = CACHE_DIR / f"recent_{opp_short.lower()}.json"
        opp_recent = read_cache(opp_recent_cache)
        
        if opp_recent:
            data = opp_recent["data"]
            st.metric("Form (W-L)", data.get("last_10_form", "—"))
            
            # Show recent games
            if data.get("recent_games"):
                recent_df = pd.DataFrame(data["recent_games"][:5])  # Top 5
                if not recent_df.empty:
                    display_df = recent_df[["date", "score", "result"]].copy()
                    display_df.columns = ["Datum", "Ergebnis", "W/L"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("Noch keine Daten. Klicke auf 'DEL-Daten aktualisieren'")

    st.divider()
    st.subheader("Cache-Status")
    st.write(f"- Tabelle: **{table_wrap.get('updated_at','?')}**")
    st.write(f"- Spielplan: **{fixtures_wrap.get('updated_at','?')}**")
    if erc_recent:
        st.write(f"- Recent ERC: **{erc_recent.get('updated_at','?')}**")
    if opp_recent:
        st.write(f"- Recent {opponent}: **{opp_recent.get('updated_at','?')}**")


with tabs[1]:
    st.subheader("Pre-Match Check")
    st.caption("Skala 1–6. 1 = low, 6 = high. Kurz halten, damit er's macht.")

    # Boomer / Nerd Mode Toggle
    mode = st.toggle("Erweiterter Modus (Taktik & Analyse)", value=False)
    mode_value = "nerd" if mode else "simple"

    # Load wiki for inline hints
    wiki_path = DATA_DIR / "wiki_terms.json"
    wiki_data = load_json(wiki_path) if wiki_path.exists() else {}

    with st.form("prematch"):
        # 1. Pre-Match Mood
        with st.container(border=True):
            st.markdown("#### 📊 Pre-Match Mood")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                nervous = st.slider("Nervös?", 1, 6, 3)
            with c2:
                confidence = st.slider("Vertrauen ins Team?", 1, 6, 4)
            with c3:
                expectation = st.slider("Erwartung (wie gut wird's)?", 1, 6, 4)
            with c4:
                mood = st.slider("Grundstimmung?", 1, 6, 4)

        # 2. Tipp & Erwartung
        with st.container(border=True):
            st.markdown("#### 🎯 Tipp & Erwartung")
            tip = st.radio("Tipp", ["ERC Sieg (reg.)", "ERC Sieg (OT/SO)", "ERC verliert (OT/SO)", "ERC verliert (reg.)"], horizontal=False)

        # 3. Beobachtungs-Fokus (nur Nerd-Modus)
        focus_tags = []
        if mode:
            with st.container(border=True):
                st.markdown("#### 🔍 Beobachtungs-Fokus")
                # Lade Optionen dynamisch aus Wiki
                focus_options = sorted(wiki_data.keys()) if wiki_data else []
                if not focus_options:
                    st.info("Wiki-Begriffe noch nicht verfügbar. Erstelle data/wiki_terms.json")
                else:
                    focus_tags = st.multiselect(
                        "Worauf achtest du heute?",
                        focus_options
                    )
                
                # Show wiki hints for selected tags
                if focus_tags and wiki_data:
                    st.caption("💡 Wiki-Hinweise zu deinen Fokus-Punkten:")
                    for tag in focus_tags:
                        if tag in wiki_data:
                            term = wiki_data[tag]
                            with st.expander(f"📖 {tag}", expanded=False):
                                st.write(term.get("short", ""))

        # 4. Notizen
        with st.container(border=True):
            st.markdown("#### 📝 Notizen")
            one_liner = st.text_input("One-Liner (optional)", placeholder="z.B. Heute wird's eng, aber machbar.")
            
            if mode:
                focus_obs = st.text_input("Beobachtung heute (optional)", placeholder="z.B. Center: middle support / Dreiecke reißen auf")
            else:
                focus_obs = ""

        submitted = st.form_submit_button("Absenden", type="primary")

    if submitted:
        payload = {
            "user": user,
            "season": "2025-26",
            "mode": mode_value,
            "game": {
                "date": next_game.get("date"),
                "time": next_game.get("time"),
                "matchday": next_game.get("matchday"),
                "home": home,
                "away": away,
                "erc": ERC_NAME,
            },
            "ratings": {
                "nervous": nervous,
                "confidence_team": confidence,
                "expectation": expectation,
                "mood": mood,
            },
            "tip": tip,
            "focus_tags": focus_tags,
            "notes": {
                "one_liner": one_liner.strip(),
                "focus_observation": focus_obs.strip(),
            },
        }
        path = save_submission(SUBMISSIONS_DIR, payload)
        st.success(f"Gespeichert: {path.name}")


with tabs[2]:
    st.subheader("Historie")
    files = list_submissions(SUBMISSIONS_DIR)
    if not files:
        st.info("Noch keine Einträge. Erst im Tab **Pre-Match Check** absenden.")
    else:
        pick = st.selectbox("Eintrag auswählen", [p.name for p in files], index=0)
        data = load_json(SUBMISSIONS_DIR / pick)
        st.json(data)


with tabs[3]:
    st.subheader("📚 Taktik-Wiki")
    st.caption("Begriffe und Konzepte aus dem Taktik-Seminar. Kompakt und durchsuchbar.")
    
    wiki_path = DATA_DIR / "wiki_terms.json"
    
    if not wiki_path.exists():
        st.warning("Wiki noch nicht angelegt. Erstelle `data/wiki_terms.json`")
    else:
        wiki_data = load_json(wiki_path)
        
        if not wiki_data:
            st.info("Wiki ist leer.")
        else:
            # Search field
            search = st.text_input("🔍 Begriff suchen", placeholder="z.B. Dreieck, Center, Forecheck...")
            
            # Filter terms
            terms = wiki_data.keys()
            if search:
                terms = [t for t in terms if search.lower() in t.lower()]
            else:
                terms = list(terms)
            
            if not terms:
                st.info("Keine Treffer.")
            else:
                st.caption(f"{len(terms)} Begriff(e) gefunden")
                
                # Display terms
                for term_name in sorted(terms):
                    term = wiki_data[term_name]
                    with st.expander(f"📖 {term_name}", expanded=False):
                        st.markdown(f"**{term.get('short', '')}**")
                        
                        if "details" in term:
                            st.markdown(term["details"])
                        
                        if "watch" in term and term["watch"]:
                            st.markdown("**Worauf achten:**")
                            for item in term["watch"]:
                                st.markdown(f"- {item}")