"""Curriculum loader and helper functions."""
import json
from pathlib import Path
from typing import Optional


def load_curriculum(curriculum_path: Path) -> dict:
    """Load curriculum from JSON file."""
    if not curriculum_path.exists():
        return {"tracks": []}
    
    with open(curriculum_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_track(curriculum: dict, track_id: str) -> Optional[dict]:
    """Get a track by ID."""
    for track in curriculum.get("tracks", []):
        if track["id"] == track_id:
            return track
    return None


def get_module(curriculum: dict, module_id: str) -> Optional[dict]:
    """Get a module by ID (format: A1, B2, etc.)."""
    track_id = module_id[0]
    track = get_track(curriculum, track_id)
    if not track:
        return None
    
    for module in track.get("modules", []):
        if module["id"] == module_id:
            return module
    return None


def get_drill(curriculum: dict, module_id: str, drill_id: str) -> Optional[dict]:
    """Get a drill by module_id and drill_id."""
    module = get_module(curriculum, module_id)
    if not module:
        return None
    
    for drill in module.get("drills", []):
        if drill["id"] == drill_id:
            return drill
    return None


def list_modules(curriculum: dict) -> list[dict]:
    """List all modules with track context."""
    modules = []
    for track in curriculum.get("tracks", []):
        for module in track.get("modules", []):
            modules.append({
                "track_id": track["id"],
                "track_title": track["title"],
                "module_id": module["id"],
                "module_title": module["title"],
                "module_summary": module.get("summary", ""),
                "drill_count": len(module.get("drills", []))
            })
    return modules


def list_drills_for_module(curriculum: dict, module_id: str) -> list[dict]:
    """List all drills for a module."""
    module = get_module(curriculum, module_id)
    if not module:
        return []
    
    drills = []
    for drill in module.get("drills", []):
        drills.append({
            "drill_id": drill["id"],
            "drill_title": drill["title"],
            "drill_type": drill["drill_type"]
        })
    return drills
