"""History page: View completed sessions beautifully."""
import streamlit as st
from pathlib import Path
from academy.curriculum import load_curriculum
from academy.sessions import list_sessions
from academy.renderers import (
    render_game_header, render_phase_badge,
    render_confidence_metric, render_helpfulness_metric
)


def render_history_page(
    curriculum_path: Path,
    sessions_dir: Path,
    username: str,
    team_logo_callback=None
):
    """Render the history page with beautiful session display."""
    st.header("📜 Academy Historie")
    st.caption("Vergangene Sessions durchsuchen")
    
    curriculum = load_curriculum(curriculum_path)
    all_sessions = list_sessions(sessions_dir)
    
    if not all_sessions:
        st.info("Noch keine Sessions vorhanden.")
        return
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        users = list(set(s.get("user", "unknown") for s in all_sessions))
        select_user = st.selectbox("User", ["alle"] + sorted(users))
    
    with col2:
        modules = list(set(s.get("module_id", "") for s in all_sessions if s.get("module_id")))
        select_module = st.selectbox("Modul", ["alle"] + sorted(modules))
    
    with col3:
        states = list(set(s.get("state", "") for s in all_sessions))
        select_state = st.selectbox("Status", ["alle"] + sorted(states))
    
    # Apply filters
    filtered_sessions = all_sessions
    if select_user != "alle":
        filtered_sessions = [s for s in filtered_sessions if s.get("user") == select_user]
    if select_module != "alle":
        filtered_sessions = [s for s in filtered_sessions if s.get("module_id") == select_module]
    if select_state != "alle":
        filtered_sessions = [s for s in filtered_sessions if s.get("state") == select_state]
    
    st.caption(f"{len(filtered_sessions)} Session(s) gefunden")
    
    if not filtered_sessions:
        st.warning("Keine Sessions mit diesen Filtern gefunden.")
        return
    
    st.divider()
    
    # Display sessions
    for session in filtered_sessions:
        render_session_detail(session, curriculum, team_logo_callback)
        st.divider()


def render_session_detail(session: dict, curriculum: dict, team_logo_callback=None):
    """Render a single session in detail."""
    game = session.get("game", {})
    module_id = session.get("module_id", "")
    drill_id = session.get("drill_id", "")
    user = session.get("user", "unknown")
    state = session.get("state", "unknown")
    
    # Container with border - use expander to show/hide details
    session_title = f"{game.get('date', 'Unbekannt')} | {game.get('home', '')} vs {game.get('away', '')} | {module_id}"
    
    with st.expander(f"🎯 {session_title}", expanded=False):
        # Header
        render_game_header(game, team_logo_callback)
        
        st.markdown(f"**User:** {user} | **Modul:** {module_id} | **Drill:** {drill_id} | **Status:** {state}")
        
        st.divider()
        
        # PRE data
        pre = session.get("pre", {})
        if pre:
            with st.expander("🔵 PRE – Vorbereitung", expanded=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    goal = pre.get("goal", "")
                    st.markdown(f"**Ziel:** {goal if goal else '_(kein Ziel gesetzt)_'}")
                    timestamp = pre.get("timestamp", "")
                    if timestamp:
                        st.caption(f"📅 {timestamp}")
                with col2:
                    confidence = pre.get("confidence", 3)
                    render_confidence_metric(confidence)
        
        # Check-ins
        checkins = session.get("checkins", [])
        if checkins:
            for checkin in checkins:
                phase = checkin.get("phase", "")
                answers = checkin.get("answers", {})
                feedback = checkin.get("feedback", "")
                next_task = checkin.get("next_task", "")
                timestamp = checkin.get("timestamp", "")
                
                with st.expander(f"{render_phase_badge(phase)} Check-in", expanded=True):
                    # Show answers - better formatting
                    if answers:
                        st.markdown("**📝 Deine Antworten:**")
                        for key, value in answers.items():
                            # Format key nicely
                            display_key = key.replace("_", " ").title()
                            st.markdown(f"- **{display_key}:** {value}")
                    else:
                        st.markdown("_(keine Antworten erfasst)_")
                    
                    if timestamp:
                        st.caption(f"📅 {timestamp}")
                    
                    st.divider()
                    
                    # Show feedback
                    if feedback:
                        st.markdown("**💬 Coaching Feedback:**")
                        st.info(feedback)
                    
                    # Show next task
                    if next_task:
                        st.markdown("**🎯 Next Task:**")
                        st.warning(next_task)
        
        # POST data
        post = session.get("post", {})
        if post:
            with st.expander("✅ POST – Session Abschluss", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    summary = post.get("summary", "")
                    st.markdown(f"**📝 Zusammenfassung:** {summary if summary else '_(keine Angabe)_'}")
                    
                    unclear = post.get("unclear", "")
                    st.markdown(f"**❓ Offene Fragen:** {unclear if unclear else '_(keine Angabe)_'}")
                    
                    next_module = post.get("next_module", "")
                    if next_module:
                        st.markdown(f"**➡️ Nächstes Modul:** {next_module}")
                    
                    timestamp = post.get("timestamp", "")
                    if timestamp:
                        st.caption(f"📅 Abgeschlossen: {timestamp}")
                
                with col2:
                    helpfulness = post.get("helpfulness", 3)
                    render_helpfulness_metric(helpfulness)
