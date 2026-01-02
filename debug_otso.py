#!/usr/bin/env python3
"""Debug tool to check OT/SO game parsing"""

import json
import re
import requests
from pathlib import Path

# Check current cached data
cache_file = Path("data/cache/recent_ing.json")
if cache_file.exists():
    data = json.loads(cache_file.read_text())
    print("=== CURRENT CACHE ===")
    for game in data["data"]["recent_games"][:10]:
        if "(OT)" in game["score"] or "(SO)" in game["score"]:
            print(f"\nDate: {game['date']}")
            print(f"Score: {game['score']}")
            print(f"Team: {game['team_score']}, Opponent: {game['opponent_score']}")
            print(f"Result: {game['result']}")
            print(f"OT/SO: {game['ot_so']}")

# Fetch raw HTML and show structure
print("\n\n=== RAW HTML STRUCTURE ===")
url = "https://www.penny-del.org/teams/erc-ingolstadt/uebersicht"
headers = {'User-Agent': 'matchhub/1.0'}
r = requests.get(url, headers=headers, timeout=25)
html = r.text

# Find the section with results
# Look for "Letzte Ergebnisse" or similar
if "Letzte Ergebnisse" in html or "letzte-ergebnisse" in html:
    # Extract the relevant table section
    pattern = r'<table[^>]*>.*?28\.12\.2025.*?</table>'
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if match:
        table_html = match.group(0)
        print("\nTable with 28.12.2025:")
        print(table_html[:1000])
    else:
        # Try to find any table row with that date
        pattern = r'<tr[^>]*>.*?28\.12\.2025.*?</tr>'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            print("\nRow with 28.12.2025:")
            print(match.group(0))
        else:
            print("\nCould not find 28.12.2025 in HTML")
            # Show first few table rows
            pattern = r'<tr[^>]*>.*?\d{2}\.\d{2}\.\d{4}.*?</tr>'
            matches = list(re.finditer(pattern, html, re.DOTALL | re.IGNORECASE))[:3]
            for i, m in enumerate(matches):
                print(f"\n--- Row {i+1} ---")
                print(m.group(0)[:500])
