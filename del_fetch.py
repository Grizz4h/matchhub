from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dateutil import tz

BERLIN = tz.gettz("Europe/Berlin")

TABLE_URL = "https://www.penny-del.org/statistik/saison-2025-26/hauptrunde/tabelle"
FIXTURES_URL = "https://www.penny-del.org/statistik/saison-2025-26/hauptrunde/spielplan"
TEAM_BASE_URL = "https://www.penny-del.org/teams/{slug}/uebersicht"

ERC_NAME = "ERC Ingolstadt"

# Mapping: Voller Name -> Tabellen-Kürzel
TEAM_MAPPING = {
    "ERC Ingolstadt": "ING",
    "Kölner Haie": "KEC",
    "Adler Mannheim": "MAN",
    "Red Bull München": "RBM",
    "Eisbären Berlin": "EBB",
    "Grizzlys Wolfsburg": "WOB",
    "Pinguins Bremerhaven": "BHV",
    "Straubing Tigers": "STR",
    "Nürnberg Ice Tigers": "NIT",
    "Schwenninger Wild Wings": "SWW",
    "Augsburger Panther": "AEV",
    "Löwen Frankfurt": "FRA",
    "Dresdner Eislöwen": "DRE",
}

# Mapping: Voller Name -> URL Slug für Team-Seiten
TEAM_SLUG_MAPPING = {
    "ERC Ingolstadt": "erc-ingolstadt",
    "Kölner Haie": "koelner-haie",
    "Adler Mannheim": "adler-mannheim",
    "Red Bull München": "ehc-red-bull-muenchen",
    "Eisbären Berlin": "eisbaeren-berlin",
    "Grizzlys Wolfsburg": "grizzlys-wolfsburg",
    "Pinguins Bremerhaven": "pinguins-bremerhaven",
    "Straubing Tigers": "straubing-tigers",
    "Nürnberg Ice Tigers": "nuernberg-ice-tigers",
    "Schwenninger Wild Wings": "schwenninger-wild-wings",
    "Augsburger Panther": "augsburger-panther",
    "Löwen Frankfurt": "loewen-frankfurt",
    "Dresdner Eislöwen": "dresdner-eislowen",
}


@dataclass(frozen=True)
class CacheWrite:
    path: Path
    updated_at: str


def _http_get(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": "matchhub/1.0 (private tool)",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _wrap(updated_at: str, data: Any) -> Dict[str, Any]:
    return {"updated_at": updated_at, "data": data}


def write_cache(path: Path, data: Any) -> CacheWrite:
    _ensure_dir(path.parent)
    updated_at = datetime.now(tz=BERLIN).isoformat(timespec="seconds")
    path.write_text(json.dumps(_wrap(updated_at, data), ensure_ascii=False, indent=2), encoding="utf-8")
    return CacheWrite(path=path, updated_at=updated_at)


def read_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _clean(s: Any) -> str:
    x = str(s).strip()
    x = re.sub(r"\s+", " ", x)
    return x


def fetch_table(cache_dir: Path) -> CacheWrite:
    html = _http_get(TABLE_URL)
    tables = pd.read_html(html)
    if not tables:
        raise RuntimeError("Keine Tabelle auf der DEL-Tabelle-Seite gefunden.")
    df = tables[0].copy()
    df.columns = [str(c).strip() for c in df.columns]
    if "Team" in df.columns:
        df["Team"] = df["Team"].map(_clean)
    records = df.to_dict(orient="records")
    return write_cache(cache_dir / "del_table.json", records)


def _parse_date_de(cell: str) -> Optional[date]:
    s = _clean(cell)
    # Beispiele: "Freitag, 02.01.2026" oder "02.01.2026"
    if "," in s:
        s = s.split(",", 1)[1].strip()
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except Exception:
        return None


def _parse_time(cell: str) -> Optional[str]:
    s = _clean(cell)
    if re.match(r"^\d{2}:\d{2}$", s):
        return s
    return None


def fetch_fixtures(cache_dir: Path) -> CacheWrite:
    html = _http_get(FIXTURES_URL)
    tables = pd.read_html(html)
    if not tables:
        raise RuntimeError("Keine Tabellen auf der DEL-Spielplan-Seite gefunden.")

    games: List[Dict[str, Any]] = []
    for df in tables:
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        col_date = next((c for c in df.columns if "Datum" in c), None)
        col_time = next((c for c in df.columns if "Uhrzeit" in c), None)
        col_md = next((c for c in df.columns if "Spieltag" in c), None)
        col_home = next((c for c in df.columns if "Heim" in c), None)
        col_away = next((c for c in df.columns if "Gast" in c), None)

        # Wenn die Tabelle nicht wie ein Spielplan aussieht, skip
        if not (col_date and (col_home or col_away)):
            continue

        for _, row in df.iterrows():
            d = _parse_date_de(row[col_date]) if col_date else None
            t = _parse_time(row[col_time]) if col_time else None
            md = None
            if col_md is not None:
                try:
                    md = int(str(row[col_md]).strip())
                except Exception:
                    md = None

            home = _clean(row[col_home]) if col_home else None
            away = _clean(row[col_away]) if col_away else None

            faceoff = None
            if d and t:
                dt = datetime.strptime(f"{d.isoformat()} {t}", "%Y-%m-%d %H:%M").replace(tzinfo=BERLIN)
                faceoff = dt.isoformat(timespec="minutes")

            # Minimalfilter: wir wollen nur Zeilen, die nach Spiel aussehen
            if not (home and away and d):
                continue

            games.append(
                {
                    "date": d.isoformat(),
                    "time": t,
                    "matchday": md,
                    "home": home,
                    "away": away,
                    "faceoff": faceoff,
                }
            )

    # Dedupe
    uniq = {}
    for g in games:
        key = (g["date"], g.get("time"), g["home"], g["away"])
        uniq[key] = g
    games = list(uniq.values())

    return write_cache(cache_dir / "del_fixtures.json", games)


def pick_next_erc_game(fixtures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    today = datetime.now(tz=BERLIN).date()
    upcoming: List[Tuple[date, str, Dict[str, Any]]] = []
    for g in fixtures:
        try:
            d = datetime.strptime(g["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if d < today:
            continue
        if g.get("home") == ERC_NAME or g.get("away") == ERC_NAME:
            upcoming.append((d, g.get("time") or "99:99", g))
    upcoming.sort(key=lambda x: (x[0], x[1]))
    return upcoming[0][2] if upcoming else None


def find_team_row(table: List[Dict[str, Any]], team_name: str) -> Optional[Dict[str, Any]]:
    # Erst direkt suchen
    for r in table:
        if _clean(r.get("Team", "")) == team_name:
            return r
    
    # Falls nicht gefunden, versuche mit Mapping (voller Name -> Kürzel)
    short_name = TEAM_MAPPING.get(team_name)
    if short_name:
        for r in table:
            if _clean(r.get("Team", "")) == short_name:
                return r
    
    return None


def fetch_team_recent_games(cache_dir: Path, team_name: str) -> CacheWrite:
    """
    Fetches recent game results from team overview page.
    Parses "Letzte Ergebnisse" table.
    
    The HTML structure shows:
    - First team-meta div = Home team (with img alt="Team Name")
    - Second team-meta div = Away team
    - Scores are always: Home - Away
    - Winner has class="team-result__score--win" on their score
    """
    slug = TEAM_SLUG_MAPPING.get(team_name)
    if not slug:
        raise ValueError(f"No slug mapping found for team: {team_name}")
    
    url = TEAM_BASE_URL.format(slug=slug)
    html = _http_get(url)
    
    # Parse tables with pandas
    tables = pd.read_html(html)
    
    recent_games = []
    for df in tables:
        df = df.copy()
        if len(df.columns) >= 3 and len(df) >= 5:
            first_col = str(df.iloc[0, 0]).strip()
            if re.match(r"\d{2}\.\d{2}\.\d{4}", first_col):
                # Found the results table
                for idx, row in df.iterrows():
                    try:
                        date_str = _clean(str(row.iloc[0]))
                        score_str = _clean(str(row.iloc[1]))
                        matchday_str = _clean(str(row.iloc[2])) if len(row) > 2 else None
                        
                        game_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                        
                        # Parse score: "X - Y" or "X - Y (OT)" or "X - Y (SO)"
                        score_match = re.match(r"(\d+)\s*-\s*(\d+)", score_str)
                        if not score_match:
                            continue
                        
                        home_score = int(score_match.group(1))
                        away_score = int(score_match.group(2))
                        
                        is_ot = "(OT)" in score_str or "n.V." in score_str
                        is_so = "(SO)" in score_str or "n.P." in score_str
                        is_overtime = is_ot or is_so
                        
                        # Find the specific row in HTML using the EXACT date
                        # Use BeautifulSoup for reliable parsing
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # Find the table
                        table = None
                        for t in soup.find_all('table'):
                            if date_str in t.get_text():
                                table = t
                                break
                        
                        if not table:
                            continue
                        
                        # Find the row with this exact date
                        target_row = None
                        for tr in table.find_all('tr'):
                            date_cell = tr.find('td', class_='team-result__date')
                            if date_cell and date_cell.get_text(strip=True) == date_str:
                                target_row = tr
                                break
                        
                        if not target_row:
                            continue
                        
                        # Extract team logos from this specific row
                        team_logos_imgs = target_row.find_all('figure', class_='team-meta__logo')
                        if len(team_logos_imgs) < 2:
                            continue
                        
                        team_names = []
                        for fig in team_logos_imgs[:2]:
                            img = fig.find('img')
                            if img and img.get('alt'):
                                team_names.append(img['alt'])
                        
                        if len(team_names) < 2:
                            continue
                        
                        home_team = team_names[0]
                        away_team = team_names[1]
                        
                        # Determine if our team is home or away
                        is_home = (home_team == team_name)
                        is_away = (away_team == team_name)
                        
                        if not (is_home or is_away):
                            # Team name mismatch, skip
                            continue
                        
                        # Calculate team scores from perspective
                        team_score = home_score if is_home else away_score
                        opponent_score = away_score if is_home else home_score
                        
                        # Determine result - use simple score comparison
                        # Works for both regular and OT/SO games
                        if team_score > opponent_score:
                            result = "OTW" if is_overtime else "W"
                        elif team_score < opponent_score:
                            result = "OTL" if is_overtime else "L"
                        else:
                            result = "T"  # Shouldn't happen in DEL
                        
                        ot_so = "OT/SO" if is_overtime else ""
                        
                        matchday = None
                        try:
                            matchday = int(matchday_str) if matchday_str else None
                        except:
                            pass
                        
                        recent_games.append({
                            "date": game_date.isoformat(),
                            "score": score_str,
                            "team_score": team_score,
                            "opponent_score": opponent_score,
                            "result": result,
                            "ot_so": ot_so,
                            "matchday": matchday,
                        })
                    except Exception:
                        continue
                
                break  # Found the table, stop searching
    
    # Calculate form from last games
    last_10_results = [g["result"] for g in recent_games[:10]]
    wins = last_10_results.count("W")
    losses = last_10_results.count("L")
    
    data = {
        "team": team_name,
        "last_10_form": f"{wins}-{losses}",
        "recent_games": recent_games[:10],  # Keep last 10
    }
    
    # Cache with team-specific filename
    short_name = TEAM_MAPPING.get(team_name, team_name.replace(" ", "_"))
    cache_file = cache_dir / f"recent_{short_name.lower()}.json"
    return write_cache(cache_file, data)

