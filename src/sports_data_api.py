"""Camada de dados esportivos do BetAI Quant Pro.

Objetivos desta versão:
- placares/fixtures atuais não usam CSV ou snapshot histórico;
- ESPN é usada para placar e calendário ao vivo com polling curto sem consumir
  a quota da API-Football;
- API-Football é usada para elencos, estatísticas de temporada e odds quando
  a chave está configurada;
- todas as fontes possuem cache e falham de forma explícita, sem inventar dados.

A ESPN não oferece contrato de estabilidade para estes endpoints públicos; por
isso toda chamada possui fallback e tratamento de erro. Dados avançados da
API-Football continuam sendo a fonte preferida quando disponíveis.
"""
from __future__ import annotations

import os
import hashlib
import threading
from pathlib import Path
from datetime import timezone
from src.quota import QuotaGuard
from src.settings import secret
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests

APP_TIMEZONE = "America/Sao_Paulo"
FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
ESPN_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
ESPN_STANDINGS_BASE_URL = "https://site.api.espn.com/apis/v2/sports/soccer"

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

# Competições disputadas dentro do ano-calendário. As demais usam temporada
# europeia cujo ano é o ano de início (ex.: 2026 para 2026/27).
CALENDAR_YEAR_LEAGUES = {71, 13, 11}

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "BetAI-Quant-Pro/3.0"})
_CACHE: Dict[str, Tuple[float, Any]] = {}
_ESPN_FAILURES = {}
_PROVIDER_STATUS: Dict[str, Dict[str, Any]] = {
    "api_football": {"ok": None, "message": "não consultada", "at": None},
    "espn": {"ok": None, "message": "não consultada", "at": None},
}


def now_local() -> datetime:
    return datetime.now(ZoneInfo(APP_TIMEZONE))


def current_season(league_id: int, when: Optional[datetime] = None) -> int:
    """Retorna o ano usado no parâmetro ``season`` da API-Football."""
    dt = when or now_local()
    if league_id in CALENDAR_YEAR_LEAGUES:
        return dt.year
    return dt.year if dt.month >= 7 else dt.year - 1


def _resolve_football_api_key() -> str:
    """Resolve a chave sem expô-la e aceita nomes legados comuns.

    O nome oficial continua sendo ``FOOTBALL_API_KEY``. Os aliases existem
    apenas para tornar upgrades de versões antigas tolerantes a configurações
    já salvas no Streamlit Cloud.
    """
    names = ("FOOTBALL_API_KEY", "API_FOOTBALL_KEY", "APISPORTS_KEY")
    try:
        import streamlit as st
        for name in names:
            value = st.secrets.get(name, "")
            if value:
                return str(value).strip()
    except Exception:
        pass
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def api_key_configured() -> bool:
    return bool(_resolve_football_api_key())


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


def _set_status(provider: str, ok: bool, message: str) -> None:
    _PROVIDER_STATUS[provider] = {
        "ok": ok,
        "message": message,
        "at": now_local().isoformat(timespec="seconds"),
    }


def _friendly_api_error(message: str) -> str:
    """Traduz erros frequentes da API-Football para mensagens úteis ao visitante."""
    raw = str(message or "").strip()
    low = raw.lower()
    quota_terms = ("request limit", "daily limit", "quota", "requests limit", "rate limit")
    if any(term in low for term in quota_terms):
        return "Limite diário da API-Football atingido. Dados avançados voltam quando a cota for renovada."
    if "invalid" in low and ("key" in low or "token" in low):
        return "Chave da API-Football inválida ou não autorizada."
    if "subscription" in low or "plan" in low:
        return "Este recurso não está disponível no plano atual da API-Football."
    return raw or "Falha ao consultar a API-Football."


def football_source_state() -> Dict[str, Any]:
    """Estado consolidado, separando configuração de disponibilidade real."""
    api = dict(_PROVIDER_STATUS["api_football"])
    espn = dict(_PROVIDER_STATUS["espn"])
    configured = api_key_configured()
    usable = bool(api.get("ok") is True or espn.get("ok") is True)
    return {
        "configured": configured,
        "usable": usable,
        "api": api,
        "espn": espn,
    }


def get_api_status() -> Dict[str, Any]:
    """Compatibilidade: devolve um resumo e os estados por provedor."""
    api = _PROVIDER_STATUS["api_football"]
    espn = _PROVIDER_STATUS["espn"]
    if api.get("ok"):
        source, state = "API-Football", api
    elif espn.get("ok"):
        source, state = "ESPN", espn
    else:
        source, state = "Sem fonte", api if api.get("ok") is False else espn
    return {
        "source": source,
        "ok": state.get("ok"),
        "message": state.get("message"),
        "at": state.get("at"),
        "providers": {k: dict(v) for k, v in _PROVIDER_STATUS.items()},
    }


def _api_get_raw(path: str, params: Optional[Dict[str, Any]] = None, *, ttl: int = 0,
             api_key: Optional[str] = None) -> Optional[Any]:
    key = (api_key or _resolve_football_api_key()).strip()
    if not key:
        _set_status("api_football", False, "FOOTBALL_API_KEY não configurada")
        return None

    params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    cache_key = f"api|{path}|{sorted(params.items())}|{hashlib.sha256(key.encode()).hexdigest()}"
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
            _set_status("api_football", False, f"HTTP {response.status_code}")
            return None
        payload = response.json()
        errors = payload.get("errors") or {}
        if errors:
            if isinstance(errors, dict):
                message = "; ".join(str(v) for v in errors.values() if v) or str(errors)
            else:
                message = str(errors)
            _set_status("api_football", False, _friendly_api_error(message))
            return None
        result = payload.get("response")
        if result is None:
            result = []
        count = len(result) if hasattr(result, "__len__") else 1
        _set_status("api_football", True, f"{count} registro(s)")
        return _cache_set(cache_key, result) if ttl > 0 else result
    except requests.RequestException as exc:
        _set_status("api_football", False, f"Falha de rede: {exc.__class__.__name__}")
        return None
    except (ValueError, TypeError):
        _set_status("api_football", False, "Resposta inválida")
        return None



_API_LOCK = threading.RLock()
_QUOTA = None


def _api_get(path, params=None, *, ttl=0, api_key=None):
    global _QUOTA
    key = (api_key or _resolve_football_api_key()).strip()
    if not key:
        _set_status('api_football', False, 'Chave não configurada')
        return None
    digest = hashlib.sha256(key.encode()).hexdigest()
    params = {k: v for k, v in (params or {}).items() if v is not None and v != ''}
    cache_key = f"api|{path}|{sorted(params.items())}|{digest}"
    with _API_LOCK:
        cached = _cache_get(cache_key, ttl) if ttl else None
        if cached is not None:
            # Preserve quota/degraded status even when older successful data is cached.
            if _PROVIDER_STATUS['api_football'].get('ok') is not False:
                _set_status('api_football', True, 'Dados em cache dentro da validade')
            return cached
        if _QUOTA is None:
            _QUOTA = QuotaGuard(Path(secret('BETAI_CACHE_DIR', '.cache')) / 'quota.sqlite')
        try:
            limit = max(1, int(secret('FOOTBALL_DAILY_BUDGET', '90')))
        except ValueError:
            limit = 90
        allowed, reason = _QUOTA.reserve(digest, limit)
        if not allowed:
            _set_status('api_football', False, reason)
            return None
        result = _api_get_raw(path, params, ttl=ttl, api_key=key)
        if result is None:
            reason = _PROVIDER_STATUS['api_football']['message']
            low = reason.lower()
            if 'diário' in low or 'quota' in low:
                now = datetime.now(timezone.utc)
                seconds = ((now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - now).total_seconds()
            else:
                seconds = 60 if '429' in low else 300
            _QUOTA.block(digest, seconds, reason)
        return result


def data_observed_at(value):
    for created, cached in list(_CACHE.values()):
        if cached is value:
            return datetime.fromtimestamp(created, timezone.utc).isoformat()
    return None


def source_label(state):
    message = str(state.get('message', '')).lower()
    if any(t in message for t in ('diário', 'cota', 'quota')) and state.get('ok') is False:
        return 'Cota esgotada'
    if state.get('ok') is True and 'com falha' not in message:
        return 'Operacional'
    return 'Degradada' if state.get('ok') is not None else 'Não verificada'


def fixtures_on_date(league_id, day):
    # Include both UTC dates that can overlap a Brasília calendar day.
    start = datetime.combine(day, datetime.min.time(), ZoneInfo(APP_TIMEZONE))
    matches = _fetch_espn_fixtures(league_id, date_from=start, date_to=start + timedelta(days=1), ttl=120)
    ok = _PROVIDER_STATUS['espn'].get('ok') is True
    if not ok:
        matches = _api_get('fixtures', {'league': league_id, 'date': day.isoformat(), 'timezone': APP_TIMEZONE}, ttl=120)
        ok = matches is not None
    selected = []
    for match in matches or []:
        try:
            date = datetime.fromisoformat(match['fixture']['date'].replace('Z', '+00:00'))
            if date.tzinfo and date.astimezone(ZoneInfo(APP_TIMEZONE)).date() == day:
                selected.append(match)
        except (ValueError, KeyError, TypeError):
            continue
    return selected, ok


def player_leaders(league_id, season, metric='goals'):
    endpoint = 'players/topscorers' if metric == 'goals' else 'players/topassists'
    result = _api_get(endpoint, {'league': league_id, 'season': season}, ttl=3600)
    if result is None:
        return [], False, None
    rows = []
    for item in result:
        player = item.get('player') or {}
        for stats in item.get('statistics') or []:
            league = stats.get('league') or {}
            if league.get('id') != league_id or league.get('season') != season:
                continue
            goals = stats.get('goals') or {}
            rows.append({'player': player, 'team': (stats.get('team') or {}).get('name'),
                         'goals': goals.get('total'), 'assists': goals.get('assists'),
                         'season': season, 'source': 'API-Football'})
    field = 'goals' if metric == 'goals' else 'assists'
    rows.sort(key=lambda r: r[field] if isinstance(r[field], (int, float)) else -1, reverse=True)
    return rows, True, data_observed_at(result)


def _espn_get(slug: str, resource: str, *, params: Optional[Dict[str, Any]] = None,
              ttl: int = 60, standings: bool = False) -> Optional[Dict[str, Any]]:
    base = ESPN_STANDINGS_BASE_URL if standings else ESPN_BASE_URL
    cache_key = f"espn|{slug}|{resource}|{sorted((params or {}).items())}|{standings}"
    cached = _cache_get(cache_key, ttl)
    if cached is not None:
        _set_status("espn", True, f"{slug} disponível (cache)")
        return cached
    failure = _ESPN_FAILURES.get(cache_key)
    if failure and failure[0] > time.time():
        _set_status('espn', False, failure[1])
        return None
    try:
        response = _SESSION.get(f"{base}/{slug}/{resource.lstrip('/')}", params=params or {}, timeout=10)
        if response.status_code != 200:
            message = f"HTTP {response.status_code} em {slug}"
            _set_status("espn", False, message)
            _ESPN_FAILURES[cache_key] = (time.time() + 120, message)
            return None
        payload = response.json()
        _set_status("espn", True, f"{slug} atualizado")
        return _cache_set(cache_key, payload)
    except requests.RequestException as exc:
        message = f"Falha de rede: {exc.__class__.__name__}"
        _set_status("espn", False, message)
        _ESPN_FAILURES[cache_key] = (time.time() + 120, message)
        return None
    except (ValueError, TypeError):
        _set_status("espn", False, "Resposta inválida")
        return None


def get_api_football_account_status(api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = _api_get("status", ttl=6 * 3600, api_key=api_key)
    return result if isinstance(result, dict) else None


def api_daily_quota() -> Optional[Tuple[int, int]]:
    status = get_api_football_account_status()
    if not status:
        return None
    req = status.get("requests") or {}
    try:
        return int(req.get("current") or 0), int(req.get("limit_day") or 0)
    except (TypeError, ValueError):
        return None


def _local_date() -> str:
    return now_local().strftime("%Y-%m-%d")


def _league_name(league_id: int) -> str:
    return next((name for name, value in API_FOOTBALL_LEAGUES.items() if value == league_id), str(league_id))


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _score(obj: Dict[str, Any]) -> int:
    try:
        value = obj.get("score")
        return int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _format_espn_event(event: Dict[str, Any], comp: Dict[str, Any], status: Dict[str, Any], slug: str) -> Dict[str, Any]:
    competitors = comp.get("competitors") or []
    home = next((x for x in competitors if x.get("homeAway") == "home"), {})
    away = next((x for x in competitors if x.get("homeAway") == "away"), {})
    home_team, away_team = home.get("team") or {}, away.get("team") or {}
    status_type = status.get("type") or {}
    state = str(status_type.get("state") or "pre").lower()
    clock = status.get("displayClock") or ""
    numbers = re.findall(r"\d+", clock)
    elapsed = int(numbers[0]) if numbers and state == "in" else None
    short = "LIVE" if state == "in" else ("FT" if status_type.get("completed") is True else "NS")
    description = str(status_type.get('description') or '').lower()
    if 'postpon' in description: short = 'PST'
    elif 'cancel' in description: short = 'CANC'
    elif 'abandon' in description: short = 'ABD'
    elif 'suspend' in description: short = 'SUSP'
    elif status_type.get('completed') and any(t in description for t in ('penalt', 'shootout', 'extra')):
        short = 'PEN' if any(t in description for t in ('penalt', 'shootout')) else 'AET'

    reverse_ids = {v: k for k, v in LEAGUE_TO_ESPN_SLUG.items()}
    league_id = reverse_ids.get(slug)
    country_map = {
        "bra.1": "Brasil", "eng.1": "Inglaterra", "esp.1": "Espanha",
        "ita.1": "Itália", "ger.1": "Alemanha", "fra.1": "França",
        "conmebol.libertadores": "América do Sul", "conmebol.sudamericana": "América do Sul",
        "uefa.champions": "Europa",
    }

    return {
        "fixture": {
            "id": _safe_int(event.get("id")) or 0,
            "date": event.get("date") or "",
            "status": {
                "long": status_type.get("description") or status_type.get("detail") or "",
                "short": short,
                "elapsed": elapsed,
            },
            "source": "ESPN",
            "espn_slug": slug,
            "espn_event_id": str(event.get("id") or ""),
        },
        "league": {
            "id": league_id,
            "name": _league_name(league_id) if league_id else slug,
            "country": country_map.get(slug, ""),
        },
        "teams": {
            "home": {
                "id": _safe_int(home_team.get("id")),
                "name": home_team.get("displayName") or home_team.get("name") or "Mandante",
                "logo": home_team.get("logo") or "",
            },
            "away": {
                "id": _safe_int(away_team.get("id")),
                "name": away_team.get("displayName") or away_team.get("name") or "Visitante",
                "logo": away_team.get("logo") or "",
            },
        },
        "goals": {"home": _score(home) if short != "NS" else None, "away": _score(away) if short != "NS" else None},
        "events": [], "statistics": [], "lineups": [], "players": [],
    }


def _fetch_espn_fixtures(league_id: Optional[int] = None, *, live_only: bool = False,
                         date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
                         ttl: Optional[int] = None) -> List[Dict[str, Any]]:
    if league_id is not None:
        slug = LEAGUE_TO_ESPN_SLUG.get(league_id)
        slugs = [slug] if slug else []
    else:
        slugs = list(dict.fromkeys(LEAGUE_TO_ESPN_SLUG.values()))

    start = date_from or now_local()
    end = date_to or start
    date_param = start.strftime("%Y%m%d") if start.date() == end.date() else f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    results: List[Dict[str, Any]] = []
    effective_ttl = ttl if ttl is not None else (15 if live_only else 60)
    attempted = len(slugs)
    successful = 0
    failures: List[str] = []

    for slug in slugs:
        payload = _espn_get(slug, "scoreboard", params={"dates": date_param, "limit": 200}, ttl=effective_ttl)
        if payload is None:
            failures.append(f"{slug}: {_PROVIDER_STATUS['espn'].get('message')}")
            continue
        successful += 1
        for event in payload.get("events", []) or []:
            comp = (event.get("competitions") or [{}])[0]
            status = comp.get("status") or event.get("status") or {}
            state = str(((status.get("type") or {}).get("state") or "pre")).lower()
            if live_only and state != "in":
                continue
            results.append(_format_espn_event(event, comp, status, slug))

    # Estado agregado: uma liga com falha não deve apagar várias consultas ESPN bem-sucedidas.
    if successful > 0:
        suffix = f"; {len(failures)} liga(s) com falha" if failures else ""
        _set_status("espn", True, f"{successful}/{attempted} competição(ões) consultada(s){suffix}")
    elif attempted > 0:
        _set_status("espn", False, "ESPN indisponível. " + "; ".join(failures[:2]))
    else:
        _set_status("espn", False, "Competição sem cobertura ESPN configurada.")
    return results


def get_realtime_live_fixtures(league_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Feed curto para Streamlit: ESPN primeiro, sem consumir quota paga.

    Se a ESPN não responder, tenta API-Football. Isso permite polling de 15 s no
    placar sem destruir o limite diário de uma conta gratuita da API-Football.
    """
    espn = _fetch_espn_fixtures(league_id, live_only=True, ttl=15)
    # Lista vazia pode significar apenas "nenhum jogo ao vivo". Só consumimos
    # API-Football como fallback quando a consulta ESPN realmente falhou.
    if espn or _PROVIDER_STATUS["espn"].get("ok") is True:
        return espn
    return get_api_football_live_fixtures(league_id)


def get_api_football_live_fixtures(league_id: Optional[int] = None,
                                   api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"live": "all", "timezone": APP_TIMEZONE}
    if league_id:
        params["league"] = league_id
    result = _api_get("fixtures", params, ttl=30, api_key=api_key)
    if result is not None:
        return result
    return _fetch_espn_fixtures(league_id, live_only=True, ttl=15)


def get_api_football_all_live(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    return get_api_football_live_fixtures(None, api_key=api_key)


def get_api_football_today_fixtures(league_id: Optional[int] = None,
                                    api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    # Calendário/placar usa ESPN primeiro para preservar quota.
    espn = _fetch_espn_fixtures(league_id, live_only=False, ttl=60)
    # Se a ESPN respondeu corretamente com lista vazia, significa simplesmente
    # que não há partida hoje. Não gastamos uma chamada paga para confirmar.
    if espn or _PROVIDER_STATUS["espn"].get("ok") is True:
        return espn
    params: Dict[str, Any] = {"date": _local_date(), "timezone": APP_TIMEZONE}
    if league_id:
        params["league"] = league_id
    return _api_get("fixtures", params, ttl=120, api_key=api_key) or []


def get_api_football_fixtures_by_league(league_id: int, season: Optional[int] = None,
                                        next_games: int = 20, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    # Próximos jogos via ESPN dispensam quota e não misturam histórico.
    today = now_local()
    espn = _fetch_espn_fixtures(league_id, date_from=today, date_to=today + timedelta(days=45), ttl=300)
    upcoming = [fx for fx in espn if (fx.get("fixture") or {}).get("status", {}).get("short") != "FT"]
    if upcoming:
        upcoming.sort(key=lambda x: (x.get("fixture") or {}).get("date") or "")
        return upcoming[:next_games]

    year = season if season is not None else current_season(league_id)
    params = {"league": league_id, "season": year, "next": next_games, "timezone": APP_TIMEZONE}
    return _api_get("fixtures", params, ttl=300, api_key=api_key) or []



def get_analysis_fixtures(league_id: int, season: Optional[int] = None,
                          next_games: int = 20, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Próximas fixtures para o modelo, preferindo IDs da API-Football.

    O modelo de estatísticas e odds precisa que os IDs de fixture/time estejam
    no mesmo namespace da API-Football. Por isso esta função não usa ESPN
    primeiro. Se a API não estiver disponível, retorna o calendário ESPN apenas
    para exibição; o app identifica a fonte e não calcula o modelo com IDs ESPN.
    """
    year = season if season is not None else current_season(league_id)
    params = {"league": league_id, "season": year, "next": next_games, "timezone": APP_TIMEZONE}
    result = _api_get("fixtures", params, ttl=300, api_key=api_key)
    if result:
        return result
    return get_api_football_fixtures_by_league(league_id, season=year, next_games=next_games, api_key=api_key)

def _normalize_espn_team(item: Dict[str, Any], league_id: int) -> Optional[Dict[str, Any]]:
    team = item.get("team") if isinstance(item.get("team"), dict) else item
    if not isinstance(team, dict) or not team.get("id"):
        return None
    logos = team.get("logos") or []
    logo = team.get("logo") or (logos[0].get("href") if logos and isinstance(logos[0], dict) else "")
    return {
        "team": {
            "id": _safe_int(team.get("id")),
            "name": team.get("displayName") or team.get("name") or "Equipe",
            "code": team.get("abbreviation") or "",
            "country": team.get("location") or "",
            "founded": None,
            "logo": logo or "",
            "source": "ESPN",
            "espn_slug": LEAGUE_TO_ESPN_SLUG.get(league_id),
        },
        "venue": {},
    }


def _espn_teams(league_id: int) -> List[Dict[str, Any]]:
    slug = LEAGUE_TO_ESPN_SLUG.get(league_id)
    if not slug:
        return []
    payload = _espn_get(slug, "teams", ttl=6 * 3600)
    if not payload:
        return []
    raw: Iterable[Dict[str, Any]] = []
    sports = payload.get("sports") or []
    if sports:
        leagues = sports[0].get("leagues") or []
        if leagues:
            raw = leagues[0].get("teams") or []
    if not raw:
        raw = payload.get("teams") or []
    result = []
    for item in raw:
        normalized = _normalize_espn_team(item, league_id)
        if normalized:
            result.append(normalized)
    return result


def get_api_football_teams(league_id: int, season: Optional[int] = None,
                           api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    year = season if season is not None else current_season(league_id)
    result = _api_get("teams", {"league": league_id, "season": year}, ttl=6 * 3600, api_key=api_key)
    if result:
        for row in result:
            if isinstance(row, dict) and isinstance(row.get("team"), dict):
                row["team"].setdefault("source", "API-Football")
        return result
    return _espn_teams(league_id)


def _position_name(value: Any) -> str:
    text = str(value or "").lower()
    if any(x in text for x in ("goal", "gole", "keeper", "gk")):
        return "Goalkeeper"
    if any(x in text for x in ("def", "back", "zague", "lateral")):
        return "Defender"
    if any(x in text for x in ("mid", "meia", "volante")):
        return "Midfielder"
    if any(x in text for x in ("att", "forward", "wing", "striker", "atac", "ponta")):
        return "Attacker"
    return str(value or "Other")


def _flatten_espn_roster(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    athletes = payload.get("athletes") or []
    flat: List[Dict[str, Any]] = []
    for group in athletes:
        if not isinstance(group, dict):
            continue
        items = group.get("items")
        if isinstance(items, list):
            group_pos = group.get("position") or group.get("name") or group.get("displayName")
            for athlete in items:
                if isinstance(athlete, dict):
                    athlete = dict(athlete)
                    athlete.setdefault("_group_position", group_pos)
                    flat.append(athlete)
        else:
            flat.append(group)
    return flat


def _espn_squad(team_id: int, league_id: int) -> List[Dict[str, Any]]:
    slug = LEAGUE_TO_ESPN_SLUG.get(league_id)
    if not slug:
        return []
    payload = _espn_get(slug, f"teams/{team_id}/roster", ttl=6 * 3600)
    if not payload:
        return []
    season_meta = payload.get('season') or {}
    if not isinstance(season_meta, dict) or season_meta.get('year') != current_season(league_id):
        _set_status('espn', False, 'Temporada do elenco não confirmada')
        return []
    players = []
    for athlete in _flatten_espn_roster(payload):
        pos = athlete.get("position") or {}
        pos_value = pos.get("name") or pos.get("displayName") or pos.get("abbreviation") if isinstance(pos, dict) else pos
        if not pos_value:
            pos_value = athlete.get("_group_position")
        headshot = athlete.get("headshot") or {}
        players.append({
            "id": _safe_int(athlete.get("id")),
            "name": athlete.get("fullName") or athlete.get("displayName") or athlete.get("shortName") or "Jogador",
            "age": athlete.get("age"),
            "number": athlete.get("jersey"),
            "position": _position_name(pos_value),
            "photo": headshot.get("href") if isinstance(headshot, dict) else "",
            "source": "ESPN",
        })
    return players


def get_api_football_squad(team_id: int, api_key: Optional[str] = None,
                           allow_stale_fallback: bool = False, league_id: Optional[int] = None,
                           source_hint: Optional[str] = None) -> List[Dict[str, Any]]:
    """Elenco atual. Nunca usa snapshot/CSV local.

    Se o time veio da ESPN, usa o roster ESPN. Se veio da API-Football, usa
    ``players/squads``. Em falha, tenta a outra fonte apenas quando o ID é
    compatível/conhecido.
    """
    if str(source_hint or "").upper() == "ESPN" and league_id:
        espn = _espn_squad(team_id, league_id)
        return espn

    result = _api_get("players/squads", {"team": team_id}, ttl=6 * 3600, api_key=api_key)
    if result:
        players = result[0].get("players", []) if result else []
        for p in players:
            if isinstance(p, dict):
                p.setdefault("source", "API-Football")
        return players

    # IDs de time da API-Football e da ESPN pertencem a namespaces distintos.
    # Nunca tentamos um ID API-Football diretamente no endpoint ESPN, pois um
    # número coincidente poderia apontar para outro clube.
    return []


def get_api_football_fixture_details(fixture_id: int, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = _api_get("fixtures", {"id": fixture_id, "timezone": APP_TIMEZONE}, ttl=60, api_key=api_key)
    return result[0] if result else None


def get_api_football_fixture_events(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "events" in detail:
        return detail.get("events") or []
    return _api_get("fixtures/events", {"fixture": fixture_id}, ttl=60, api_key=api_key) or []


def get_api_football_fixture_statistics(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "statistics" in detail:
        return detail.get("statistics") or []
    return _api_get("fixtures/statistics", {"fixture": fixture_id}, ttl=90, api_key=api_key) or []


def get_api_football_fixture_lineups(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "lineups" in detail:
        return detail.get("lineups") or []
    return _api_get("fixtures/lineups", {"fixture": fixture_id}, ttl=300, api_key=api_key) or []


def get_api_football_fixture_players(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    detail = get_api_football_fixture_details(fixture_id, api_key=api_key)
    if detail is not None and "players" in detail:
        return detail.get("players") or []
    return _api_get("fixtures/players", {"fixture": fixture_id}, ttl=90, api_key=api_key) or []


def _normalize_espn_summary_event(item: Dict[str, Any]) -> Dict[str, Any]:
    clock = item.get("clock") or {}
    display = clock.get("displayValue") or item.get("time") or ""
    nums = re.findall(r"\d+", str(display))
    minute = int(nums[0]) if nums else None
    typ = item.get("type") or {}
    if isinstance(typ, dict):
        typ_text = typ.get("text") or typ.get("description") or typ.get("name") or "Evento"
    else:
        typ_text = str(typ or "Evento")
    team = item.get("team") or {}
    return {
        "time": {"elapsed": minute, "extra": None},
        "type": typ_text,
        "detail": item.get("text") or item.get("shortText") or typ_text,
        "team": {"name": team.get("displayName") or team.get("name") or ""} if isinstance(team, dict) else {"name": ""},
        "player": {"name": ""},
        "assist": {"name": ""},
    }


def get_espn_fixture_bundle(fixture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    f = fixture.get("fixture") or {}
    slug = f.get("espn_slug")
    event_id = f.get("espn_event_id") or f.get("id")
    if not slug or not event_id:
        return None
    payload = _espn_get(str(slug), "summary", params={"event": str(event_id)}, ttl=30)
    if not payload:
        return None

    raw_events = payload.get("keyEvents") or payload.get("plays") or []
    events = [_normalize_espn_summary_event(x) for x in raw_events if isinstance(x, dict)]

    stats: List[Dict[str, Any]] = []
    boxscore = payload.get("boxscore") or {}
    for block in boxscore.get("teams", []) or []:
        team = block.get("team") or {}
        values = []
        for stat in block.get("statistics", []) or []:
            values.append({
                "type": stat.get("label") or stat.get("displayName") or stat.get("name") or "Métrica",
                "value": stat.get("displayValue") if stat.get("displayValue") is not None else stat.get("value"),
            })
        stats.append({"team": {"name": team.get("displayName") or team.get("name") or "Equipe"}, "statistics": values})

    lineups: List[Dict[str, Any]] = []
    players: List[Dict[str, Any]] = []
    for roster in payload.get("rosters", []) or []:
        team = roster.get("team") or {}
        team_name = team.get("displayName") or team.get("name") or "Equipe"
        start_xi = []
        player_rows = []
        for entry in roster.get("roster", []) or roster.get("athletes", []) or []:
            athlete = entry.get("athlete") if isinstance(entry.get("athlete"), dict) else entry
            if not isinstance(athlete, dict):
                continue
            position = athlete.get("position") or entry.get("position") or {}
            pos_text = position.get("abbreviation") or position.get("displayName") or position.get("name") if isinstance(position, dict) else position
            player = {
                "id": _safe_int(athlete.get("id")),
                "name": athlete.get("displayName") or athlete.get("fullName") or athlete.get("shortName") or "Jogador",
                "number": athlete.get("jersey") or entry.get("jersey"),
                "pos": str(pos_text or ""),
                "starter": bool(entry.get("starter")),
            }
            if entry.get("starter") is True:
                start_xi.append({"player": player})
            player_rows.append({"player": player, "statistics": []})
        if start_xi:
            lineups.append({"team": {"name": team_name}, "formation": None, "coach": {}, "startXI": start_xi})
        if player_rows:
            players.append({"team": {"name": team_name}, "players": player_rows})

    return {
        "source": "ESPN",
        "events": events,
        "statistics": stats,
        "lineups": lineups,
        "players": players,
    }


def get_fixture_bundle(fixture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Obtém os detalhes da partida preservando o namespace correto do ID."""
    f = fixture.get("fixture") or {}
    if str(f.get("source") or "").upper() == "ESPN":
        return get_espn_fixture_bundle(fixture)

    fixture_id = _safe_int(f.get("id"))
    if not fixture_id:
        return None
    detail = get_api_football_fixture_details(fixture_id)
    if not detail:
        return None
    return {
        "source": "API-Football",
        "events": detail.get("events") or [],
        "statistics": detail.get("statistics") or [],
        "lineups": detail.get("lineups") or [],
        "players": detail.get("players") or [],
    }


def _espn_standings(league_id: int) -> List[List[Dict[str, Any]]]:
    slug = LEAGUE_TO_ESPN_SLUG.get(league_id)
    if not slug:
        return []
    payload = _espn_get(slug, "standings", params={"season": current_season(league_id)}, ttl=600, standings=True)
    if not payload:
        return []

    season_meta = payload.get('season') or {}
    if not isinstance(season_meta, dict) or season_meta.get('year') != current_season(league_id):
        _set_status('espn', False, 'Temporada da tabela não confirmada; fallback necessário')
        return []
    groups = payload.get("children") or [payload]
    normalized_groups: List[List[Dict[str, Any]]] = []
    for group in groups:
        standings = group.get("standings") or {}
        entries = standings.get("entries") or group.get("entries") or []
        rows = []
        for index, entry in enumerate(entries, start=1):
            team = entry.get("team") or {}
            stat_lookup = {}
            for stat in entry.get("stats", []) or []:
                key = stat.get("name") or stat.get("abbreviation") or stat.get("displayName")
                if key:
                    stat_lookup[str(key).lower()] = stat.get("value") if stat.get("value") is not None else stat.get("displayValue")

            def pick(*keys: str, default: Any = None) -> Any:
                for key in keys:
                    if key.lower() in stat_lookup:
                        return stat_lookup[key.lower()]
                return default

            rank = pick("rank", default=index)
            rows.append({
                "rank": _safe_int(rank) or index,
                "team": {"name": team.get("displayName") or team.get("name") or "Equipe"},
                "all": {
                    "played": pick("gamesPlayed", "games", "gp"),
                    "win": pick("wins", "w"),
                    "draw": pick("ties", "draws", "d"),
                    "lose": pick("losses", "l"),
                    "goals": {"for": pick("pointsFor", "goalsFor", "gf"), "against": pick("pointsAgainst", "goalsAgainst", "ga")},
                },
                "goalsDiff": pick("pointDifferential", "goalDifference", "gd"),
                "points": pick("points", "pts"),
                "form": pick("streak", "form", default="—"),
            })
        if rows:
            normalized_groups.append(rows)
    return normalized_groups


def get_api_football_standings(league_id: int, season: Optional[int] = None,
                               api_key: Optional[str] = None) -> List[List[Dict[str, Any]]]:
    espn = _espn_standings(league_id)
    if espn:
        return espn
    year = season if season is not None else current_season(league_id)
    result = _api_get("standings", {"league": league_id, "season": year}, ttl=600, api_key=api_key) or []
    if not result:
        return []
    league = result[0].get("league") or {}
    return (league.get("standings") or []) if league.get("id") == league_id and league.get("season") == year else []


def get_api_football_team_statistics(league_id: int, team_id: int, season: Optional[int] = None,
                                     api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    year = season if season is not None else current_season(league_id)
    result = _api_get("teams/statistics", {"league": league_id, "season": year, "team": team_id}, ttl=900, api_key=api_key)
    if isinstance(result, dict):
        return result
    return result[0] if isinstance(result, list) and result else None


def get_api_football_odds(fixture_id: int, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    return _api_get("odds", {"fixture": fixture_id}, ttl=300, api_key=api_key) or []


def get_api_football_predictions(fixture_id: int, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    result = _api_get("predictions", {"fixture": fixture_id}, ttl=1800, api_key=api_key)
    return result[0] if result else None
