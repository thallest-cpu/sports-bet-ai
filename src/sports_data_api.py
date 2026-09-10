"""Camada de dados esportivos do BetAI Quant Pro.

Princípios:
- dados atuais/LIVE nunca usam snapshots locais como se fossem atuais;
- API-Football é a fonte principal quando a chave está configurada;
- ESPN é fallback somente para fixtures/placares básicos;
- cache possui TTL explícito por tipo de dado.
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

APP_TIMEZONE = "America/Sao_Paulo"
FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"


def _resolve_football_api_key() -> str:
    try:
        import streamlit as st
        value = st.secrets.get("FOOTBALL_API_KEY", "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.environ.get("FOOTBALL_API_KEY", "").strip()


FOOTBALL_API_KEY = _resolve_football_api_key()
FOOTBALL_HEADERS = {"x-apisports-key": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}

API_FOOTBALL_LEAGUES: Dict[str, int] = {
    "Brasileirão Série A": 71,
    "Premier League": 39,
    "La Liga": 140,
    "Serie A (Itália)": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "Champions League": 2,
    "Copa Libertadores": 13,
    "Copa Sul-Americana": 11,
}

LEAGUE_TO_ESPN_SLUG: Dict[int, str] = {
    71: "bra.1",
    39: "eng.1",
    140: "esp.1",
    135: "ita.1",
    78: "ger.1",
    61: "fra.1",
    2: "uefa.champions",
    13: "conmebol.libertadores",
    11: "conmebol.sudamericana",
}

API_LEAGUE_TO_SEASON_KEY = {
    "Brasileirão Série A": "Brasileirão Série A 2026",
    "Premier League": "Premier League 2026/27",
    "La Liga": "La Liga 2026/27",
    "Serie A (Itália)": "Serie A 2026/27",
    "Bundesliga": "Bundesliga 2026/27",
    "Ligue 1": "Ligue 1 2026/27",
    "Champions League": "UEFA Champions League 2026/27",
    "Copa Libertadores": "Copa Libertadores 2026",
    "Copa Sul-Americana": "Copa Sul-Americana 2026",
}

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "BetAI-Quant-Pro/2.0"})
_CACHE: Dict[str, Tuple[float, Any]] = {}
_LAST_STATUS: Dict[str, Any] = {
    "source": "not_called",
    "ok": None,
    "message": "Nenhuma consulta realizada ainda.",
    "at": None,
}


def clear_api_cache() -> None:
    _CACHE.clear()


def _cache_get(key: str, ttl: int) -> Any:
    item = _CACHE.get(key)
    if not item:
        return None
    created, value = item
    if time.time() - created <= ttl:
        return value
    _CACHE.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> Any:
    _CACHE[key] = (time.time(), value)
    return value


def _set_status(source: str, ok: bool, message: str = "") -> None:
    _LAST_STATUS.update({
        "source": source,
        "ok": ok,
        "message": message,
        "at": datetime.now(ZoneInfo(APP_TIMEZONE)).isoformat(timespec="seconds"),
    })


def get_api_status() -> Dict[str, Any]:
    return dict(_LAST_STATUS)


def api_key_configured() -> bool:
    return bool(_resolve_football_api_key())


def _api_get(path: str, params: Optional[Dict[str, Any]] = None, *, ttl: int = 0,
             api_key: Optional[str] = None) -> Optional[Any]:
    key = (api_key or _resolve_football_api_key()).strip()
    if not key:
        _set_status("API-Football", False, "FOOTBALL_API_KEY não configurada")
        return None

    params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    cache_key = f"{path}|{sorted(params.items())}|{key[-4:]}"
    if ttl > 0:
        cached = _cache_get(cache_key, ttl)
        if cached is not None:
            return cached

    try:
        response = _SESSION.get(
            f"{FOOTBALL_BASE_URL}/{path.lstrip('/')}",
            headers={"x-apisports-key": key},
            params=params,
            timeout=12,
        )
        if response.status_code != 200:
            _set_status("API-Football", False, f"HTTP {response.status_code}")
            return None
        payload = response.json()
        errors = payload.get("errors") or {}
        if errors:
            message = "; ".join(str(v) for v in errors.values() if v) or str(errors)
            _set_status("API-Football", False, message)
            return None
        result = payload.get("response")
        if result is None:
            result = []
        count = len(result) if hasattr(result, "__len__") else 1
        _set_status("API-Football", True, f"{count} registro(s)")
        return _cache_set(cache_key, result) if ttl > 0 else result
    except requests.RequestException as exc:
        _set_status("API-Football", False, f"Falha de rede: {exc.__class__.__name__}")
        return None
    except ValueError:
        _set_status("API-Football", False, "Resposta JSON inválida")
        return None


def _local_date() -> str:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).strftime("%Y-%m-%d")


def get_api_football_teams(league_id: int, season: int = 2026,
                           api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    return _api_get("teams", {"league": league_id, "season": season}, ttl=6 * 3600, api_key=api_key) or []


def get_api_football_squad(team_id: int, api_key: Optional[str] = None,
                           allow_stale_fallback: bool = False) -> List[Dict[str, Any]]:
    # Não existe fallback local por padrão: elenco antigo não deve parecer atual.
    result = _api_get("players/squads", {"team": team_id}, ttl=6 * 3600, api_key=api_key)
    if not result:
        return []
    return result[0].get("players", []) if result else []


def get_api_football_live_fixtures(league_id: Optional[int] = None,
                                   api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"live": "all", "timezone": APP_TIMEZONE}
    if league_id:
        params["league"] = league_id
    result = _api_get("fixtures", params, ttl=12, api_key=api_key)
    if result is not None:
        return result
    return _fetch_espn_fixtures(league_id=league_id, live_only=True)


def get_api_football_all_live(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    return get_api_football_live_fixtures(None, api_key=api_key)


def get_api_football_today_fixtures(league_id: Optional[int] = None,
                                    api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"date": _local_date(), "timezone": APP_TIMEZONE}
    if league_id:
        params["league"] = league_id
    result = _api_get("fixtures", params, ttl=60, api_key=api_key)
    if result is not None:
        return result
    return _fetch_espn_fixtures(league_id=league_id, live_only=False)


def get_api_football_fixtures_by_league(league_id: int, season: int = 2026,
                                        next_games: int = 20, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    params = {"league": league_id, "season": season, "next": next_games, "timezone": APP_TIMEZONE}
    return _api_get("fixtures", params, ttl=300, api_key=api_key) or []


def get_api_football_fixture_details(fixture_id: int, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = _api_get("fixtures", {"id": fixture_id, "timezone": APP_TIMEZONE}, ttl=12, api_key=api_key)
    return result[0] if result else None


def get_api_football_fixture_events(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "events" in detail:
        return detail.get("events") or []
    return _api_get("fixtures/events", {"fixture": fixture_id}, ttl=12, api_key=api_key) or []


def get_api_football_fixture_statistics(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "statistics" in detail:
        return detail.get("statistics") or []
    return _api_get("fixtures/statistics", {"fixture": fixture_id}, ttl=55, api_key=api_key) or []


def get_api_football_fixture_lineups(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "lineups" in detail:
        return detail.get("lineups") or []
    return _api_get("fixtures/lineups", {"fixture": fixture_id}, ttl=60, api_key=api_key) or []


def get_api_football_fixture_players(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "players" in detail:
        return detail.get("players") or []
    return _api_get("fixtures/players", {"fixture": fixture_id}, ttl=55, api_key=api_key) or []


def get_api_football_standings(league_id: int, season: int = 2026,
                               api_key: Optional[str] = None) -> List[List[Dict[str, Any]]]:
    result = _api_get("standings", {"league": league_id, "season": season}, ttl=600, api_key=api_key) or []
    if not result:
        return []
    league = result[0].get("league") or {}
    return league.get("standings") or []


def get_api_football_team_statistics(league_id: int, team_id: int, season: int = 2026,
                                     api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = _api_get("teams/statistics", {"league": league_id, "season": season, "team": team_id}, ttl=900, api_key=api_key)
    if isinstance(result, dict):
        return result
    return result[0] if isinstance(result, list) and result else None


def get_api_football_odds(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    return _api_get("odds", {"fixture": fixture_id}, ttl=180, api_key=api_key) or []


def get_api_football_predictions(fixture_id: int, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = _api_get("predictions", {"fixture": fixture_id}, ttl=1800, api_key=api_key)
    return result[0] if result else None


def _fetch_espn_fixtures(league_id: Optional[int], live_only: bool) -> List[Dict[str, Any]]:
    if league_id and league_id in LEAGUE_TO_ESPN_SLUG:
        slugs = [LEAGUE_TO_ESPN_SLUG[league_id]]
    elif league_id:
        slugs = []
    else:
        slugs = list(dict.fromkeys(LEAGUE_TO_ESPN_SLUG.values()))

    results: List[Dict[str, Any]] = []
    date_param = datetime.now(ZoneInfo(APP_TIMEZONE)).strftime("%Y%m%d")
    for slug in slugs:
        cache_key = f"espn|{slug}|{date_param}|{live_only}"
        cached = _cache_get(cache_key, 15 if live_only else 60)
        if cached is not None:
            results.extend(cached)
            continue
        league_results: List[Dict[str, Any]] = []
        try:
            response = _SESSION.get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard",
                params={"dates": date_param, "limit": 200}, timeout=10,
            )
            if response.status_code != 200:
                continue
            for event in response.json().get("events", []) or []:
                comp = (event.get("competitions") or [{}])[0]
                status = comp.get("status") or event.get("status") or {}
                state = ((status.get("type") or {}).get("state") or "pre").lower()
                if live_only and state != "in":
                    continue
                league_results.append(_format_espn_event(event, comp, status, slug))
            _cache_set(cache_key, league_results)
            results.extend(league_results)
        except requests.RequestException:
            continue

    _set_status("ESPN fallback", True, f"{len(results)} fixture(s); detalhes limitados")
    return results


def _format_espn_event(event: Dict[str, Any], comp: Dict[str, Any], status: Dict[str, Any], slug: str) -> Dict[str, Any]:
    competitors = comp.get("competitors") or []
    home = next((x for x in competitors if x.get("homeAway") == "home"), {})
    away = next((x for x in competitors if x.get("homeAway") == "away"), {})
    home_team, away_team = home.get("team") or {}, away.get("team") or {}
    status_type = status.get("type") or {}
    state = (status_type.get("state") or "pre").lower()
    clock = status.get("displayClock") or ""
    numbers = re.findall(r"\d+", clock)
    elapsed = int(numbers[0]) if numbers and state == "in" else None
    short = "LIVE" if state == "in" else ("FT" if state == "post" else "NS")

    league_name = next((name for name, lid in API_FOOTBALL_LEAGUES.items() if LEAGUE_TO_ESPN_SLUG.get(lid) == slug), slug)
    country_map = {"bra.1": "Brasil", "eng.1": "Inglaterra", "esp.1": "Espanha", "ita.1": "Itália", "ger.1": "Alemanha", "fra.1": "França"}
    reverse_ids = {v: k for k, v in LEAGUE_TO_ESPN_SLUG.items()}

    def _score(obj: Dict[str, Any]) -> int:
        try:
            return int(float(obj.get("score") or 0))
        except (TypeError, ValueError):
            return 0

    return {
        "fixture": {
            "id": int(re.sub(r"\D", "", str(event.get("id") or "0")) or 0),
            "date": event.get("date") or "",
            "status": {"long": status_type.get("description") or "", "short": short, "elapsed": elapsed},
            "source": "ESPN",
        },
        "league": {"id": reverse_ids.get(slug), "name": league_name, "country": country_map.get(slug, "")},
        "teams": {
            "home": {"id": home_team.get("id"), "name": home_team.get("displayName") or "Mandante", "logo": home_team.get("logo") or ""},
            "away": {"id": away_team.get("id"), "name": away_team.get("displayName") or "Visitante", "logo": away_team.get("logo") or ""},
        },
        "goals": {"home": _score(home), "away": _score(away)},
        "events": [], "statistics": [], "lineups": [], "players": [],
    }
