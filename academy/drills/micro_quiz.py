"""Micro Quiz drill: Quick multiple-choice questions with explanations."""
import streamlit as st
from academy.drill_engine import register_drill
import time


@register_drill("micro_quiz")
def render_micro_quiz(drill: dict, context: dict):
    """
    Render micro quiz drill.
    
    Shows timed multiple-choice questions with immediate feedback.
    """
    config = drill.get("config", {})
    questions = config.get("questions", [])
    time_limit = config.get("time_limit", 60)
    
    phase = context.get("phase", "PRE")
    
    st.markdown(f"### {drill.get('title', 'Micro Quiz')}")
    st.caption(f"⏱️ Zeit-Limit: {time_limit} Sekunden")
    
    if not questions:
        st.warning("Keine Fragen konfiguriert.")
        return None, None, None
    
    # Initialize session state for quiz
    quiz_key = f"quiz_{drill.get('id', 'quiz')}_{phase}"
    
    if f"{quiz_key}_started" not in st.session_state:
        st.session_state[f"{quiz_key}_started"] = False
        st.session_state[f"{quiz_key}_answers"] = {}
        st.session_state[f"{quiz_key}_start_time"] = None
    
    # Start button
    if not st.session_state[f"{quiz_key}_started"]:
        if st.button("▶️ Quiz starten", key=f"{quiz_key}_start"):
            st.session_state[f"{quiz_key}_started"] = True
            st.session_state[f"{quiz_key}_start_time"] = time.time()
            st.rerun()
        return None, None, None
    
    # Calculate elapsed time
    elapsed = int(time.time() - st.session_state[f"{quiz_key}_start_time"])
    remaining = max(0, time_limit - elapsed)
    
    # Show timer
    if remaining > 0:
        st.progress(remaining / time_limit, text=f"⏱️ {remaining}s verbleibend")
    else:
        st.error("⏰ Zeit abgelaufen!")
    
    # Render questions
    answers = st.session_state[f"{quiz_key}_answers"]
    
    with st.form(key=f"{quiz_key}_form"):
        for i, q in enumerate(questions):
            q_id = q.get("id", f"q{i+1}")
            question_text = q.get("question", "")
            options = q.get("options", [])
            
            st.markdown(f"**{i+1}. {question_text}**")
            answer = st.radio(
                "Wähle eine Antwort:",
                options,
                key=f"{quiz_key}_{q_id}",
                label_visibility="collapsed"
            )
            answers[q_id] = answer
            st.divider()
        
        submitted = st.form_submit_button("✅ Quiz abschließen")
    
    if submitted or remaining == 0:
        # Evaluate answers
        correct_count = 0
        total_count = len(questions)
        
        st.session_state[f"{quiz_key}_started"] = False  # Reset for next time
        
        st.success(f"✅ Quiz abgeschlossen in {elapsed}s!")
        
        # Show results with explanations
        st.markdown("---")
        st.markdown("### 📊 Ergebnisse")
        
        for i, q in enumerate(questions):
            q_id = q.get("id", f"q{i+1}")
            question_text = q.get("question", "")
            correct_answer = q.get("correct", "")
            explanation = q.get("explanation", "")
            user_answer = answers.get(q_id, "")
            
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
            
            with st.expander(
                f"{'✅' if is_correct else '❌'} Frage {i+1}: {question_text}",
                expanded=not is_correct
            ):
                st.markdown(f"**Deine Antwort:** {user_answer}")
                st.markdown(f"**Korrekt:** {correct_answer}")
                
                if explanation:
                    st.info(f"💡 **Erklärung:** {explanation}")
        
        # Summary
        score = int((correct_count / total_count) * 100)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Richtig", f"{correct_count}/{total_count}")
        with col2:
            st.metric("Score", f"{score}%")
        with col3:
            emoji = "🏆" if score >= 80 else "👍" if score >= 60 else "💪"
            st.metric("Rating", emoji)
        
        # Return answers as simple dict
        feedback = f"Quiz abgeschlossen: {correct_count}/{total_count} richtig ({score}%)"
        next_task = "Wiederhole Begriffe mit < 60% Erfolgsrate" if score < 60 else ""
        
        return answers, feedback, next_task
    
    return None, None, None
