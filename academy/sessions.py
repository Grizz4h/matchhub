"""Session management: create, load, save, list sessions."""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


def create_session(
    sessions_dir: Path,
    user: str,
    date: str,
    league: str,
    home: str,
    away: str,
    module_id: str,
    drill_id: str,
    goal: str = "",
    confidence: int = 3
) -> dict:
    """Create a new session."""
    session_id = f"{date}_{home.replace(' ', '_')}_vs_{away.replace(' ', '_')}_{user}_{module_id}_{drill_id}"
    
    session = {
        "session_id": session_id,
        "user": user,
        "game": {
            "date": date,
            "league": league,
            "home": home,
            "away": away
        },
        "module_id": module_id,
        "drill_id": drill_id,
        "pre": {
            "goal": goal,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        },
        "checkins": [],
        "post": {},
        "state": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Save to file
    sessions_dir.mkdir(parents=True, exist_ok=True)
    filepath = sessions_dir / f"{session_id}.json"
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)
    
    return session


def load_session(sessions_dir: Path, session_id: str) -> Optional[dict]:
    """Load a session by ID."""
    filepath = sessions_dir / f"{session_id}.json"
    if not filepath.exists():
        return None
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(sessions_dir: Path, session: dict):
    """Save session to file."""
    session["updated_at"] = datetime.now().isoformat()
    session_id = session["session_id"]
    filepath = sessions_dir / f"{session_id}.json"
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)


def add_checkin(session: dict, phase: str, answers: dict, feedback: str = "", next_task: str = ""):
    """Add a checkin to the session."""
    checkin = {
        "phase": phase,
        "timestamp": datetime.now().isoformat(),
        "answers": answers,
        "feedback": feedback,
        "next_task": next_task
    }
    
    session["checkins"].append(checkin)
    return session


def complete_session(session: dict, summary: str = "", unclear: str = "", next_module: str = "", helpfulness: int = 3):
    """Complete a session with post data."""
    session["post"] = {
        "summary": summary,
        "unclear": unclear,
        "next_module": next_module,
        "helpfulness": helpfulness,
        "timestamp": datetime.now().isoformat()
    }
    session["state"] = "done"
    return session


def list_sessions(sessions_dir: Path, user: Optional[str] = None, module_id: Optional[str] = None) -> list[dict]:
    """List all sessions, optionally filtered by user or module."""
    if not sessions_dir.exists():
        return []
    
    sessions = []
    for filepath in sessions_dir.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                session = json.load(f)
                
                # Apply filters
                if user and session.get("user") != user:
                    continue
                if module_id and session.get("module_id") != module_id:
                    continue
                
                sessions.append(session)
        except Exception:
            continue
    
    # Sort by created_at descending
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions


def get_active_session(sessions_dir: Path, user: str) -> Optional[dict]:
    """Get the most recent active session for a user."""
    sessions = list_sessions(sessions_dir, user=user)
    for session in sessions:
        if session.get("state") == "active":
            return session
    return None
