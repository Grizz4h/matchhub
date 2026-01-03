"""Generic UI helper functions for Academy pages."""
import streamlit as st


def render_game_header(game: dict, logo_callback=None):
    """Render game header with logos if available."""
    home = game.get("home", "")
    away = game.get("away", "")
    date = game.get("date", "")
    league = game.get("league", "DEL")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if logo_callback:
            logo_callback(home)
        st.markdown(f"**{home}**")
    
    with col2:
        st.markdown(f"<h3 style='text-align: center;'>vs</h3>", unsafe_allow_html=True)
        st.caption(f"{date} · {league}")
    
    with col3:
        if logo_callback:
            logo_callback(away)
        st.markdown(f"**{away}**")


def render_module_card(track_id: str, track_title: str, module: dict, expanded: bool = False):
    """Render a module card with expandable details."""
    module_id = module["id"]
    module_title = module["title"]
    module_summary = module.get("summary", "")
    drill_count = len(module.get("drills", []))
    
    with st.expander(f"**{module_id}** – {module_title}", expanded=expanded):
        st.caption(f"Track {track_id}: {track_title}")
        st.markdown(module_summary)
        
        if drill_count > 0:
            st.success(f"✅ {drill_count} Drill(s) verfügbar")
            for drill in module.get("drills", []):
                st.markdown(f"- **{drill['id']}**: {drill['title']} ({drill['drill_type']})")
            
            # Store module for easy access
            if st.button(f"📋 {module_id} vormerken", key=f"select_{module_id}", use_container_width=True):
                st.session_state["selected_module_id"] = module_id
                st.info(f"✅ **{module_id}** vorgemerkt! Gehe jetzt zu **Session Trainer** in der Sidebar.")
        else:
            st.warning("Noch keine Drills verfügbar.")


def render_phase_badge(phase: str) -> str:
    """Render a phase badge with color."""
    badges = {
        "PRE": "🔵",
        "P1": "1️⃣",
        "P2": "2️⃣",
        "P3": "3️⃣",
        "POST": "✅"
    }
    return badges.get(phase, "❓") + " " + phase


def render_confidence_metric(confidence: int):
    """Render confidence as metric."""
    emoji = "🟢" if confidence >= 4 else "🟡" if confidence >= 3 else "🔴"
    st.metric("Confidence", f"{confidence}/5 {emoji}")


def render_helpfulness_metric(helpfulness: int):
    """Render helpfulness as metric."""
    emoji = "⭐" * helpfulness
    st.metric("Helpfulness", emoji)
