"""Drill engine: registry and dispatcher for drill types."""
import streamlit as st
from typing import Callable, Optional


# Drill registry: maps drill_type to render function
DRILL_REGISTRY: dict[str, Callable] = {}


def register_drill(drill_type: str):
    """Decorator to register a drill renderer."""
    def decorator(func: Callable):
        DRILL_REGISTRY[drill_type] = func
        return func
    return decorator


def render_drill(drill: dict, context: dict) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    """
    Render a drill based on its type.
    
    Args:
        drill: The drill configuration
        context: Context containing user, game, session_id, phase, etc.
    
    Returns:
        tuple of (answers, feedback, next_task) or (None, None, None) if not submitted
    """
    drill_type = drill.get("drill_type")
    
    if drill_type not in DRILL_REGISTRY:
        st.error(f"Drill type '{drill_type}' not registered.")
        return None, None, None
    
    renderer = DRILL_REGISTRY[drill_type]
    return renderer(drill, context)


def evaluate_coaching_rules(answers: dict, rules: list[dict], phase: str) -> tuple[str, str]:
    """
    Evaluate coaching rules based on answers.
    
    Args:
        answers: User's answers
        rules: List of coaching rules from drill config
        phase: Current phase (e.g., "P1", "P2", "P3")
    
    Returns:
        tuple of (feedback, next_task)
    """
    feedback_parts = []
    next_task_parts = []
    
    for rule in rules:
        condition = rule.get("condition", {})
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        # Get answer value
        answer_value = answers.get(field)
        
        # Evaluate condition
        match = False
        if operator == "==":
            match = answer_value == value
        elif operator == "!=":
            match = answer_value != value
        elif operator == "<=":
            match = answer_value <= value
        elif operator == ">=":
            match = answer_value >= value
        elif operator == "<":
            match = answer_value < value
        elif operator == ">":
            match = answer_value > value
        
        if match:
            fb = rule.get("feedback", "")
            nt = rule.get("next_task", "")
            
            # Replace {next_period} placeholder
            next_period_num = int(phase[1]) + 1 if phase.startswith("P") and len(phase) == 2 else ""
            if next_period_num and next_period_num <= 3:
                nt = nt.replace("{next_period}", str(next_period_num))
            else:
                nt = nt.replace("P{next_period}", "nächste Session")
            
            if fb:
                feedback_parts.append(fb)
            if nt:
                next_task_parts.append(nt)
    
    feedback = "\n\n".join(feedback_parts) if feedback_parts else ""
    next_task = "\n\n".join(next_task_parts) if next_task_parts else ""
    
    return feedback, next_task
