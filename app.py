"""
BetAI Quant Pro — app Streamlit de análise esportiva com dados ao vivo.

Abas:
    1. Ao Vivo         -> jogos acontecendo agora (placar, minuto, eventos)
    2. Próximos Jogos   -> jogos futuros de uma liga
    3. Análise & Previsões -> estatísticas reais + modelo de previsão

Regras seguidas:
    - Nunca mostra dado histórico como se fosse atual.
    - Nunca usa listas hardcoded de jogadores/times.
    - Sempre exibe "não disponível" em vez de inventar dado quando a API falha.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from src.sports_data_api import SportsDataAPI, SportsDataAPIError, fixture_kickoff_utc
from src.predictions import predict_match

st.set_page_config(page_title="BetAI Quant Pro", page_icon="⚽", layout="wide")


# --------------------------------------------------------------------------- #
# Configuração / API key
# --------------------------------------------------------------------------- #

def get_api_key() -> str | None:
    """
    Busca a API key na seguinte ordem: st.secrets -> variável de ambiente ->
    campo digitado manualmente na sidebar. Nunca fica hardcoded no código.
    """
    key = None
    try:
        key = st.secrets.get("API_FOOTBALL_KEY")  # type: ignore[attr-defined]
    except Exception:
        key = None
    if not key:
        key = os.environ.get("API_FOOTBALL_KEY")
    return key


@st.cache_resource(show_spinner=False)
def get_api_client(api_key: str | None) -> SportsDataAPI:
    return SportsDataAPI(api_key=api_key)


with st.sidebar:
    st.title("⚽ BetAI Quant Pro")
    st.caption("Análise esportiva e dados ao vivo em tempo real")

    env_key = get_api_key()
    manual_key = st.text_input(
        "API-Football key",
        value="" if env_key else "",
        type="password",
        help="Se não configurada em secrets/variável de ambiente, cole sua chave aqui.",
    )
    api_key = manual_key.strip() or env_key

    st.divider()
    st.markdown("**Liga**")
    # IDs de ligas comuns na API-Football (não são dados de jogo, apenas
    # identificadores de competição — não caracterizam hardcoded de resultados)
    LEAGUES = {
        "Brasileirão Série A": 71,
        "Premier League": 39,
        "La Liga": 140,
        "Serie A (Itália)": 135,
        "Bundesliga": 78,
        "Ligue 1": 61,
        "Champions League": 2,
    }
    league_name = st.selectbox("Selecione a liga", list(LEAGUES.keys()))
    league_id = LEAGUES[league_name]
    season = st.number_input("Temporada", min_value=2015, max_value=2100, value=datetime.now().year, step=1)

    st.divider()
    if not api_key:
        st.warning("Configure sua API key da API-Football para carregar dados.")

api = get_api_client(api_key)

tab_live, tab_upcoming, tab_analysis = st.tabs(["🔴 Ao Vivo", "📅 Próximos Jogos", "📊 Análise & Previsões"])


# --------------------------------------------------------------------------- #
# Helpers de exibição
# --------------------------------------------------------------------------- #

def render_fixture_row(fx: dict) -> None:
    teams = fx.get("teams", {})
    goals = fx.get("goals", {})
    fixture_info = fx.get("fixture", {})
    status = fixture_info.get("status", {})

    home = teams.get("home", {}).get("name", "?")
    away = teams.get("away", {}).get("name", "?")
    home_goals = goals.get("home")
    away_goals = goals.get("away")
    elapsed = status.get("elapsed")
    status_short = status.get("short", "")

    kickoff = fixture_kickoff_utc(fx)
    kickoff_str = kickoff.strftime("%d/%m %H:%M UTC") if kickoff else "horário não disponível"

    cols = st.columns([3, 1, 3, 2])
    cols[0].markdown(f"**{home}**")
    score_display = f"{home_goals if home_goals is not None else '-'} : {away_goals if away_goals is not None else '-'}"
    cols[1].markdown(f"<h4 style='text-align:center'>{score_display}</h4>", unsafe_allow_html=True)
    cols[2].markdown(f"**{away}**")

    if status_short in ("1H", "2H", "ET", "LIVE"):
        cols[3].markdown(f"🔴 {elapsed}' " if elapsed is not None else "🔴 ao vivo")
    elif status_short in ("NS",):
        cols[3].markdown(f"🕒 {kickoff_str}")
    elif status_short in ("FT", "AET", "PEN"):
        cols[3].markdown("✅ Encerrado")
    else:
        cols[3].markdown(status.get("long", status_short) or "—")


# --------------------------------------------------------------------------- #
# Aba: Ao Vivo
# --------------------------------------------------------------------------- #

with tab_live:
    st.subheader("Jogos ao vivo agora")
    if not api.is_configured():
        st.info("Configure a API key na barra lateral para ver jogos ao vivo.")
    else:
        col_a, col_b = st.columns([1, 5])
        with col_a:
            refresh = st.button("🔄 Atualizar", key="refresh_live")
        if refresh:
            st.cache_resource.clear()

        try:
            live_fixtures = api.get_live_fixtures(league_id=league_id)
        except SportsDataAPIError as e:
            st.error(f"Não foi possível carregar jogos ao vivo: {e}")
            live_fixtures = []

        if not live_fixtures:
            st.info("Nenhum jogo ao vivo nesta liga no momento.")
        else:
            for fx in live_fixtures:
                render_fixture_row(fx)
                st.divider()


# --------------------------------------------------------------------------- #
# Aba: Próximos Jogos
# --------------------------------------------------------------------------- #

with tab_upcoming:
    st.subheader(f"Próximos jogos — {league_name}")
    if not api.is_configured():
        st.info("Configure a API key na barra lateral para ver os próximos jogos.")
    else:
        n_games = st.slider("Quantidade de jogos futuros", min_value=5, max_value=30, value=10, key="n_upcoming")
        try:
            upcoming = api.get_upcoming_fixtures(league_id=league_id, season=int(season), next_n=n_games)
        except SportsDataAPIError as e:
            st.error(f"Não foi possível carregar os próximos jogos: {e}")
            upcoming = []

        if not upcoming:
            st.info("Nenhum jogo futuro encontrado para essa liga/temporada.")
        else:
            for fx in upcoming:
                render_fixture_row(fx)
                st.divider()


# --------------------------------------------------------------------------- #
# Aba: Análise & Previsões
# --------------------------------------------------------------------------- #

with tab_analysis:
    st.subheader("Análise estatística e previsão de partida")
    st.caption(
        "Previsão calculada em cima das estatísticas reais da temporada atual "
        "(modelo de Poisson). Jogos históricos são usados apenas para alimentar "
        "o modelo — nunca exibidos como jogo atual."
    )

    if not api.is_configured():
        st.info("Configure a API key na barra lateral para gerar análises.")
    else:
        try:
            candidate_fixtures = api.get_upcoming_fixtures(league_id=league_id, season=int(season), next_n=20)
        except SportsDataAPIError as e:
            st.error(f"Não foi possível carregar os jogos para análise: {e}")
            candidate_fixtures = []

        if not candidate_fixtures:
            st.info("Nenhum jogo futuro disponível para análise nesta liga/temporada.")
        else:
            options = {}
            for fx in candidate_fixtures:
                teams = fx.get("teams", {})
                home = teams.get("home", {}).get("name", "?")
                away = teams.get("away", {}).get("name", "?")
                kickoff = fixture_kickoff_utc(fx)
                label = f"{home} x {away} — {kickoff.strftime('%d/%m %H:%M UTC') if kickoff else 'data não disponível'}"
                options[label] = fx

            chosen_label = st.selectbox("Escolha um jogo futuro", list(options.keys()))
            fx = options[chosen_label]
            teams = fx.get("teams", {})
            home_team = teams.get("home", {})
            away_team = teams.get("away", {})

            if st.button("Gerar análise", type="primary"):
                with st.spinner("Buscando estatísticas reais dos times..."):
                    try:
                        home_stats = api.get_team_statistics(home_team.get("id"), league_id, int(season))
                        away_stats = api.get_team_statistics(away_team.get("id"), league_id, int(season))
                    except SportsDataAPIError as e:
                        st.error(f"Não foi possível carregar estatísticas: {e}")
                        home_stats = away_stats = None

                prediction = predict_match(home_stats, away_stats)

                if prediction is None:
                    st.warning(
                        "Não disponível: estatísticas insuficientes da API para gerar uma "
                        "previsão confiável para este jogo."
                    )
                else:
                    st.markdown(f"### {home_team.get('name')} x {away_team.get('name')}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"Vitória {home_team.get('name')}", f"{prediction.home_win_pct}%")
                    c2.metric("Empate", f"{prediction.draw_pct}%")
                    c3.metric(f"Vitória {away_team.get('name')}", f"{prediction.away_win_pct}%")

                    c4, c5, c6 = st.columns(3)
                    c4.metric("Gols esperados (mandante)", prediction.expected_goals_home)
                    c5.metric("Gols esperados (visitante)", prediction.expected_goals_away)
                    c6.metric("Confiança do modelo", prediction.confidence.capitalize())

                    c7, c8 = st.columns(2)
                    c7.metric("Mais de 2.5 gols", f"{prediction.over_2_5_pct}%")
                    c8.metric("Ambas marcam", f"{prediction.btts_pct}%")

                    st.caption(
                        "Previsão estatística baseada em médias de gols marcados/sofridos "
                        "da temporada atual. Não constitui recomendação de aposta."
                    )
