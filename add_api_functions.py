"""Adiciona as novas funções de API ao sports_data_api.py"""
import datetime

CODE_TO_APPEND = '''

# ============================================================
# NOVAS FUNÇÕES PARA REFORMA ESTILO BETANO (Adicionadas automaticamente)
# ============================================================
import datetime as _dt
import streamlit as st

@st.cache_data(ttl=3600, show_spinner=False)
def get_api_football_yesterday_fixtures(league_id=None, api_key=None):
    """Busca jogos finalizados de ontem."""
    key = api_key or FOOTBALL_API_KEY
    if not key:
        return []
    yesterday = (_dt.datetime.now() - _dt.timedelta(days=1)).strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": key}
    params = {"date": yesterday, "season": 2026}
    if league_id:
        params["league"] = league_id
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        return resp.json().get("response", [])
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def get_api_football_fixture_lineups(fixture_id, api_key=None):
    """Busca escalações oficiais de uma partida."""
    key = api_key or FOOTBALL_API_KEY
    if not key:
        return []
    url = "https://v3.football.api-sports.io/fixtures/lineups"
    headers = {"x-apisports-key": key}
    params = {"fixture": fixture_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        return resp.json().get("response", [])
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def get_api_football_fixture_odds(fixture_id, api_key=None):
    """Busca odds de casas de apostas para uma partida."""
    key = api_key or FOOTBALL_API_KEY
    if not key:
        return []
    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": key}
    params = {"fixture": fixture_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        return resp.json().get("response", [])
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def get_api_football_fixture_h2h(team1_id, team2_id, api_key=None):
    """Busca confronto direto (H2H) entre dois times."""
    key = api_key or FOOTBALL_API_KEY
    if not key:
        return []
    url = "https://v3.football.api-sports.io/fixtures/headtohead"
    headers = {"x-apisports-key": key}
    params = {"h2h": f"{team1_id}-{team2_id}", "last": 5}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        return resp.json().get("response", [])
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def get_api_football_fixture_players(fixture_id, api_key=None):
    """Busca estatísticas individuais dos jogadores em uma partida."""
    key = api_key or FOOTBALL_API_KEY
    if not key:
        return []
    url = "https://v3.football.api-sports.io/fixtures/players"
    headers = {"x-apisports-key": key}
    params = {"fixture": fixture_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        return resp.json().get("response", [])
    except Exception:
        return []
'''

target = "src/sports_data_api.py"

with open(target, "r", encoding="utf-8") as f:
    existing = f.read()

# Evitar duplicação
if "get_api_football_yesterday_fixtures" not in existing:
    with open(target, "a", encoding="utf-8") as f:
        f.write(CODE_TO_APPEND)
    print("Funções adicionadas com sucesso!")
else:
    print("Funções já existem, nada a fazer.")
