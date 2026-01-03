"""Session Trainer page: Create and run training sessions."""
import streamlit as st
from pathlib import Path
from datetime import datetime
from academy.curriculum import load_curriculum, list_modules, list_drills_for_module, get_drill
from academy.sessions import (
    create_session, load_session, save_session, get_active_session,
    add_checkin, complete_session
)
from academy.drill_engine import render_drill
from academy.renderers import render_game_header, render_phase_badge, render_confidence_metric

# Import drill renderers to register them
from academy.drills import period_checkin, micro_quiz


def render_session_trainer_page(
    curriculum_path: Path,
    sessions_dir: Path,
    user: str,
    username: str,
    team_logo_callback=None,
    team_list=None
):
    """Render the session trainer page."""
    st.header("🎯 Session Trainer")
    st.caption("Lern-Sessions mit Live-Game-Kontext")
    
    curriculum = load_curriculum(curriculum_path)

    # If POST just finished, force showing setup
    if st.session_state.get("force_new_session"):
        st.session_state.pop("force_new_session", None)
        render_session_setup(curriculum, sessions_dir, user, username, team_list)
        return

    # IMPORTANT: Always reload fresh from disk, never cache
    if hasattr(st.session_state, "_active_session_cache"):
        delattr(st.session_state, "_active_session_cache")

    active_session = get_active_session(sessions_dir, username)

    # Reload from disk to be 100% sure state is active
    if active_session:
        fresh = load_session(sessions_dir, active_session["session_id"])
        if not fresh or fresh.get("state") != "active":
            active_session = None
        else:
            active_session = fresh

    if active_session:
        render_active_session(active_session, curriculum, sessions_dir, user, username, team_logo_callback)
    else:
        render_session_setup(curriculum, sessions_dir, user, username, team_list)


def render_session_setup(curriculum: dict, sessions_dir: Path, user: str, username: str, team_list=None):
    """Render session setup form (PRE phase)."""
    st.subheader("🆕 Neue Session starten")
    
    # Default DEL teams if no list provided
    if team_list is None:
        team_list = [
            "ERC Ingolstadt",
            "Adler Mannheim",
            "Eisbären Berlin",
            "Red Bull München",
            "Kölner Haie",
            "Grizzlys Wolfsburg",
            "Pinguins Bremerhaven",
            "Straubing Tigers",
            "Nürnberg Ice Tigers",
            "Augsburger Panther",
            "Schwenninger Wild Wings",
            "Düsseldorfer EG",
            "Iserlohn Roosters",
            "Löwen Frankfurt"
        ]
    
    with st.form("session_setup"):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Datum", value=datetime.now())
            date_str = date.strftime("%Y-%m-%d")
            
            league = st.text_input("Liga", value="DEL")
        
        with col2:
            home = st.selectbox("Team Home", team_list, index=0)
            away = st.selectbox("Team Away", team_list, index=1)
        
        st.divider()
        
        # Module selection
        modules = list_modules(curriculum)
        if not modules:
            st.warning("Keine Module verfügbar.")
            st.stop()
        
        module_options = {
            f"{m['module_id']} – {m['module_title']}": m["module_id"]
            for m in modules
        }
        
        # Check if module was preselected from Curriculum page
        default_idx = 0
        if "selected_module_id" in st.session_state:
            preselect_id = st.session_state["selected_module_id"]
            for i, (label, mod_id) in enumerate(module_options.items()):
                if mod_id == preselect_id:
                    default_idx = i
                    st.info(f"✅ Modul **{preselect_id}** aus Curriculum vorausgewählt")
                    break
        
        selected_module_label = st.selectbox("Modul auswählen", list(module_options.keys()), index=default_idx)
        selected_module_id = module_options[selected_module_label]
        
        # Drill selection
        drills = list_drills_for_module(curriculum, selected_module_id)
        
        if not drills:
            st.warning(f"Modul {selected_module_id} hat noch keine Drills.")
            st.form_submit_button("Session starten", disabled=True)
            return
        
        drill_options = {
            f"{d['drill_id']} – {d['drill_title']}": d["drill_id"]
            for d in drills
        }
        
        selected_drill_label = st.selectbox("Drill auswählen", list(drill_options.keys()))
        selected_drill_id = drill_options[selected_drill_label]
        
        st.divider()
        
        # Drill-specific goal suggestions
        drill_goals = {
            "A1_D1": [
                "Dreiecke in der D-Zone bewusst erkennen",
                "Center-Positionierung (low/middle/high) verstehen",
                "Breakout-Qualität bewerten lernen",
                "Forward-Positioning beim Puck-Retrieval beobachten",
                "Dreieck-Stabilität über alle 3 Drittel verfolgen"
            ],
            "A1_Q1": [
                "Grundlagen-Wissen zu Rollen festigen",
                "Dreieck-Konzept verinnerlichen",
                "Center-Aufgaben in D-Zone lernen",
                "Begriffe sicher anwenden können"
            ],
            "default": [
                "Konzepte aus diesem Drill im Spiel erkennen",
                "Bewertungs-Kompetenz entwickeln",
                "System-Reads verbessern"
            ]
        }
        
        # Get goals for selected drill or use default
        goal_options = drill_goals.get(selected_drill_id, drill_goals["default"]) + ["Eigenes Ziel..."]
        
        goal_preset = st.selectbox("Ziel dieser Session", goal_options)
        
        if goal_preset == "Eigenes Ziel...":
            goal = st.text_input("Eigenes Ziel eingeben", max_chars=200, placeholder="z.B. Winger-Anpassung bei Center high beobachten")
        else:
            goal = goal_preset
        
        confidence = st.slider("Confidence (1-5)", 1, 5, 3)
        
        submitted = st.form_submit_button("🚀 Session starten", type="primary")
    
    if submitted:
        if not home or not away:
            st.error("Bitte beide Teams eingeben.")
            return
        
        # Create session
        session = create_session(
            sessions_dir=sessions_dir,
            user=username,
            date=date_str,
            league=league,
            home=home,
            away=away,
            module_id=selected_module_id,
            drill_id=selected_drill_id,
            goal=goal,
            confidence=confidence
        )
        
        st.success(f"✅ Session {session['session_id']} erstellt!")
        st.rerun()


def render_active_session(
    session: dict,
    curriculum: dict,
    sessions_dir: Path,
    user: str,
    username: str,
    team_logo_callback=None
):
    """Render active session with phase workflow."""
    
    # Only show "Neue Session" button if session is truly active (not done)
    if session.get("state") == "active":
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader("📍 Aktive Session")
        
        with col2:
            if st.button("✅ POST", type="primary", use_container_width=True):
                # Show POST form
                st.session_state["show_post_form"] = True
        
        with col3:
            if st.button("🔄 Abbrechen", type="secondary", use_container_width=True):
                # Mark current session as cancelled
                session["state"] = "cancelled"
                save_session(sessions_dir, session)
                st.success("Session abgebrochen. Neue Session starten...")
                st.rerun()
    else:
        st.subheader("📍 Aktive Session")
    
    # Show POST completion section if button was clicked
    if st.session_state.get("show_post_form"):
        st.divider()
        st.markdown("### ✅ Session abschließen")
        
        # Optional notes expander (collapsed by default)
        with st.expander("📝 Optional: Notizen & Reflexion", expanded=False):
            summary = st.text_area("Zusammenfassung", max_chars=300, height=100, 
                                  help="Wichtige Erkenntnisse aus dieser Session")
            unclear = st.text_area("Offene Fragen", max_chars=200, height=80,
                                  help="Was ist noch unklar oder muss geklärt werden?")
            
            if st.button("💾 Mit Notizen speichern", type="secondary", use_container_width=True, key="save_with_notes"):
                session_id = session.get("session_id")
                fresh_session = load_session(sessions_dir, session_id)
                if fresh_session:
                    complete_session(fresh_session, summary, unclear, "", 3)
                    save_session(sessions_dir, fresh_session)
                    st.session_state["force_new_session"] = True
                    st.session_state["show_post_form"] = False
                    st.success("✅ Session mit Notizen abgeschlossen!")
                    st.rerun()
        
        # Main completion button (always visible)
        if st.button("🏁 Jetzt abschließen", type="primary", use_container_width=True, key="complete_now"):
            session_id = session.get("session_id")
            fresh_session = load_session(sessions_dir, session_id)
            if fresh_session:
                complete_session(fresh_session, "", "", "", 3)
                save_session(sessions_dir, fresh_session)
                st.session_state["force_new_session"] = True
                st.session_state["show_post_form"] = False
                st.success("✅ Session abgeschlossen!")
                st.rerun()
        
        st.divider()
        st.info("⬅️ Falls du doch noch Phasen bearbeiten möchtest, wähle unten eine Phase aus.")
    
    game = session.get("game", {})
    module_id = session.get("module_id", "")
    drill_id = session.get("drill_id", "")
    
    # Game header
    render_game_header(game, team_logo_callback)
    
    st.divider()
    
    # Session info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Modul", module_id)
    with col2:
        st.metric("Drill", drill_id)
    with col3:
        pre_data = session.get("pre", {})
        confidence = pre_data.get("confidence", 3)
        render_confidence_metric(confidence)
    
    # Show goal
    pre_goal = session.get("pre", {}).get("goal", "")
    if pre_goal:
        st.info(f"🎯 **Ziel:** {pre_goal}")
    
    st.divider()
    
    # Phase selector
    phases = ["PRE", "P1", "P2", "P3"]
    checkins = session.get("checkins", [])
    completed_phases = [c["phase"] for c in checkins]
    
    st.markdown("### Phase auswählen")
    phase_cols = st.columns(len(phases))
    
    selected_phase = None
    for i, phase in enumerate(phases):
        with phase_cols[i]:
            badge = render_phase_badge(phase)
            is_completed = phase in completed_phases
            button_label = f"{badge}\n{'✅' if is_completed else ''}"
            
            if st.button(button_label, key=f"phase_{phase}", use_container_width=True):
                selected_phase = phase
    
    if not selected_phase:
        st.info("👆 Wähle eine Phase aus (PRE für vor dem Spiel, P1/P2/P3 für Drittelpausen).")
        return
    
    st.divider()
    
    # Handle PRE phase (show pre info)
    if selected_phase == "PRE":
        st.markdown("### 📋 PRE – Session Setup")
        st.markdown(f"**Ziel:** {pre_goal or 'Kein Ziel definiert'}")
        st.markdown(f"**Confidence:** {confidence}/5")
        st.info("PRE-Phase abgeschlossen. Wähle P1-P3 für Check-ins.")
        return
    
    # Render drill for P1-P3
    st.markdown(f"### {render_phase_badge(selected_phase)} – Check-in")
    
    # Check if already completed
    if selected_phase in completed_phases:
        st.warning(f"Phase {selected_phase} bereits ausgefüllt. Erneutes Ausfüllen überschreibt.")
    
    drill = get_drill(curriculum, module_id, drill_id)
    if not drill:
        st.error(f"Drill {drill_id} nicht gefunden.")
        return
    
    # Prepare context
    context = {
        "user": user,
        "username": username,
        "game": game,
        "session_id": session["session_id"],
        "phase": selected_phase,
        "module_id": module_id,
        "drill_id": drill_id
    }
    
    # Render drill
    answers, feedback, next_task = render_drill(drill, context)
    
    if answers is not None:
        # Save checkin
        add_checkin(session, selected_phase, answers, feedback, next_task)
        save_session(sessions_dir, session)
        
        st.success(f"✅ Check-in {selected_phase} gespeichert!")
        
        # Show button to continue
        if st.button("➡️ Weiter"):
            st.rerun()


def render_post_phase(session: dict, curriculum: dict, sessions_dir: Path, username: str):
    """Render POST phase (session completion)."""
    st.markdown("### ✅ POST – Session abschließen")
    
    # Check if already completed
    if session.get("state") == "done":
        st.success("🎉 Diese Session ist bereits abgeschlossen!")
        post = session.get("post", {})
        
        col1, col2 = st.columns([2, 1])
        with col1:
            if post.get("summary"):
                st.markdown(f"**Zusammenfassung:** {post['summary']}")
            if post.get("next_module"):
                st.markdown(f"**Nächstes Modul:** {post['next_module']}")
        with col2:
            from academy.renderers import render_helpfulness_metric
            render_helpfulness_metric(post.get("helpfulness", 3))
        
        st.info("👈 Die Session ist abgeschlossen. Gehe zu Session Trainer für eine neue Session.")
        return