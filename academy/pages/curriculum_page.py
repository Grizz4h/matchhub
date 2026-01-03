"""Curriculum page: Browse all tracks and modules."""
import streamlit as st
from pathlib import Path
from academy.curriculum import load_curriculum
from academy.renderers import render_module_card


def render_curriculum_page(curriculum_path: Path):
    """Render the curriculum overview page."""
    st.header("📚 Academy Curriculum")
    st.caption("Vollständige Übersicht aller Tracks und Module")
    
    curriculum = load_curriculum(curriculum_path)
    tracks = curriculum.get("tracks", [])
    
    if not tracks:
        st.warning("Curriculum noch nicht geladen.")
        return
    
    # Stats
    total_modules = sum(len(track.get("modules", [])) for track in tracks)
    total_drills = sum(
        len(module.get("drills", []))
        for track in tracks
        for module in track.get("modules", [])
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tracks", len(tracks))
    with col2:
        st.metric("Module", total_modules)
    with col3:
        st.metric("Drills", total_drills)
    
    st.divider()
    
    # Filter
    filter_track = st.selectbox(
        "Track filtern",
        ["Alle"] + [f"{t['id']} – {t['title']}" for t in tracks],
        key="curriculum_track_filter"
    )
    
    # Display tracks
    for track in tracks:
        track_id = track["id"]
        track_title = track["title"]
        track_goal = track.get("goal", "")
        modules = track.get("modules", [])
        
        # Apply filter
        if filter_track != "Alle" and not filter_track.startswith(track_id):
            continue
        
        st.markdown(f"## Track {track_id}: {track_title}")
        st.caption(f"🎯 {track_goal}")
        
        if not modules:
            st.info("Noch keine Module verfügbar.")
            continue
        
        # Display modules
        for module in modules:
            render_module_card(track_id, track_title, module, expanded=False)
        
        st.divider()
