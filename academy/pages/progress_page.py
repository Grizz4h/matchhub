"""Progress page: Track learning progress across modules."""
import streamlit as st
from pathlib import Path
from academy.curriculum import load_curriculum
from academy.sessions import list_sessions
from collections import defaultdict


def render_progress_page(
    curriculum_path: Path,
    sessions_dir: Path,
    username: str
):
    """Render the progress tracking page."""
    st.header("📈 Lernfortschritt")
    st.caption("Übersicht über deine Academy-Journey")
    
    curriculum = load_curriculum(curriculum_path)
    user_sessions = list_sessions(sessions_dir, user=username)
    
    if not user_sessions:
        st.info("Noch keine Sessions vorhanden. Starte deine erste Session im Session Trainer!")
        return
    
    # Calculate stats
    total_sessions = len(user_sessions)
    completed_sessions = len([s for s in user_sessions if s.get("state") == "done"])
    active_sessions = len([s for s in user_sessions if s.get("state") == "active"])
    
    # Module stats
    module_counts = defaultdict(int)
    module_helpfulness = defaultdict(list)
    
    for session in user_sessions:
        module_id = session.get("module_id", "")
        if module_id:
            module_counts[module_id] += 1
            
            post = session.get("post", {})
            helpfulness = post.get("helpfulness")
            if helpfulness:
                module_helpfulness[module_id].append(helpfulness)
    
    # Display overall stats
    st.markdown("### 📊 Gesamt-Statistik")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sessions", total_sessions)
    with col2:
        st.metric("Abgeschlossen", completed_sessions)
    with col3:
        st.metric("Aktiv", active_sessions)
    with col4:
        modules_touched = len(module_counts)
        st.metric("Module bearbeitet", modules_touched)
    
    st.divider()
    
    # Module breakdown
    st.markdown("### 📚 Fortschritt nach Modulen")
    
    if not module_counts:
        st.info("Noch keine Module begonnen.")
        return
    
    # Sort modules by count
    sorted_modules = sorted(module_counts.items(), key=lambda x: x[1], reverse=True)
    
    for module_id, count in sorted_modules:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**Modul {module_id}**")
            
            with col2:
                st.metric("Sessions", count)
            
            with col3:
                if module_id in module_helpfulness and module_helpfulness[module_id]:
                    avg_help = sum(module_helpfulness[module_id]) / len(module_helpfulness[module_id])
                    stars = "⭐" * int(round(avg_help))
                    st.metric("Ø Helpfulness", stars)
                else:
                    st.metric("Ø Helpfulness", "–")
    
    st.divider()
    
    # Track overview
    st.markdown("### 🎯 Track-Übersicht")
    
    tracks = curriculum.get("tracks", [])
    
    for track in tracks:
        track_id = track["id"]
        track_title = track["title"]
        track_modules = track.get("modules", [])
        
        # Count modules touched in this track
        touched = sum(1 for m in track_modules if m["id"] in module_counts)
        total = len(track_modules)
        
        if touched == 0:
            continue
        
        progress = touched / total if total > 0 else 0
        
        with st.expander(f"Track {track_id}: {track_title}", expanded=False):
            st.progress(progress, text=f"{touched}/{total} Module begonnen")
            
            for module in track_modules:
                module_id = module["id"]
                if module_id in module_counts:
                    st.markdown(f"✅ **{module_id}**: {module['title']} ({module_counts[module_id]}x)")
                else:
                    st.markdown(f"⬜ **{module_id}**: {module['title']}")
