"""Period Check-in drill: Questions during period breaks."""
import streamlit as st
from academy.drill_engine import register_drill, evaluate_coaching_rules


@register_drill("period_checkin")
def render_period_checkin(drill: dict, context: dict):
    """
    Render period check-in drill.
    
    Shows questions configured in drill config, evaluates coaching rules,
    and returns answers + feedback.
    """
    config = drill.get("config", {})
    questions = config.get("questions", [])
    coaching_rules = config.get("coaching_rules", [])
    
    user = context.get("user", "")
    phase = context.get("phase", "P1")
    
    st.markdown(f"### {drill.get('title', 'Period Check-in')}")
    st.caption(f"Phase: {phase}")
    
    if not questions:
        st.warning("Keine Fragen konfiguriert.")
        return None, None, None
    
    # Render questions
    answers = {}
    
    with st.form(key=f"period_checkin_{phase}"):
        for q in questions:
            q_id = q.get("id")
            q_type = q.get("type")
            q_label = q.get("label")
            q_required = q.get("required", False)
            user_filter = q.get("user_filter", [])
            
            # Skip question if user filter doesn't match
            if user_filter and user not in user_filter:
                continue
            
            # Render based on type
            if q_type == "radio":
                options = q.get("options", [])
                answer = st.radio(q_label, options, key=q_id)
                answers[q_id] = answer
            
            elif q_type == "slider":
                min_val = q.get("min", 1)
                max_val = q.get("max", 5)
                default_val = q.get("default", 3)
                answer = st.slider(q_label, min_val, max_val, default_val, key=q_id)
                answers[q_id] = answer
            
            elif q_type == "text":
                max_length = q.get("max_length", 120)
                answer = st.text_input(q_label, max_chars=max_length, key=q_id)
                if answer:
                    answers[q_id] = answer
                elif not q_required:
                    answers[q_id] = ""
            
            elif q_type == "select":
                options = q.get("options", [])
                answer = st.selectbox(q_label, options, key=q_id)
                answers[q_id] = answer
            
            else:
                st.warning(f"Unbekannter Question-Type: {q_type}")
        
        submitted = st.form_submit_button("💾 Speichern")
    
    if submitted:
        # Evaluate coaching rules
        feedback, next_task = evaluate_coaching_rules(answers, coaching_rules, phase)
        
        # Show feedback immediately
        if feedback or next_task:
            st.success("✅ Gespeichert!")
            
            if feedback:
                st.info(feedback)
            
            if next_task:
                st.warning(f"**Next Task:** {next_task}")
        else:
            st.success("✅ Gespeichert!")
        
        return answers, feedback, next_task
    
    return None, None, None
