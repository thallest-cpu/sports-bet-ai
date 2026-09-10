from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

NBA_BASE_URL = "https://api.balldontlie.io/v1"
APP_TIMEZONE = "America/Sao_Paulo"
_CACHE: Dict[str, Tuple[float, Any]] = {}


def _resolve_nba_key() -> str:
    try:
        import streamlit as st
        value = st.secrets.get("BALLDONTLIE_API_KEY", "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.environ.get("BALLDONTLIE_API_KEY", "").strip()


def nba_key_configured() -> bool:
    return bool(_resolve_nba_key())


def _get(path: str, params: Optional[Dict[str, Any]] = None, ttl: int = 60) -> List[Dict[str, Any]]:
    key = _resolve_nba_key()
    if not key:
        return []
    cache_key = f"{path}|{sorted((params or {}).items())}"
    item = _CACHE.get(cache_key)
    if item and time.time() - item[0] <= ttl:
        return item[1]
    try:
        r = requests.get(f"{NBA_BASE_URL}/{path.lstrip('/')}", headers={"Authorization": key}, params=params or {}, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json().get("data", []) or []
        _CACHE[cache_key] = (time.time(), data)
        return data
    except Exception:
        return []


def get_nba_teams() -> List[Dict[str, Any]]:
    return _get("teams", ttl=24 * 3600)


def get_nba_players(team_id: int) -> List[Dict[str, Any]]:
    return _get("players", {"team_ids[]": team_id, "per_page": 100}, ttl=6 * 3600)


def get_nba_games_today() -> List[Dict[str, Any]]:
    today = datetime.now(ZoneInfo(APP_TIMEZONE)).date().isoformat()
    return _get("games", {"dates[]": today, "per_page": 100}, ttl=60)


def get_nba_live_box_scores() -> List[Dict[str, Any]]:
    live = _get("box_scores/live", ttl=15)
    if live:
        return live
    games = get_nba_games_today()
    result = []
    for game in games:
        status = str(game.get("status") or "").lower()
        if any(token in status for token in ("q1", "q2", "q3", "q4", "half", "ot", "in progress")):
            result.append(game)
    return result
