"""
Cliente da API-Football (https://www.api-football.com/) para o BetAI Quant Pro.

Regras seguidas neste módulo (requisitos do projeto):
- Nunca mostra dados históricos como se fossem atuais.
- Nunca usa listas hardcoded de jogadores/times.
- Se a API falhar, timeout ou faltar API key, retorna dados vazios com uma
  mensagem de erro clara em vez de inventar dados. A camada de UI decide
  como exibir "não disponível".
- Cache em camadas, com TTLs diferentes por tipo de dado:
    * jogos AO VIVO        -> TTL curto (30s)
    * próximos jogos       -> TTL médio (5 min)
    * elencos / times      -> TTL longo (12h)
    * estatísticas de time -> TTL médio (30 min)
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import requests

logger = logging.getLogger("betai.sports_data_api")

API_BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TIMEOUT = 10  # segundos


class SportsDataAPIError(Exception):
    """Erro genérico ao consultar a API esportiva (timeout, rate limit, etc.)."""


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class _TTLCache:
    """Cache simples em memória, por chave, com TTL individual por entrada."""

    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._store[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl_seconds)

    def clear(self) -> None:
        self._store.clear()


# TTLs por tipo de dado (em segundos)
TTL_LIVE = 30
TTL_UPCOMING = 5 * 60
TTL_TEAM_STATS = 30 * 60
TTL_SQUAD = 12 * 60 * 60
TTL_LEAGUES = 24 * 60 * 60


class SportsDataAPI:
    """
    Wrapper fino sobre a API-Football.

    Uso:
        api = SportsDataAPI(api_key="SUA_CHAVE")
        jogos = api.get_live_fixtures()
    """

    def __init__(self, api_key: str | None, base_url: str = API_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._cache = _TTLCache()
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # Infra interna
    # ------------------------------------------------------------------ #

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "x-apisports-key": self.api_key or "",
        }

    def _get(self, path: str, params: dict | None = None, *, cache_key: str | None = None,
              ttl: float = 0) -> dict:
        """
        Faz GET na API com cache opcional. Levanta SportsDataAPIError em
        qualquer falha (timeout, rate limit, HTTP erro, API key ausente).
        Nunca retorna dados inventados.
        """
        if not self.is_configured():
            raise SportsDataAPIError("API key da API-Football não configurada.")

        if cache_key is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, headers=self._headers(), params=params, timeout=self.timeout)
        except requests.Timeout as exc:
            raise SportsDataAPIError(f"Timeout ao consultar {path}.") from exc
        except requests.RequestException as exc:
            raise SportsDataAPIError(f"Erro de rede ao consultar {path}: {exc}") from exc

        if resp.status_code == 429:
            raise SportsDataAPIError("Rate limit da API-Football atingido. Tente novamente em instantes.")
        if resp.status_code == 401:
            raise SportsDataAPIError("API key inválida ou expirada.")
        if not resp.ok:
            raise SportsDataAPIError(f"API retornou HTTP {resp.status_code} em {path}.")

        try:
            data = resp.json()
        except ValueError as exc:
            raise SportsDataAPIError("Resposta da API não é um JSON válido.") from exc

        # A API-Football embrulha erros dentro de um campo "errors"
        errors = data.get("errors")
        if errors:
            raise SportsDataAPIError(f"API-Football retornou erro: {errors}")

        if cache_key is not None:
            self._cache.set(cache_key, data, ttl)

        return data

    # ------------------------------------------------------------------ #
    # Jogos ao vivo
    # ------------------------------------------------------------------ #

    def get_live_fixtures(self, league_id: int | None = None) -> list[dict]:
        """Retorna os jogos AO VIVO agora. TTL curto — nunca serve cache velho como live."""
        params: dict[str, Any] = {"live": "all"}
        if league_id:
            params["league"] = league_id
        cache_key = f"live:{league_id}"
        data = self._get("/fixtures", params=params, cache_key=cache_key, ttl=TTL_LIVE)
        return data.get("response", [])

    # ------------------------------------------------------------------ #
    # Próximos jogos / jogos do dia
    # ------------------------------------------------------------------ #

    def get_fixtures_by_date(self, day: date, league_id: int | None = None) -> list[dict]:
        """
        Jogos de uma data específica. Se `day` for hoje ou no futuro, isso é
        tratado como "próximo jogo" pela UI — nunca como histórico.
        """
        params: dict[str, Any] = {"date": day.isoformat()}
        if league_id:
            params["league"] = league_id
        cache_key = f"fixtures:{day.isoformat()}:{league_id}"
        data = self._get("/fixtures", params=params, cache_key=cache_key, ttl=TTL_UPCOMING)
        return data.get("response", [])

    def get_upcoming_fixtures(self, league_id: int, season: int, next_n: int = 10) -> list[dict]:
        """Próximos N jogos futuros de uma liga/temporada."""
        params = {"league": league_id, "season": season, "next": next_n}
        cache_key = f"upcoming:{league_id}:{season}:{next_n}"
        data = self._get("/fixtures", params=params, cache_key=cache_key, ttl=TTL_UPCOMING)
        return data.get("response", [])

    # ------------------------------------------------------------------ #
    # Times, elencos e estatísticas (histórico usado só para alimentar o modelo)
    # ------------------------------------------------------------------ #

    def get_leagues(self, country: str | None = None) -> list[dict]:
        params = {"country": country} if country else {}
        cache_key = f"leagues:{country}"
        data = self._get("/leagues", params=params, cache_key=cache_key, ttl=TTL_LEAGUES)
        return data.get("response", [])

    def get_team_squad(self, team_id: int) -> list[dict]:
        """Elenco ATUAL do time, conforme a API. Cache longo (muda pouco)."""
        cache_key = f"squad:{team_id}"
        data = self._get("/players/squads", params={"team": team_id}, cache_key=cache_key, ttl=TTL_SQUAD)
        response = data.get("response", [])
        if not response:
            return []
        return response[0].get("players", [])

    def get_team_statistics(self, team_id: int, league_id: int, season: int) -> dict | None:
        """
        Estatísticas agregadas do time na temporada (usadas para alimentar o
        modelo estatístico de previsão — não são exibidas como "jogo atual").
        """
        cache_key = f"team_stats:{team_id}:{league_id}:{season}"
        params = {"team": team_id, "league": league_id, "season": season}
        data = self._get("/teams/statistics", params=params, cache_key=cache_key, ttl=TTL_TEAM_STATS)
        response = data.get("response")
        return response or None

    def get_head_to_head(self, team1_id: int, team2_id: int, last_n: int = 10) -> list[dict]:
        """Histórico de confrontos diretos — usado só como insumo estatístico."""
        cache_key = f"h2h:{team1_id}:{team2_id}:{last_n}"
        params = {"h2h": f"{team1_id}-{team2_id}", "last": last_n}
        data = self._get("/fixtures/headtohead", params=params, cache_key=cache_key, ttl=TTL_TEAM_STATS)
        return data.get("response", [])

    def get_odds(self, fixture_id: int) -> list[dict]:
        cache_key = f"odds:{fixture_id}"
        data = self._get("/odds", params={"fixture": fixture_id}, cache_key=cache_key, ttl=TTL_UPCOMING)
        return data.get("response", [])


def fixture_kickoff_utc(fixture: dict) -> datetime | None:
    """Extrai o horário do jogo (UTC) de um objeto fixture da API-Football."""
    iso = fixture.get("fixture", {}).get("date")
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
