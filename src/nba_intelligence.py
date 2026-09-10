import requests
import datetime
from typing import List, Dict, Any, Optional

NBA_API_KEY = "dab914bb-514e-4217-977e-8a057ab87b42"
NBA_BASE_URL = "https://api.balldontlie.io/v1"
NBA_HEADERS = {"Authorization": NBA_API_KEY}

# Cache em memória para respeitar o limite de 5 req/min do Free Tier da Balldontlie
_NBA_TEAMS_CACHE: List[Dict[str, Any]] = []
_NBA_PLAYERS_CACHE: Dict[int, List[Dict[str, Any]]] = {}
_NBA_GAMES_CACHE: Dict[str, Any] = {"date": None, "data": []}

NBA_TOP_FRANCHISES = [
    {"id": 14, "name": "Los Angeles Lakers", "city": "Los Angeles", "conference": "West", "star": "LeBron James", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png"},
    {"id": 2, "name": "Boston Celtics", "city": "Boston", "conference": "East", "star": "Jayson Tatum", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/bos.png"},
    {"id": 10, "name": "Golden State Warriors", "city": "Golden State", "conference": "West", "star": "Stephen Curry", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/gsw.png"},
    {"id": 17, "name": "Milwaukee Bucks", "city": "Milwaukee", "conference": "East", "star": "Giannis Antetokounmpo", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mil.png"},
    {"id": 8, "name": "Denver Nuggets", "city": "Denver", "conference": "West", "star": "Nikola Jokic", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/den.png"},
    {"id": 16, "name": "Miami Heat", "city": "Miami", "conference": "East", "star": "Jimmy Butler", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mia.png"},
    {"id": 6, "name": "Dallas Mavericks", "city": "Dallas", "conference": "West", "star": "Luka Doncic", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/dal.png"},
    {"id": 24, "name": "Phoenix Suns", "city": "Phoenix", "conference": "West", "star": "Kevin Durant", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png"},
    {"id": 20, "name": "New York Knicks", "city": "New York", "conference": "East", "star": "Jalen Brunson", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/nyk.png"},
    {"id": 23, "name": "Philadelphia 76ers", "city": "Philadelphia", "conference": "East", "star": "Joel Embiid", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/phi.png"},
]

def get_nba_teams() -> List[Dict[str, Any]]:
    """Retorna todas as equipes da NBA, utilizando cache para proteger a cota da API."""
    global _NBA_TEAMS_CACHE
    if _NBA_TEAMS_CACHE:
        return _NBA_TEAMS_CACHE
    try:
        r = requests.get(f"{NBA_BASE_URL}/teams", headers=NBA_HEADERS, timeout=5)
        if r.status_code == 200:
            teams = r.json().get("data", [])
            if teams:
                _NBA_TEAMS_CACHE = teams
                return teams
    except Exception:
        pass
    # Fallback estruturado caso a API atinja rate limit
    return [{"id": f["id"], "full_name": f["name"], "city": f["city"], "conference": f["conference"]} for f in NBA_TOP_FRANCHISES]

def get_nba_players(team_id: int) -> List[Dict[str, Any]]:
    """Retorna jogadores de uma franquia específica com cache local."""
    global _NBA_PLAYERS_CACHE
    if team_id in _NBA_PLAYERS_CACHE:
        return _NBA_PLAYERS_CACHE[team_id]
    try:
        r = requests.get(
            f"{NBA_BASE_URL}/players",
            headers=NBA_HEADERS,
            params={"team_ids[]": team_id, "per_page": 40},
            timeout=5
        )
        if r.status_code == 200:
            players = r.json().get("data", [])
            if players:
                _NBA_PLAYERS_CACHE[team_id] = players
                return players
    except Exception:
        pass
    return []

def get_nba_games_today() -> List[Dict[str, Any]]:
    """Retorna partidas agendadas ou em andamento da NBA."""
    global _NBA_GAMES_CACHE
    hoje = datetime.date.today().isoformat()
    if _NBA_GAMES_CACHE["date"] == hoje and _NBA_GAMES_CACHE["data"]:
        return _NBA_GAMES_CACHE["data"]
    try:
        r = requests.get(
            f"{NBA_BASE_URL}/games",
            headers=NBA_HEADERS,
            params={"dates[]": hoje},
            timeout=5
        )
        if r.status_code == 200:
            games = r.json().get("data", [])
            _NBA_GAMES_CACHE = {"date": hoje, "data": games}
            return games
    except Exception:
        pass
    return []

def get_nba_live_box_scores() -> List[Dict[str, Any]]:
    """Consulta jogos ao vivo da NBA com tratamento de planos da API."""
    try:
        r = requests.get(f"{NBA_BASE_URL}/box_scores/live", headers=NBA_HEADERS, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception:
        pass
    
    # Fallback: verificar em games se há jogos hoje com status de andamento
    today_games = get_nba_games_today()
    live = []
    for g in today_games:
        st_text = str(g.get("status", "")).lower()
        if "in progress" in st_text or "q" in st_text or "half" in st_text:
            live.append(g)
    return live

def calculate_nba_probability(team_home: str, team_away: str) -> Dict[str, Any]:
    """
    Calcula a probabilidade estimada de vitória entre duas franquias NBA
    considerando fator casa (Home Court Advantage ~ +5%) e força relativa.
    """
    ratings = {
        "Boston Celtics": 1.28,
        "Denver Nuggets": 1.24,
        "Milwaukee Bucks": 1.20,
        "Los Angeles Lakers": 1.15,
        "Golden State Warriors": 1.14,
        "Dallas Mavericks": 1.18,
        "Miami Heat": 1.12,
        "Phoenix Suns": 1.13,
        "New York Knicks": 1.15,
        "Philadelphia 76ers": 1.14,
        "Oklahoma City Thunder": 1.22,
        "Minnesota Timberwolves": 1.19
    }
    r_home = ratings.get(team_home, 1.05) * 1.08  # Vantagem de mando de quadra NBA
    r_away = ratings.get(team_away, 1.05)

    prob_home = round((r_home / (r_home + r_away)) * 100)
    prob_away = 100 - prob_home

    fair_odd_home = round(100 / max(1, prob_home), 2)
    fair_odd_away = round(100 / max(1, prob_away), 2)

    return {
        "prob_home": prob_home,
        "prob_away": prob_away,
        "fair_odd_home": fair_odd_home,
        "fair_odd_away": fair_odd_away,
        "favorito": team_home if prob_home >= prob_away else team_away,
        "vantagem": abs(prob_home - prob_away)
    }
