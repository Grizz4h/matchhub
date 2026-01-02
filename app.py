import streamlit as st
from pathlib import Path
import json
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

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
from datetime import datetime


# =====================================
# SETUP
# =====================================

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
OBSERVATIONS_DIR = DATA_DIR / "observations"
LOGO_DIR = DATA_DIR / "teamlogos"

TABLE_CACHE = CACHE_DIR / "del_table.json"
FIXTURES_CACHE = CACHE_DIR / "del_fixtures.json"

# Load team logo mapping
TEAM_LOGO_MAP = {}
try:
    with open(DATA_DIR / "team_map.json", "r", encoding="utf-8") as f:
        TEAM_LOGO_MAP = json.load(f)
except FileNotFoundError:
    pass  # Graceful fallback if mapping doesn't exist yet


# =====================================
# AUTHENTICATION
# =====================================

st.set_page_config(page_title="MatchHub", page_icon="🏒", layout="wide")

# Load auth config
with open(DATA_DIR / "auth.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

try:
    authenticator.login()
except Exception as e:
    st.error(f"Login-Fehler: {e}")
    st.stop()

if st.session_state.get("authentication_status") == False:
    st.error("Username/Password ist falsch")
    st.stop()
elif st.session_state.get("authentication_status") == None:
    st.warning("Bitte Username und Password eingeben")
    st.stop()

# User ist jetzt eingeloggt
name = st.session_state.get("name")
username = st.session_state.get("username")


# =====================================
# HELPER FUNCTIONS
# =====================================

def team_logo(team_name: str, width: int = 60):
    """Display team logo if available. Single source of truth for logos."""
    filename = TEAM_LOGO_MAP.get(team_name)
    if not filename:
        return
    path = LOGO_DIR / filename
    if path.exists():
        st.image(str(path), width=width)


# =====================================
# HELPER FUNCTIONS: Historie
# =====================================

def load_all_submissions(submissions_dir: Path) -> list[dict]:
    """Load all submission JSON files with filename. Keep only latest per user + game."""
    submissions = []
    if not submissions_dir.exists():
        return submissions
    
    # Load all
    all_subs = []
    for file_path in submissions_dir.glob("*.json"):
        try:
            data = load_json(file_path)
            if data:
                data["_filename"] = file_path.name
                all_subs.append(data)
        except Exception:
            continue
    
    # Group by user + game_key, keep latest timestamp
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for sub in all_subs:
        user = sub.get("user", "unknown")
        game = sub.get("game", {})
        game_key = f"{game.get('date', 'unknown')}__{game.get('home', 'unknown')}__{game.get('away', 'unknown')}"
        key = f"{user}__{game_key}"
        grouped[key].append(sub)
    
    # For each group, keep only the latest (by timestamp/submitted_at)
    for key, subs in grouped.items():
        if len(subs) > 1:
            # Sort by timestamp/submitted_at descending
            subs.sort(key=lambda x: x.get("timestamp", x.get("submitted_at", "")), reverse=True)
        submissions.append(subs[0])  # Keep latest
    
    return submissions


def save_observation(observations_dir: Path, observation: dict) -> Path:
    """Save observation to combined JSON file per game+user. Updates specific period."""
    observations_dir.mkdir(exist_ok=True)
    
    user = observation.get("user", "unknown")
    game = observation.get("game", {})
    date = game.get("date", "unknown")
    home = game.get("home", "unknown").replace(" ", "_")
    away = game.get("away", "unknown").replace(" ", "_")
    period = observation.get("period", 1)
    
    # Filename for combined observations
    filename = f"{date}_{home}_vs_{away}_{user}.json"
    filepath = observations_dir / filename
    
    # Load existing data or create new
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            existing_data = {}
    else:
        existing_data = {}
    
    # Update metadata
    existing_data.update({
        "user": user,
        "game": game,
        "focus": observation.get("focus", "CENTER_TRIANGLES"),
        "last_updated": datetime.now().isoformat()
    })
    
    # Update the specific period
    if "periods" not in existing_data:
        existing_data["periods"] = {}
    
    existing_data["periods"][str(period)] = {
        "period": period,
        "timestamp": observation.get("timestamp"),
        "answers": observation.get("answers", {})
    }
    
    # Save back
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def load_all_observations(observations_dir: Path) -> list[dict]:
    """Load all observation JSON files. Each file contains all periods for a game+user."""
    observations = []
    if not observations_dir.exists():
        return observations
    
    # Load all
    all_obs = []
    for file_path in observations_dir.glob("*.json"):
        try:
            data = load_json(file_path)
            if data:
                data["_filename"] = file_path.name
                
                # Check if this is new format (has "periods" key) or old format (has "period" key)
                if "periods" in data:
                    # New format: already has periods as dict, convert to list
                    periods_dict = data.get("periods", {})
                    periods_list = []
                    for period_key, period_data in periods_dict.items():
                        periods_list.append(period_data)
                    
                    # Sort by period
                    periods_list.sort(key=lambda x: x.get("period", 1))
                    
                    data["periods"] = periods_list
                elif "period" in data:
                    # Old format: single period observation, wrap in list
                    single_period = {
                        "period": data.get("period", 1),
                        "timestamp": data.get("timestamp"),
                        "answers": data.get("answers", {})
                    }
                    data["periods"] = [single_period]
                else:
                    # Skip invalid files
                    continue
                
                all_obs.append(data)
        except Exception:
            continue
    
    # Group by user + game_key, collect all periods
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for obs in all_obs:
        user = obs.get("user", "unknown")
        game = obs.get("game", {})
        game_key = f"{game.get('date', 'unknown')}__{game.get('home', 'unknown')}__{game.get('away', 'unknown')}"
        key = f"{user}__{game_key}"
        grouped[key].append(obs)
    
    # For each group, combine all periods
    for key, obs_list in grouped.items():
        # Collect all periods from all observations in this group
        all_periods = []
        for obs in obs_list:
            all_periods.extend(obs.get("periods", []))
        
        # Sort by period and remove duplicates (keep latest timestamp)
        period_map = {}
        for period in all_periods:
            p_num = period.get("period", 1)
            if p_num not in period_map or period.get("timestamp", "") > period_map[p_num].get("timestamp", ""):
                period_map[p_num] = period
        
        combined_periods = list(period_map.values())
        combined_periods.sort(key=lambda x: x.get("period", 1))
        
        # Create combined entry
        if combined_periods:
            combined = {
                "user": obs_list[0].get("user"),
                "game": obs_list[0].get("game"),
                "focus": obs_list[0].get("focus"),
                "periods": combined_periods,
                "timestamp": combined_periods[0].get("timestamp"),  # Use first timestamp
            }
            observations.append(combined)
    
    return observations


def get_game_key(entry: dict, entry_type: str) -> str:
    """Generate game key: YYYY-MM-DD__HOME__AWAY"""
    if entry_type == "Pre-Match":
        game = entry.get("game", {})
        date = game.get("date", "unknown")
        home = game.get("home", "unknown")
        away = game.get("away", "unknown")
    else:  # Beobachtung
        game = entry.get("game", {})
        date = game.get("date", "unknown")
        home = game.get("home", "unknown")
        away = game.get("away", "unknown")
    
    return f"{date}__{home}__{away}"


def format_game_display(game_key: str) -> str:
    """Format game key for display: YYYY-MM-DD · HOME vs AWAY"""
    parts = game_key.split("__")
    if len(parts) == 3:
        date, home, away = parts
        return f"{date} · {home} vs {away}"
    return game_key


def display_pre_match_entry(entry: dict):
    """Display Pre-Match entry in card format."""
    game = entry.get("game", {})
    home = game.get("home", "—")
    away = game.get("away", "—")
    date = game.get("date", "—")
    
    # Header with logos
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        team_logo(home, 80)
    with col2:
        st.markdown(f"### {home} vs {away}")
        st.caption(f"📅 {date}")
    with col3:
        team_logo(away, 80)
    
    st.divider()
    
    # Metrics - use "ratings" field from submissions
    ratings = entry.get("ratings", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("😰 Nervös", ratings.get("nervous", "—"))
    with col2:
        st.metric("💪 Vertrauen", ratings.get("confidence_team", "—"))  # Note: it's confidence_team
    with col3:
        st.metric("🎯 Erwartung", ratings.get("expectation", "—"))
    with col4:
        st.metric("😊 Grundstimmung", ratings.get("mood", "—"))
    
    st.divider()
    
    # Tipp
    tip = entry.get("tip", "—")
    st.markdown("### 🎯 Tipp")
    st.info(tip)
    
    # Notes
    notes = entry.get("notes", {})
    one_liner = notes.get("one_liner", "")
    focus = notes.get("focus_observation", "")
    
    if one_liner or focus:
        st.markdown("### 📝 Notizen")
        with st.container(border=True):
            if one_liner:
                st.markdown(f"**One-Liner:** {one_liner}")
            if focus:
                st.markdown(f"**Fokus:** {focus}")


def display_observation_entry(entry: dict):
    """Display Beobachtung entry in card format. Shows all periods together."""
    game = entry.get("game", {})
    home = game.get("home", "—")
    away = game.get("away", "—")
    date = game.get("date", "—")
    
    # Header with logos
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        team_logo(home, 80)
    with col2:
        st.markdown(f"### {home} vs {away}")
        st.caption(f"📅 {date}")
    with col3:
        team_logo(away, 80)
    
    st.divider()
    
    # Show all periods
    periods = entry.get("periods", [])
    if not periods:
        st.warning("Keine Drittel-Daten gefunden.")
        return
    
    for period_data in periods:
        period = period_data.get("period", 1)
        answers = period_data.get("answers", {})
        
        with st.container(border=True):
            st.markdown(f"### 🏒 Drittel {period}")
            
            # Answers
            center_pos = answers.get("center_position", "—")
            triangles = answers.get("triangle_rating", "—")
            breakout = answers.get("breakout_quality", "—")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Center-Position", center_pos.title())
            with col2:
                st.metric("🔺 Dreiecke", f"{triangles}/5" if triangles != "—" else "—")
            with col3:
                st.metric("⚡ Breakout", breakout.title())
            
            # Note
            note = answers.get("note", "").strip()
            if note:
                st.markdown("**Notiz:**")
                st.caption(note)
            
            # Feedback/Learning task (if available)
            if "feedback" in period_data or "learning_task" in period_data:
                st.divider()
                if "feedback" in period_data:
                    st.markdown("### 🔎 Feedback")
                    st.info(period_data["feedback"])
                if "learning_task" in period_data:
                    st.markdown("### 🎯 Lernauftrag")
                    st.success(period_data["learning_task"])


# =====================================
# HELPER FUNCTIONS: Last Five Analysis
# =====================================

def get_last_five(fixtures: list[dict], team_name: str, max_games: int = 5) -> list[dict]:
    """
    Extract last N finished games for a specific team from fixtures.
    
    Args:
        fixtures: List of all fixtures
        team_name: Full team name (e.g., "ERC Ingolstadt")
        max_games: Maximum number of games to return (default: 5)
    
    Returns:
        List of game dicts with result details, sorted newest first
        
    Note: Currently fixtures don't contain results. This function is prepared
    for when results are added to the fixtures cache, or you can extend
    fetch_fixtures() to scrape results as well.
    """
    import re
    from datetime import datetime
    
    today = datetime.now().date()
    team_games = []
    
    for game in fixtures:
        # Skip games without results
        home = game.get("home", "")
        away = game.get("away", "")
        
        # Check if team is involved
        if team_name not in [home, away]:
            continue
        
        # Check if game is in the past
        try:
            game_date = datetime.strptime(game["date"], "%Y-%m-%d").date()
        except:
            continue
        
        if game_date >= today:
            continue
        
        # Check if result exists (we need a score)
        # NOTE: Current fixtures don't have 'result' field yet
        result_str = game.get("result", "")
        if not result_str or result_str == "-":
            continue
        
        # Parse result (format: "3:2" or "3:2 n.V." or "3:2 n.P.")
        score_match = re.match(r"(\d+):(\d+)", result_str)
        if not score_match:
            continue
        
        home_goals = int(score_match.group(1))
        away_goals = int(score_match.group(2))
        
        # Determine perspective: goals for/against from team's view
        is_home = (home == team_name)
        goals_for = home_goals if is_home else away_goals
        goals_against = away_goals if is_home else home_goals
        opponent = away if is_home else home
        
        # Determine result type
        is_overtime = "n.V." in result_str or "n.P." in result_str
        
        if goals_for > goals_against:
            result = "OTW" if is_overtime else "W"
        elif goals_for < goals_against:
            result = "OTL" if is_overtime else "L"
        else:
            result = "T"  # Shouldn't happen in DEL
        
        team_games.append({
            "date": game["date"],
            "opponent": opponent,
            "home_away": "H" if is_home else "A",
            "goals_for": goals_for,
            "goals_against": goals_against,
            "result": result,
            "score": f"{goals_for}:{goals_against}",
            "matchday": game.get("matchday", "?")
        })
    
    # Sort by date descending (newest first)
    team_games.sort(key=lambda x: x["date"], reverse=True)
    
    return team_games[:max_games]


def get_last_five_from_recent(recent_games_data: dict, max_games: int = 5) -> list[dict]:
    """
    Convert recent games data (from team page scraper) to Last Five format.
    
    This is a bridge function until fixtures contain results.
    """
    if not recent_games_data or "recent_games" not in recent_games_data:
        return []
    
    games = recent_games_data["recent_games"][:max_games]
    result = []
    
    for g in games:
        # Map to expected format
        result.append({
            "date": g.get("date", ""),
            "opponent": "—",  # Not available from current scraper
            "home_away": "—",
            "goals_for": g.get("team_score", 0),
            "goals_against": g.get("opponent_score", 0),
            "result": g.get("result", "?"),
            "score": g.get("score", ""),
            "matchday": g.get("matchday", "?")
        })
    
    return result


def calculate_form_summary(last_five: list[dict]) -> dict:
    """
    Calculate form summary from last five games.
    
    Returns:
        Dict with W, OTW, OTL, L counts and formatted string
    """
    w = sum(1 for g in last_five if g["result"] == "W")
    otw = sum(1 for g in last_five if g["result"] == "OTW")
    otl = sum(1 for g in last_five if g["result"] == "OTL")
    l = sum(1 for g in last_five if g["result"] == "L")
    
    return {
        "W": w,
        "OTW": otw,
        "OTL": otl,
        "L": l,
        "total": len(last_five),
        "formatted": f"{w+otw}–{otl+l}–0"  # Total Wins - Total Losses - OT (simplified)
    }


# =====================================
# UI: TITLE & REFRESH
# =====================================

st.title("🏒 MatchHub – ERC Pre-Match")
st.caption(f"Willkommen, **{name}** 👋")


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
    
    # Logout button
    authenticator.logout(location="sidebar")
    st.caption(f"Eingeloggt als: **{username}**")

# Use username from auth instead of selector
user = username

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

tabs = st.tabs(["Heute", "Pre-Match Check", "Beobachtung", "Historie", "Wiki"])

with tabs[0]:
    # =====================================
    # MATCH HEADER mit Logos & Stats
    # =====================================
    st.subheader("Nächstes Spiel")
    
    # HOME TEAM
    with st.container(border=True):
        col_h_logo, col_h_info = st.columns([1, 3])
        with col_h_logo:
            team_logo(home, width=80)
        with col_h_info:
            st.markdown(f"### {home}")
            if home == ERC_NAME:
                st.caption("🏠 Heimspiel")
            else:
                st.caption("✈️ Auswärts")
            
            # Stats inline
            if erc_row and home == ERC_NAME:
                st.markdown(f"**Platz #{erc_row.get('#', '?')}** · {erc_row.get('P', '?')} Punkte · Tore {erc_row.get('GF', '?')}:{erc_row.get('GA', '?')}")
            elif opp_row and home == opponent:
                st.markdown(f"**Platz #{opp_row.get('#', '?')}** · {opp_row.get('P', '?')} Punkte · Tore {opp_row.get('GF', '?')}:{opp_row.get('GA', '?')}")
    
    # MATCH INFO
    st.markdown(
        f"**📅 {next_game.get('date')}** · "
        f"**⏱ {next_game.get('time') or '—'}** Uhr · "
        f"**🏒 Spieltag {next_game.get('matchday') or '—'}**"
    )
    st.caption("Hauptrunde · DEL 2025/26")
    
    # AWAY TEAM
    with st.container(border=True):
        col_a_logo, col_a_info = st.columns([1, 3])
        with col_a_logo:
            team_logo(away, width=80)
        with col_a_info:
            st.markdown(f"### {away}")
            if away == ERC_NAME:
                st.caption("🏠 Heimspiel")
            else:
                st.caption("✈️ Auswärts")
            
            # Stats inline
            if erc_row and away == ERC_NAME:
                st.markdown(f"**Platz #{erc_row.get('#', '?')}** · {erc_row.get('P', '?')} Punkte · Tore {erc_row.get('GF', '?')}:{erc_row.get('GA', '?')}")
            elif opp_row and away == opponent:
                st.markdown(f"**Platz #{opp_row.get('#', '?')}** · {opp_row.get('P', '?')} Punkte · Tore {opp_row.get('GF', '?')}:{opp_row.get('GA', '?')}")
    
    st.divider()
    
    # =====================================
    # DIREKTER VERGLEICH (kompakt & mobile-friendly)
    # =====================================
    if erc_row and opp_row:
        st.markdown("#### 📊 Direkter Vergleich")
        
        # Kompakte Darstellung als Tabelle
        import pandas as pd
        comparison_data = {
            "Kategorie": ["Platz", "Punkte", "Tore für", "Tore gegen", "Differenz"],
            "ERC": [
                f"#{erc_row.get('#', '?')}",
                erc_row.get('P', '?'),
                erc_row.get('GF', '?'),
                erc_row.get('GA', '?'),
                erc_row.get('GDIFF', '?')
            ],
            opponent: [
                f"#{opp_row.get('#', '?')}",
                opp_row.get('P', '?'),
                opp_row.get('GF', '?'),
                opp_row.get('GA', '?'),
                opp_row.get('GDIFF', '?')
            ]
        }
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # =====================================
    # LAST FIVE / FORMKURVE (aus Recent Games)
    # =====================================
    st.subheader("📊 Last Five – Formkurve")
    st.caption("Letzte 5 Spiele mit Ergebnis. Quelle: Team-Übersichtsseiten.")
    
    # Load recent games data
    erc_short = TEAM_MAPPING.get(ERC_NAME, ERC_NAME.replace(" ", "_"))
    erc_recent_cache = CACHE_DIR / f"recent_{erc_short.lower()}.json"
    erc_recent = read_cache(erc_recent_cache)
    
    opp_short = TEAM_MAPPING.get(opponent, opponent.replace(" ", "_"))
    opp_recent_cache = CACHE_DIR / f"recent_{opp_short.lower()}.json"
    opp_recent = read_cache(opp_recent_cache)
    
    # Get last five for both teams (using bridge function)
    erc_last_five = get_last_five_from_recent(erc_recent.get("data", {}) if erc_recent else {}, max_games=5)
    opp_last_five = get_last_five_from_recent(opp_recent.get("data", {}) if opp_recent else {}, max_games=5)
    
    # Calculate form summaries
    erc_form = calculate_form_summary(erc_last_five)
    opp_form = calculate_form_summary(opp_last_five)
    
    # Form comparison header
    if erc_last_five and opp_last_five:
        st.markdown(
            f"**Form-Vergleich:** "
            f"{ERC_NAME}: `{erc_form['formatted']}` ({erc_form['W']}W-{erc_form['OTW']}OW-{erc_form['OTL']}OL-{erc_form['L']}L) "
            f"| {opponent}: `{opp_form['formatted']}` ({opp_form['W']}W-{opp_form['OTW']}OW-{opp_form['OTL']}OL-{opp_form['L']}L)"
        )
    elif erc_last_five or opp_last_five:
        if erc_last_five:
            st.markdown(f"**{ERC_NAME}:** `{erc_form['formatted']}` ({erc_form['W']}W-{erc_form['OTW']}OW-{erc_form['OTL']}OL-{erc_form['L']}L)")
        if opp_last_five:
            st.markdown(f"**{opponent}:** `{opp_form['formatted']}` ({opp_form['W']}W-{opp_form['OTW']}OW-{opp_form['OTL']}OL-{opp_form['L']}L)")
    
    # Display in two columns
    col_erc, col_opp = st.columns(2)
    
    with col_erc:
        st.markdown(f"**{ERC_NAME}**")
        if not erc_last_five:
            st.info("Noch keine Daten. Klicke auf 'DEL-Daten aktualisieren'")
        else:
            import pandas as pd
            df = pd.DataFrame(erc_last_five)
            # Format for display - adjusted to available columns
            display_df = df[["date", "score", "result"]].copy()
            display_df.columns = ["Datum", "Ergebnis", "Typ"]
            
            # Optional: Add color coding based on result
            def style_result(val):
                if val in ["W", "OTW"]:
                    return "background-color: #d4edda; color: #155724"
                elif val in ["L", "OTL"]:
                    return "background-color: #f8d7da; color: #721c24"
                return ""
            
            st.dataframe(
                display_df.style.applymap(style_result, subset=["Typ"]),
                use_container_width=True,
                hide_index=True,
                height=220
            )
    
    with col_opp:
        st.markdown(f"**{opponent}**")
        if not opp_last_five:
            st.info("Noch keine Daten. Klicke auf 'DEL-Daten aktualisieren'")
        else:
            import pandas as pd
            df = pd.DataFrame(opp_last_five)
            display_df = df[["date", "score", "result"]].copy()
            display_df.columns = ["Datum", "Ergebnis", "Typ"]
            
            def style_result(val):
                if val in ["W", "OTW"]:
                    return "background-color: #d4edda; color: #155724"
                elif val in ["L", "OTL"]:
                    return "background-color: #f8d7da; color: #721c24"
                return ""
            
            st.dataframe(
                display_df.style.applymap(style_result, subset=["Typ"]),
                use_container_width=True,
                hide_index=True,
                height=220
            )
    
    st.divider()
    st.subheader("Cache-Status")
    st.write(f"- Tabelle: **{table_wrap.get('updated_at','?')}**")
    st.write(f"- Spielplan: **{fixtures_wrap.get('updated_at','?')}**")
    
    # Check if recent caches exist
    erc_short = TEAM_MAPPING.get(ERC_NAME, ERC_NAME.replace(" ", "_"))
    erc_recent_cache = CACHE_DIR / f"recent_{erc_short.lower()}.json"
    if erc_recent_cache.exists():
        erc_recent_data = read_cache(erc_recent_cache)
        if erc_recent_data:
            st.write(f"- Recent ERC: **{erc_recent_data.get('updated_at','?')}**")
    
    opp_short = TEAM_MAPPING.get(opponent, opponent.replace(" ", "_"))
    opp_recent_cache = CACHE_DIR / f"recent_{opp_short.lower()}.json"
    if opp_recent_cache.exists():
        opp_recent_data = read_cache(opp_recent_cache)
        if opp_recent_data:
            st.write(f"- Recent {opponent}: **{opp_recent_data.get('updated_at','?')}**")


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
    # =====================================
    # BEOBACHTUNG: Center & Support-Dreiecke
    # =====================================
    st.subheader("🧠 Beobachtung: Center & Support-Dreiecke")
    st.caption(f"Fokus heute: **Center-Position & Dreiecke** • User: **{username}**")
    
    # Game Info (auto)
    st.markdown(f"**{home} vs {away}** • {next_game.get('date')} • Spieltag {next_game.get('matchday')}")
    
    st.divider()
    
    # Period Selection
    period = st.radio("📋 Drittel", [1, 2, 3], horizontal=True, key="obs_period")
    
    st.info("💡 **Drittelpause-Check** – max. 60-90 Sekunden zwischen den Dritteln")
    
    with st.form(f"observation_period_{period}"):
        # =====================================
        # FRAGE A1: Center-Position in der DZ
        # =====================================
        st.markdown("### Frage 1: Center-Position in der DZ")
        center_pos = st.radio(
            "Wo war der Center defensiv meistens positioniert?",
            ["Low – tief vor dem Slot", "Middle – Slot / Hashmarks", "High – oberhalb der Kreise / Richtung Blaue"],
            key=f"center_pos_{period}"
        )
        st.caption("ℹ️ *Der Center ist der Pivot zwischen Slot-Schutz und erstem Outlet-Pass.*")
        
        st.divider()
        
        # =====================================
        # FRAGE A2: Dreiecke & Anspielstationen
        # =====================================
        st.markdown("### Frage 2: Dreiecke & Anspielstationen")
        triangles = st.slider(
            "Wie oft gab es saubere 3er-Anspielstationen (Dreiecke)?",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = fast nie | 3 = phasenweise | 5 = fast immer",
            key=f"triangles_{period}"
        )
        st.caption("ℹ️ *Stabile Dreiecke = weniger Blind Clears, mehr Kontrolle.*")
        
        st.divider()
        
        # =====================================
        # FRAGE A3: Breakout-Qualität
        # =====================================
        st.markdown("### Frage 3: Breakout-Qualität")
        breakout = st.radio(
            "Wie kam ERC meist aus der eigenen Zone?",
            ["Sauber – kontrollierter Aufbau", "Gemischt – mal Kontrolle, mal Chaos", "Chaotisch – Blind Clears, Icing-Gefahr"],
            key=f"breakout_{period}"
        )
        st.caption("ℹ️ *Breakout-Probleme zeigen sich zuerst beim Center-Support.*")
        
        st.divider()
        
        # =====================================
        # OPTIONAL: Notiz (nur für christoph)
        # =====================================
        note = ""
        if username == "christoph":
            st.markdown("### Optional: Kurznotiz")
            note = st.text_input(
                "Wodurch reißen die Dreiecke? (max. 120 Zeichen)",
                max_chars=120,
                key=f"note_{period}"
            )
        
        # Submit
        submitted = st.form_submit_button("✅ Check-in speichern", type="primary")
    
    if submitted:
        # Parse answers
        center_parsed = center_pos.split(" – ")[0].lower()
        breakout_parsed = breakout.split(" – ")[0].lower()
        
        # Build observation object
        observation = {
            "user": username,
            "game": {
                "date": next_game.get("date"),
                "home": home,
                "away": away,
                "matchday": next_game.get("matchday")
            },
            "focus": "CENTER_TRIANGLES",
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "answers": {
                "center_position": center_parsed,
                "triangle_rating": triangles,
                "breakout_quality": breakout_parsed,
                "note": note.strip()
            }
        }
        
        # Save to combined JSON
        from pathlib import Path
        import json
        obs_dir = DATA_DIR / "observations"
        filepath = save_observation(obs_dir, observation)
        
        st.success(f"✅ Drittel {period} gespeichert!")
        
        # =====================================
        # SOFORT-FEEDBACK: Automatische Auswertung
        # =====================================
        st.divider()
        st.markdown("### 🔎 Automatische Auswertung")
        
        # Analyse-Logik
        analysis = []
        learning_task = ""
        
        if center_parsed == "high" and triangles <= 2:
            analysis.append("**ERC verliert Struktur zwischen Slot und Blaue** – Dreiecke reißen früh.")
            learning_task = "Achte darauf, ob der Center früher absinkt, sobald der Gegner Druck aufbaut."
        elif center_parsed == "low" and breakout_parsed == "chaotisch":
            analysis.append("**Center steht zu tief** – fehlende Outlet-Option führt zu Blind Clears.")
            learning_task = "Beobachte, ob der Center rechtzeitig nach oben kommt, um den ersten Pass anzubieten."
        elif triangles >= 4 and breakout_parsed == "sauber":
            analysis.append("**Starke Struktur!** Dreiecke stabil, Breakouts kontrolliert.")
            learning_task = "Achte darauf, wie lange diese Struktur unter Druck hält."
        elif breakout_parsed == "gemischt":
            analysis.append("**Inkonsistenz** – mal funktioniert's, mal nicht.")
            learning_task = "Versuche zu erkennen, wann die Dreiecke zusammenbrechen (Forechecking-Druck? Tempo?)."
        else:
            analysis.append("**Solide Basisarbeit** – Center und Dreiecke arbeiten zusammen.")
            learning_task = "Beobachte, wie sich das unter zunehmendem Druck entwickelt."
        
        # Display
        for a in analysis:
            st.markdown(a)
        
        st.divider()
        st.markdown("### 🎯 Lernauftrag für nächstes Drittel")
        st.info(learning_task)


with tabs[3]:
    # =====================================
    # HISTORIE: Schöne Ansicht statt JSON-Dump
    # =====================================
    st.subheader("📚 Historie")
    st.caption("Einträge durchsuchen und anzeigen lassen.")
    
    # Load data
    submissions = load_all_submissions(SUBMISSIONS_DIR)
    observations = load_all_observations(DATA_DIR / "observations")
    
    if not submissions and not observations:
        st.info("Noch keine Einträge vorhanden.")
        st.stop()
    
    # Build game options
    # Use a composite key (type + game_key) so Pre-Match and Beobachtung for
    # dasselbe Spiel nicht kollidieren. Vorher wurde Beobachtung vom gleichen
    # Spiel durch das Pre-Match-Entry überschrieben und tauchte im Dropdown
    # nicht auf.
    game_options = {}

    # Add Pre-Match games
    for sub in submissions:
        game_key = get_game_key(sub, "Pre-Match")
        composite_key = f"Pre-Match__{game_key}"
        if composite_key not in game_options:
            game_options[composite_key] = {"type": "Pre-Match", "game_key": game_key, "entries": []}
        game_options[composite_key]["entries"].append(sub)

    # Add Beobachtung games (now each entry contains all periods)
    for obs in observations:
        game_key = get_game_key(obs, "Beobachtung")
        composite_key = f"Beobachtung__{game_key}"
        if composite_key not in game_options:
            game_options[composite_key] = {"type": "Beobachtung", "game_key": game_key, "entries": []}
        game_options[composite_key]["entries"].append(obs)
    
    # Dropdowns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        user_options = ["alle", "martin", "christoph"]
        select_user = st.selectbox("👤 User", user_options, index=0)
    
    with col2:
        type_options = ["Pre-Match", "Beobachtung"]
        select_type = st.selectbox("📋 Typ", type_options, index=0)
    
    with col3:
        # Filter games by type
        available_games = [k for k, v in game_options.items() if v["type"] == select_type]
        if not available_games:
            st.warning(f"Keine {select_type} Einträge gefunden.")
            st.stop()
        
        game_display_options = [format_game_display(game_options[k]["game_key"]) for k in available_games]
        select_game_idx = st.selectbox("🏒 Spiel", range(len(game_display_options)), format_func=lambda i: game_display_options[i])
        selected_game_key = available_games[select_game_idx]
    
    # Get entries for selected game
    game_data = game_options[selected_game_key]
    entries = game_data["entries"]
    
    # Filter by user if not "alle"
    if select_user != "alle":
        entries = [e for e in entries if e.get("user") == select_user]
    
    if not entries:
        st.warning(f"Keine Einträge für {select_user} in diesem Spiel gefunden.")
        st.stop()
    
    # Since we keep only latest per user+game+type, there should be only one entry
    selected_entry = entries[0]
    
    st.divider()
    
    # Display the entry beautifully
    if select_type == "Pre-Match":
        display_pre_match_entry(selected_entry)
    else:
        display_observation_entry(selected_entry)


with tabs[4]:
    # =====================================
    # WIKI: Taktik-Glossar
    # =====================================
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