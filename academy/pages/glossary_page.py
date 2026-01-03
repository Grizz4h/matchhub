"""Glossary page: Browse tactical terms."""
import streamlit as st
from pathlib import Path
import json


def render_glossary_page(wiki_path: Path):
    """Render the glossary/wiki page."""
    st.header("📖 Taktik-Glossar")
    st.caption("Begriffe und Konzepte aus dem Eishockey-Taktik-Universum")
    
    if not wiki_path.exists():
        st.warning("Wiki noch nicht angelegt. Erstelle `data/wiki_terms.json`")
        st.info("Diese Seite nutzt die gleichen Wiki-Daten wie MatchHub.")
        return
    
    try:
        with open(wiki_path, "r", encoding="utf-8") as f:
            wiki_data = json.load(f)
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return
    
    if not wiki_data:
        st.info("Wiki ist leer.")
        return
    
    # Search field
    search = st.text_input(
        "🔍 Begriff suchen",
        placeholder="z.B. Dreieck, Center, Forecheck, Box+1..."
    )
    
    # Filter terms
    terms = list(wiki_data.keys())
    if search:
        terms = [t for t in terms if search.lower() in t.lower()]
    
    if not terms:
        st.info("Keine Treffer.")
        return
    
    st.caption(f"{len(terms)} Begriff(e) gefunden")
    st.divider()
    
    # Display terms
    for term_name in sorted(terms):
        term = wiki_data[term_name]
        
        with st.expander(f"📖 {term_name}", expanded=False):
            short_desc = term.get("short", "")
            if short_desc:
                st.markdown(f"**{short_desc}**")
            
            details = term.get("details", "")
            if details:
                st.markdown(details)
            
            watch_items = term.get("watch", [])
            if watch_items:
                st.markdown("**Worauf achten:**")
                for item in watch_items:
                    st.markdown(f"- {item}")
