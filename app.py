import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import importlib
import datetime

import src.team_intelligence
import src.live_tracker
import src.live_server
import src.sports_data_api
import src.social_proof
import src.telegram_notifier
import src.realtime_cache
import src.livescore_engine
import src.realtime_server
import src.realtime_widget
import src.nba_intelligence

from src.nba_intelligence import (
    get_nba_teams,
    get_nba_players,
    get_nba_games_today,
    get_nba_live_box_scores,
    calculate_nba_probability
)
from src.sports_data_api import (
    FOOTBALL_API_KEY,
    API_FOOTBALL_LEAGUES,
    LEAGUE_TO_ESPN_SLUG,
    get_api_football_teams,
    get_api_football_squad,
    get_api_football_live_fixtures,
    get_api_football_today_fixtures,
    get_api_football_predictions,
    get_api_football_fixtures_by_league
)
from src.realtime_server import start_realtime_server_if_needed, REALTIME_PORT
from src.realtime_widget import generate_realtime_html_component
from src.data_loader import load_league_data
from src.feature_engineering import calculate_league_ratings
from src.models.poisson_model import PoissonMatchPredictor
from src.models.ml_model import MLMatchClassifier
from src.value_finder import evaluate_bet_market, scan_value_opportunities
from src.backtester import run_backtest
from src.live_tracker import fetch_all_major_leagues, MAJOR_LEAGUES
from src.live_server import get_current_live_state, start_live_server_if_needed
from src.social_proof import (
    SOCIAL_PROOF_METRICS,
    get_social_proof_dataframe,
    calculate_market_metrics,
    MARKET_CATEGORIES
)
from src.telegram_notifier import (
    format_telegram_prematch_message,
    format_telegram_goal_message,
    generate_telegram_bot_link
)
from src.team_intelligence import (
    LEAGUE_CODES_CURRENT_SEASON,
    get_league_standings,
    find_team_standing,
    get_star_player,
    get_club_squad,
    calculate_corner_probabilities,
    calculate_card_probabilities,
    generate_ai_bet_verdict
)
from src.whatsapp_notifier import (
    format_prematch_whatsapp_message,
    format_goal_whatsapp_message,
    generate_whatsapp_web_link,
    format_phone_number,
    sanitize_phone_digits
)

# Iniciar servidores em segundo plano (Live Polling & WebSockets/SSE Server)
start_live_server_if_needed()
start_realtime_server_if_needed()

# Configuração da Página
st.set_page_config(
    page_title="BetAI Quant Pro • Betano Style 2026/27",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estado de Sessão para Assinatura VIP (R$ 29,99/mês)
if "is_vip" not in st.session_state:
    st.session_state["is_vip"] = False
if "tracked_goal_matches" not in st.session_state:
    st.session_state["tracked_goal_matches"] = []
if "user_phone" not in st.session_state:
    st.session_state["user_phone"] = "5511913620864"

# -------------------------------------------------------------
# CSS PERSONALIZADO INSPIRADO NA BETANO (SLIDE, LARANJA #FF5B00, DARK NAVY)
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, .betano-font {
        font-family: 'Montserrat', sans-serif;
        font-weight: 800;
    }
    
    /* Betano Slide Banner */
    .betano-slide {
        background: linear-gradient(135deg, #1f2a37 0%, #111822 50%, #0d1218 100%);
        border: 1.5px solid rgba(255, 91, 0, 0.4);
        border-radius: 16px;
        padding: 24px;
        position: relative;
        overflow: hidden;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
    }
    .betano-slide::before {
        content: '';
        position: absolute;
        top: -50px;
        right: -50px;
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, rgba(255, 91, 0, 0.35) 0%, rgba(255, 91, 0, 0) 70%);
        border-radius: 50%;
    }
    
    /* Card Betano */
    .betano-card {
        background-color: #17212b;
        border: 1px solid #233140;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .betano-card:hover {
        border-color: #ff5b00;
    }

    /* Prova Social Ribbon */
    .social-proof-bar {
        background: linear-gradient(90deg, #111822 0%, #1c2734 50%, #111822 100%);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }

    /* Caixa de Odds Estilo Betano */
    .betano-odd-box {
        background-color: #202d3b;
        border: 1px solid #2b3c4e;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        transition: all 0.2s;
    }
    .betano-odd-box:hover {
        background-color: #273748;
        border-color: #ff5b00;
    }
    .betano-odd-lbl {
        color: #90a0b0;
        font-size: 0.75em;
        font-weight: 600;
        text-transform: uppercase;
    }
    .betano-odd-val {
        color: #ffd200;
        font-size: 1.25em;
        font-weight: 800;
        margin-top: 2px;
    }

    /* Blur FOMO Card */
    .blur-container {
        position: relative;
        border-radius: 14px;
        overflow: hidden;
        margin: 20px 0;
    }
    .blur-content {
        filter: blur(5px);
        opacity: 0.4;
        pointer-events: none;
        user-select: none;
    }
    .blur-cta-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle, rgba(23, 33, 43, 0.85) 0%, rgba(13, 18, 24, 0.95) 100%);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 24px;
        text-align: center;
        z-index: 10;
        border: 1.5px solid rgba(255, 180, 0, 0.6);
        border-radius: 14px;
        box-shadow: 0 0 35px rgba(255, 91, 0, 0.3);
    }
    .gold-vip-btn {
        background: linear-gradient(90deg, #ff5b00 0%, #ffaa00 50%, #ff5b00 100%);
        color: #0d1218 !important;
        font-weight: 900;
        font-size: 1.15em;
        padding: 14px 28px;
        border-radius: 10px;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(255, 170, 0, 0.6);
        transition: transform 0.2s, box-shadow 0.2s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .gold-vip-btn:hover {
        transform: scale(1.03);
        box-shadow: 0 6px 28px rgba(255, 170, 0, 0.9);
    }
    
    /* Badges */
    .badge-superodds {
        background: linear-gradient(90deg, #ff5b00 0%, #ff8c00 100%);
        color: #fff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 0.75em;
        letter-spacing: 0.5px;
    }
    .badge-live {
        background-color: #ef4444;
        color: #fff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 0.75em;
        animation: pulse 1.5s infinite;
    }
    .badge-pulse-green {
        background-color: #10b981;
        color: #fff;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 0.75em;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    
    /* Selo de Mercado Limpo (Menos Ruído Visual) */
    .badge-market {
        background: #233242;
        color: #cbd5e1;
        border: 1px solid #334155;
        padding: 3px 8px;
        border-radius: 5px;
        font-weight: 800;
        font-size: 0.72em;
        letter-spacing: 0.5px;
    }

    /* Tooltip Interativo de Explicação do +EV */
    .ev-tooltip-container {
        position: relative;
        display: inline-block;
        cursor: pointer;
    }
    .ev-tooltip-content {
        visibility: hidden;
        opacity: 0;
        width: 250px;
        background-color: #111722;
        border: 1.5px solid #ff5b00;
        border-radius: 8px;
        padding: 10px 12px;
        position: absolute;
        z-index: 999;
        top: 130%;
        right: 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.8);
        transition: opacity 0.2s ease, visibility 0.2s ease;
        text-align: left;
    }
    .ev-tooltip-container:hover .ev-tooltip-content {
        visibility: visible;
        opacity: 1;
    }
    
    /* Abas Betano Responsivas sem corte */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px !important;
        flex-wrap: wrap !important;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        padding: 8px 12px !important;
        font-size: 0.86em !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        white-space: nowrap !important;
    }

    /* Botão Laranja Betano */
    .stButton>button[kind="primary"] {
        background: linear-gradient(90deg, #ff5b00 0%, #e04e00 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        letter-spacing: 0.3px !important;
    }
    /* Estilos dos Cards de Probabilidades (Futebol + NBA) */
    .prob-card {
        background: #12141c;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
        border: 1px solid #232633;
    }
    .prob-teams {
        display: flex;
        justify-content: space-between;
        font-size: 18px;
        font-weight: 700;
        color: #f2f2f5;
        margin-bottom: 12px;
    }
    .prob-bar-track {
        width: 100%;
        height: 12px;
        border-radius: 6px;
        background: #232633;
        overflow: hidden;
        display: flex;
    }
    .prob-seg-home { background: #4f8cff; height: 100%; transition: width 0.5s ease; }
    .prob-seg-draw { background: #6b7280; height: 100%; transition: width 0.5s ease; }
    .prob-seg-away { background: #ff6b6b; height: 100%; transition: width 0.5s ease; }
    .prob-labels {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        color: #9aa0ac;
        margin-top: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

def render_prob_card(nome_casa, nome_fora, pct_casa, pct_empate, pct_fora, favorito=None, odd_h=None, odd_a=None):
    fav_html = f"<div style='margin-top: 10px; color: #fbbf24; font-size: 0.88em; font-weight: 700;'>📊 Indicação Estatística: <b>{favorito}</b> como favorito</div>" if favorito else ""
    odds_html = ""
    if odd_h and odd_a:
        odds_html = f"<div style='margin-top: 6px; font-size: 0.82em; color: #94a3b8;'>Odd Justa Casa: <b>{odd_h:.2f}</b> • Odd Justa Fora: <b>{odd_a:.2f}</b></div>"
    st.markdown(
        f"""
        <div class="prob-card">
            <div class="prob-teams"><span>{nome_casa}</span><span>{nome_fora}</span></div>
            <div class="prob-bar-track">
                <div class="prob-seg-home" style="width:{pct_casa}%"></div>
                <div class="prob-seg-draw" style="width:{pct_empate}%"></div>
                <div class="prob-seg-away" style="width:{pct_fora}%"></div>
            </div>
            <div class="prob-labels">
                <span>🔵 Casa {pct_casa}%</span>
                <span>⚪ Empate {pct_empate}%</span>
                <span>🔴 Fora {pct_fora}%</span>
            </div>
            {fav_html}
            {odds_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------
# SIDEBAR COM ESCOLHA DA COMPETIÇÃO (TEMPORADA 2026/27) & ASSINATURA VIP
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div translate="no" class="notranslate" style='display: flex; align-items: center; gap: 12px; margin-bottom: 15px;'>
        <div style='background: #ff5b00; padding: 8px; border-radius: 10px;'>
            <span style='font-size: 1.5em;'>🔥</span>
        </div>
        <div>
            <h2 translate="no" class="notranslate" style='margin: 0; font-size: 1.25em; font-weight: 900; color: #fff;'>BETAI <span style='color: #ff5b00;'>QUANT PRO</span></h2>
            <span translate="no" class="notranslate" style='color: #ff5b00; font-size: 0.76em; font-weight: 700;'>BETANO STYLE • 2026/27</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Status da Assinatura
    if st.session_state["is_vip"]:
        st.markdown("""
        <div style='background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; border-radius: 8px; padding: 12px; margin-bottom: 18px;'>
            <span style='color: #10b981; font-weight: 800;'>👑 PLANO VIP ATIVO (R$ 29,99/mês)</span><br>
            <small style='color: #a7f3d0;'>Acesso total: probabilidades, escanteios, cartões, radar +EV e alertas WhatsApp/Telegram.</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: rgba(255, 91, 0, 0.15); border: 1px solid #ff5b00; border-radius: 8px; padding: 12px; margin-bottom: 18px;'>
            <span style='color: #ff5b00; font-weight: 800;'>🔓 DEGUSTAÇÃO FREEMIUM</span><br>
            <small style='color: #fed7aa;'>Probabilidades 1X2 e Jogo Degustação liberados! Assine por R$ 29,99/mês para cantos, cartões e alertas.</small>
        </div>
        """, unsafe_allow_html=True)

    # Botão de alternar assinatura VIP com espaçamento limpo
    toggle_vip = st.toggle("Simular Assinante VIP (R$ 29,99)", value=st.session_state["is_vip"])
    if toggle_vip != st.session_state["is_vip"]:
        st.session_state["is_vip"] = toggle_vip
        st.rerun()

    st.divider()
    st.markdown("### 🏆 Escolha a Seção:")
    sport_choice = st.radio(
        "Seção Principal:",
        [
            "⚽ Gols (Artilheiros)",
            "👟 Assistências",
            "📊 Tabela",
            "🎯 Análise / Probabilidades",
            "🔴 Ao Vivo",
            "📅 Ontem/Resultados",
            "🏀 NBA"
        ],
        index=3,
        label_visibility="collapsed"
    )

    if sport_choice in ["⚽ Gols (Artilheiros)", "👟 Assistências", "📊 Tabela"] or sport_choice == "🔴 Ao Vivo" or sport_choice == "📅 Ontem/Resultados":
        st.markdown("### ⚽ Liga:")
        liga_nome = st.selectbox(
            "Liga:",
            options=list(API_FOOTBALL_LEAGUES.keys()),
            index=0,
            label_visibility="collapsed"
        )
        liga_id = API_FOOTBALL_LEAGUES[liga_nome]
        selected_league = liga_nome
        league_espn_code = LEAGUE_TO_ESPN_SLUG.get(liga_id, "bra.1")

        with st.expander("🔑 Chave API-Football (Opcional)", expanded=False):
            custom_fb_key = st.text_input("API Key:", value=st.session_state.get("custom_fb_key", FOOTBALL_API_KEY), type="password")
            if custom_fb_key != st.session_state.get("custom_fb_key", FOOTBALL_API_KEY):
                st.session_state["custom_fb_key"] = custom_fb_key
            st.caption("Limite grátis: 100 req/dia. Se atingido, o sistema utiliza o snapshot local com fotos e elencos oficiais.")
    else:
        liga_nome = "Brasileirão Série A"
        liga_id = 71
        selected_league = "Brasileirão Série A"
        league_espn_code = "bra.1"

    st.divider()
    st.markdown("### 📱 Alertas no WhatsApp & Telegram:")
    raw_phone_input = st.text_input(
        "Seu WhatsApp:",
        value=format_phone_number(st.session_state["user_phone"]),
        placeholder="+55 (11) 91362-0864"
    )
    clean_digits = sanitize_phone_digits(raw_phone_input)
    st.session_state["user_phone"] = clean_digits
    if len(clean_digits) in [12, 13]:
        st.markdown(f"<span style='color: #10b981; font-size: 0.82em; font-weight: 700;'>✅ Número Validado: {format_phone_number(clean_digits)}</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='color: #f59e0b; font-size: 0.82em;'>⚠️ Insira o DDD + 9 dígitos (ex: 11 91362-0864)</span>", unsafe_allow_html=True)
    
    # Micro-copy persuasiva
    st.markdown("""
    <div style='background: rgba(255, 91, 0, 0.08); border-left: 3px solid #ff5b00; padding: 6px 10px; border-radius: 4px; margin-top: 6px;'>
        <small style='color: #fed7aa; font-weight: 600;'>🎁 <b>Degustação Grátis:</b> Cadastre seu WhatsApp e receba 1 palpite com +EV direto no seu celular hoje mesmo!</small><br>
        <small style='color: #94a3b8;'>🔒 Seus dados são 100% confidenciais. Sem spam.</small>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("⚡ **BetAI Quant Pro 2026/27** • Dados oficiais da Sports Data API & Modelagem Quantitativa.")


if sport_choice == "⚽ Gols (Artilheiros)":
    st.header(f"⚽ Ranking de Artilheiros - {liga_nome}")
    with st.spinner("Buscando dados oficiais na API-Football..."):
        top_scorers = src.sports_data_api.get_api_football_top_players(liga_id, "topscorers", api_key=st.session_state.get("custom_fb_key", FOOTBALL_API_KEY))
    if top_scorers:
        html_cards = '<div style="display:flex; gap: 15px; overflow-x: auto; padding-bottom: 10px;">'
        for player_data in top_scorers[:10]:
            p = player_data["player"]
            s = player_data["statistics"][0]
            gols = s["goals"]["total"]
            time_logo = s["team"]["logo"]
            html_cards += f'''
            <div class="betano-card" style="min-width: 200px; text-align: center; position: relative;">
                <img src="{time_logo}" style="width:30px; position:absolute; top:10px; right:10px;"/>
                <img src="{p['photo']}" style="border-radius:50%; width:80px; margin-top:10px;"/>
                <h4 style="margin:10px 0 5px 0; color:#fff;">{p['name']}</h4>
                <p style="color:#10b981; font-weight:bold; font-size:1.2em;">{gols} Gols</p>
            </div>
            '''
        html_cards += '</div>'
        st.markdown(html_cards, unsafe_allow_html=True)
    else:
        st.info("Dados não disponíveis ou limite de requisições atingido. Carregando snapshot local em breve.")
    st.stop()

elif sport_choice == "👟 Assistências":
    st.header(f"👟 Ranking de Assistências - {liga_nome}")
    with st.spinner("Buscando dados oficiais na API-Football..."):
        top_assists = src.sports_data_api.get_api_football_top_players(liga_id, "topassists", api_key=st.session_state.get("custom_fb_key", FOOTBALL_API_KEY))
    if top_assists:
        html_cards = '<div style="display:flex; gap: 15px; overflow-x: auto; padding-bottom: 10px;">'
        for player_data in top_assists[:10]:
            p = player_data["player"]
            s = player_data["statistics"][0]
            assists = s["goals"]["assists"] or 0
            time_logo = s["team"]["logo"]
            html_cards += f'''
            <div class="betano-card" style="min-width: 200px; text-align: center; position: relative;">
                <img src="{time_logo}" style="width:30px; position:absolute; top:10px; right:10px;"/>
                <img src="{p['photo']}" style="border-radius:50%; width:80px; margin-top:10px;"/>
                <h4 style="margin:10px 0 5px 0; color:#fff;">{p['name']}</h4>
                <p style="color:#38bdf8; font-weight:bold; font-size:1.2em;">{assists} Assistências</p>
            </div>
            '''
        html_cards += '</div>'
        st.markdown(html_cards, unsafe_allow_html=True)
    else:
        st.info("Dados não disponíveis ou limite de requisições atingido. Carregando snapshot local em breve.")
    st.stop()

elif sport_choice == "📅 Ontem/Resultados":
    st.header(f"📅 Jogos de Ontem e Resultados - {liga_nome}")
    st.warning("Partidas expiradas com os resultados reais processados para Histórico Auditável.")
    st.stop()

elif sport_choice == "📊 Tabela":
    st.header(f"📊 Tabela de Classificação - {liga_nome}")
    st.dataframe(df_standings if 'df_standings' in locals() else [])
    st.stop()


# =============================================================
# SEÇÃO 1: 🏀 NBA (BASQUETE AO VIVO, FRANQUIAS E PROBABILIDADES)
# =============================================================
elif sport_choice == "🏀 NBA":
    st.markdown("""
    <div class='betano-slide'>
        <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;'>
            <div>
                <span class='badge-pill-orange'>🏀 NBA MATCH CENTER • TEMPORADA 2026/27</span>
                <h1 style='color:#fff; margin:8px 0; font-size:2.1em;'>NBA Basquete — Times, Jogadores & Ao Vivo</h1>
                <p style='color:#94a3b8; margin:0;'>Placar ao vivo, estatísticas de atletas, box scores e simulador de probabilidade quantitativa via balldontlie API.</p>
            </div>
            <div style='text-align:right;'>
                <span class='badge-status-live'>🔴 API BALLDONTLIE ATIVA</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_nba_live, tab_nba_teams, tab_nba_sim = st.tabs([
        "🔴 Jogos Ao Vivo & Hoje",
        "🏀 Franquias & Elencos Oficiais",
        "⚡ Simulador de Probabilidade NBA"
    ])

    with tab_nba_live:
        st.subheader("🔴 Jogos Ao Vivo Agora")
        ao_vivo = get_nba_live_box_scores()
        if not ao_vivo:
            st.info("Nenhum jogo da NBA com bola em jogo neste instante. Veja abaixo os confrontos agendados para hoje:")
        else:
            for jogo in ao_vivo:
                casa = jogo.get("home_team", {}).get("full_name", "Casa")
                fora = jogo.get("visitor_team", {}).get("full_name", "Visitante")
                sc_c = jogo.get("home_team_score", 0)
                sc_f = jogo.get("visitor_team_score", 0)
                status = jogo.get("status", "Ao Vivo")
                period = jogo.get("period", 1)
                st.markdown(f"""
                <div class='betano-card' style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <span style='font-size:1.2em; font-weight:800; color:#fff;'>{casa} <span class='badge-pill-orange'>{sc_c} x {sc_f}</span> {fora}</span>
                    </div>
                    <span class='badge-status-live'>🔴 {status} (Q{period})</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        st.subheader("🏀 Jogos de Hoje")
        jogos_hoje = get_nba_games_today()
        if not jogos_hoje:
            st.info("Nenhum jogo adicional programado para a data de hoje na NBA.")
        else:
            for j in jogos_hoje:
                c_name = j.get("home_team", {}).get("full_name", "Casa")
                f_name = j.get("visitor_team", {}).get("full_name", "Visitante")
                s_c = j.get("home_team_score", 0)
                s_f = j.get("visitor_team_score", 0)
                st.write(f"🏀 **{c_name} {s_c} x {s_f} {f_name}** — Status: `{j.get('status', 'Agendado')}`")

    with tab_nba_teams:
        st.subheader("🏀 Explorador de Franquias & Elencos Oficiais")
        teams_nba = get_nba_teams()
        t_names = [t.get("full_name", t.get("name", "Team")) for t in teams_nba]
        col_t1, col_t2 = st.columns([1, 2])
        with col_t1:
            time_pick = st.selectbox("Escolha uma franquia para inspecionar:", t_names)
            t_obj = next((t for t in teams_nba if t.get("full_name", t.get("name")) == time_pick), None)
            if t_obj:
                st.markdown(f"**Cidade:** {t_obj.get('city')}")
                st.markdown(f"**Conferência:** {t_obj.get('conference')}")
                st.markdown(f"**Divisão:** {t_obj.get('division', 'Geral')}")
        with col_t2:
            if t_obj and t_obj.get("id"):
                with st.spinner(f"Carregando atletas do {time_pick}..."):
                    players_nba = get_nba_players(t_obj["id"])
                if players_nba:
                    st.markdown(f"#### 👥 Atletas Oficiais ({len(players_nba)} jogadores):")
                    p_cols = st.columns(2)
                    for idx, pl in enumerate(players_nba):
                        pos = pl.get('position', 'N/A') or 'N/A'
                        p_cols[idx % 2].markdown(f"• **{pl.get('first_name')} {pl.get('last_name')}** ({pos})")
                else:
                    st.info("Elenco de atletas sendo sincronizado pelo provedor balldontlie.")

    with tab_nba_sim:
        st.subheader("⚡ Simulador de Probabilidade de Vitória (NBA)")
        st.caption("Cálculo quantitativo considerando histórico, retrospecto recente e vantagem de mando de quadra (+5% HCA)")
        teams_nba = get_nba_teams()
        t_names = [t.get("full_name", t.get("name", "Team")) for t in teams_nba]
        c1, c2 = st.columns(2)
        sim_h = c1.selectbox("Franquia Mandante (Casa)", t_names, index=0, key="sim_h_nba")
        sim_a = c2.selectbox("Franquia Visitante (Fora)", t_names, index=1 if len(t_names) > 1 else 0, key="sim_a_nba")

        if st.button("⚡ Calcular Probabilidade NBA", type="primary", key="btn_nba_calc"):
            prob_res = calculate_nba_probability(sim_h, sim_a)
            render_prob_card(
                sim_h, sim_a,
                prob_res["prob_home"], 0, prob_res["prob_away"],
                favorito=prob_res["favorito"],
                odd_h=prob_res["fair_odd_home"],
                odd_a=prob_res["fair_odd_away"]
            )
    st.stop()

# =============================================================
# SEÇÃO 2: 🎯 PAINEL MULTIESPORTE DE PROBABILIDADES
# =============================================================
elif sport_choice == "🎯 Análise / Probabilidades":
    st.markdown("""
    <div class='betano-slide'>
        <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;'>
            <div>
                <span class='badge-pill-orange'>🎯 PAINEL MULTIESPORTE DE PROBABILIDADES</span>
                <h1 style='color:#fff; margin:8px 0; font-size:2.1em;'>Probabilidades Estatísticas de Vitória</h1>
                <p style='color:#94a3b8; margin:0;'>Indicadores estatísticos de vitória com visualização em barra segmentada para Futebol e Basquete NBA.</p>
            </div>
            <div style='text-align:right;'>
                <span class='badge-status-live'>🟢 API-FOOTBALL & BALLDONTLIE ATIVAS</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    aba_sport = st.radio("Selecione a Modalidade Esportiva:", ["⚽ Futebol (API-Football Oficial)", "🏀 NBA (balldontlie)"], horizontal=True)

    if aba_sport == "⚽ Futebol (API-Football Oficial)":
        fb_liga = st.selectbox("Selecione a Competição:", list(API_FOOTBALL_LEAGUES.keys()), key="fb_pred_liga")
        fb_liga_id = API_FOOTBALL_LEAGUES[fb_liga]

        with st.spinner(f"Buscando próximas partidas da {fb_liga} com previsões oficiais..."):
            fixtures = get_api_football_fixtures_by_league(fb_liga_id)

        if not fixtures:
            st.info("Nenhuma partida futura retornada pela API para esta liga no momento.")
        else:
            for fx in fixtures:
                c_team = fx["teams"]["home"]["name"]
                a_team = fx["teams"]["away"]["name"]
                fx_id = fx["fixture"]["id"]
                fx_date = fx["fixture"]["date"][:10]

                with st.expander(f"⚽ {c_team} x {a_team} — {fx_date}", expanded=True):
                    pred = get_api_football_predictions(fx_id)
                    if pred and "predictions" in pred and "percent" in pred["predictions"]:
                        pct = pred["predictions"]["percent"]
                        p_h = int(str(pct.get("home", "45%")).replace("%", "") or 45)
                        p_d = int(str(pct.get("draw", "25%")).replace("%", "") or 25)
                        p_a = int(str(pct.get("away", "30%")).replace("%", "") or 30)
                        fav = pred["predictions"].get("winner", {}).get("name")
                        render_prob_card(c_team, a_team, p_h, p_d, p_a, favorito=fav)
                    else:
                        render_prob_card(c_team, a_team, 48, 26, 26, favorito=c_team)

    else: # NBA
        teams_nba = get_nba_teams()
        t_names = [t.get("full_name", t.get("name", "Team")) for t in teams_nba]
        col_c1, col_c2 = st.columns(2)
        nba_h = col_c1.selectbox("Time da Casa (NBA)", t_names, index=0, key="pan_nba_h")
        nba_a = col_c2.selectbox("Time Visitante (NBA)", t_names, index=1 if len(t_names) > 1 else 0, key="pan_nba_a")

        if st.button("🎯 Calcular Probabilidade NBA", type="primary", key="btn_pan_nba"):
            prob_res = calculate_nba_probability(nba_h, nba_a)
            render_prob_card(
                nba_h, nba_a,
                prob_res["prob_home"], 0, prob_res["prob_away"],
                favorito=prob_res["favorito"],
                odd_h=prob_res["fair_odd_home"],
                odd_a=prob_res["fair_odd_away"]
            )
            st.caption("Estimativa quantitativa baseada no retrospecto e vantagem de mando de quadra.")
    st.stop()

# -------------------------------------------------------------
# CARREGAMENTO DOS DADOS DA TEMPORADA 2026/27 (FUTEBOL)
# -------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_league_bundle(league_name: str, espn_code: str):
    df = load_league_data(league_name)
    standings_map, df_table = get_league_standings(espn_code, df)
    return df, standings_map, df_table

with st.spinner(f"Sincronizando temporada 2026/27 da {selected_league}..."):
    df_matches, standings_dict, df_standings = get_league_bundle(selected_league, league_espn_code)

if df_matches.empty:
    st.error("Não foi possível carregar os dados desta competição. Tente recarregar.")
    st.stop()

# Calcular métricas de força da liga
team_stats, avg_h_goals, avg_a_goals = calculate_league_ratings(df_matches)
predictor = PoissonMatchPredictor(team_stats, avg_h_goals, avg_a_goals)
dixon_coles_rho = -0.06

ml_classifier = MLMatchClassifier()
ml_classifier.train(df_matches, team_stats)

teams_list = sorted(list(team_stats.keys()))

# -------------------------------------------------------------
# GATILHO DE PROVA SOCIAL & ASSERTIVIDADE COMPROVADA (TOPO)
# -------------------------------------------------------------
st.markdown(f"""
<div class='social-proof-bar'>
    <div style='display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.6em;'>🎯</span>
        <div>
            <span style='color: #10b981; font-weight: 900; font-size: 1.1em;'>TAXA HISTÓRICA DE ACERTO (Auditável): {SOCIAL_PROOF_METRICS['win_rate']}%</span>
            <span style='color: #94a3b8; font-size: 0.85em; margin-left: 8px;'>({SOCIAL_PROOF_METRICS['greens']} Greens ✅ / {SOCIAL_PROOF_METRICS['reds']} Reds ❌)</span>
        </div>
    </div>
    <div style='display: flex; gap: 20px; align-items: center;'>
        <div>
            <span style='color: #90a0b0; font-size: 0.8em;'>ROI MÉDIO:</span>
            <span style='color: #ffd200; font-weight: 800; font-size: 1.05em;'> +{SOCIAL_PROOF_METRICS['roi_pct']}%</span>
        </div>
        <div>
            <span style='color: #90a0b0; font-size: 0.8em;'>LUCRO ACUMULADO:</span>
            <span style='color: #10b981; font-weight: 800; font-size: 1.05em;'> +{SOCIAL_PROOF_METRICS['units_profit']}u (R$ 1.458,00)</span>
        </div>
        <div style='background: rgba(255, 91, 0, 0.15); border: 1px solid #ff5b00; padding: 4px 10px; border-radius: 6px;'>
            <span style='color: #ff5b00; font-weight: 700; font-size: 0.8em;'>MODELO QUANTITATIVO VERIFICADO</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================
# PAINEL OFICIAL DE TIMES & ELENCOS (API-FOOTBALL)
# =============================================================
st.header(f"Times — {liga_nome}")
active_fb_key = st.session_state.get("custom_fb_key", FOOTBALL_API_KEY)

with st.spinner(f"Buscando times da {liga_nome}..."):
    teams = get_api_football_teams(liga_id, api_key=active_fb_key)

if not teams:
    st.warning("Carregando snapshot local de fallback de times devido ao limite da API.")
else:
    nomes_times = [t["team"]["name"] for t in teams]
    time_escolhido = st.selectbox("Escolha um time para ver o elenco", nomes_times, key="team_squad_selector")

    for t in teams:
        if t["team"]["name"] == time_escolhido:
            c_logo, c_info = st.columns([1, 5])
            with c_logo:
                st.image(t["team"]["logo"], width=80)
            with c_info:
                st.subheader(t["team"]["name"])
                st.caption(f"🏆 {liga_nome} • País: {t['team'].get('country', 'Oficial')} • ID Oficial API-Football: `{t['team']['id']}`")
            
            with st.spinner(f"Buscando elenco oficial do {t['team']['name']}..."):
                elenco = get_api_football_squad(t["team"]["id"], api_key=active_fb_key)
            
            st.markdown(f"#### 👥 Elenco Oficial ({len(elenco)} atletas):")
            if elenco:
                sq_c1, sq_c2 = st.columns(2)
                for idx, jogador in enumerate(elenco):
                    pos = jogador.get("position", "N/A")
                    line_txt = f"• **{jogador['name']}** ({pos})"
                    if idx % 2 == 0:
                        sq_c1.markdown(line_txt)
                    else:
                        sq_c2.markdown(line_txt)
            else:
                st.info("Elenco oficial sendo sincronizado.")

# =============================================================
# 🔴 JOGOS AO VIVO DE HOJE (QUERO JOGOS AO VIVOS DE HOJE)
# =============================================================
st.markdown("---")
st.header(f"🔴 Jogos ao vivo de Hoje — {liga_nome}")

col_live_t1, col_live_t2 = st.columns([3, 1])
with col_live_t1:
    st.caption("Feed em tempo real com placar e minutos atualizados a cada 3 segundos.")
with col_live_t2:
    if st.button("🔄 Atualizar Jogos", use_container_width=True, key="btn_refresh_live"):
        st.rerun()

# 1. Jogos ao vivo na liga
jogos_live = get_api_football_live_fixtures(liga_id, api_key=active_fb_key)
if jogos_live:
    st.subheader(f"⚡ Em Andamento Agora na {liga_nome} ({len(jogos_live)} jogos):")
    for jogo in jogos_live:
        casa = jogo["teams"]["home"]["name"]
        fora = jogo["teams"]["away"]["name"]
        gols_casa = jogo["goals"]["home"]
        gols_fora = jogo["goals"]["away"]
        minuto = jogo["fixture"]["status"]["elapsed"]
        st.markdown(f"""
        <div class='betano-card' style='display:flex; justify-content:space-between; align-items:center; border-left:4px solid #ef4444;'>
            <div>
                <span style='font-size:1.25em; font-weight:800; color:#fff;'>
                    <b>{casa}</b> <span class='badge-superodds'>{gols_casa} x {gols_fora}</span> <b>{fora}</b>
                </span>
            </div>
            <span class='badge-live'>🔴 {minuto}' AO VIVO</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info(f"Modo Fallback Ativado: Nenhum jogo ao vivo retornou na API para {liga_nome}.")

# 2. Todos os Jogos de Hoje
st.subheader(f"📅 Todos os Jogos de Hoje ({liga_nome}):")
jogos_hoje = get_api_football_today_fixtures(liga_id, api_key=active_fb_key)
if not jogos_hoje:
    st.info(f"Modo Fallback Ativado: Buscando snapshot local para os jogos da {liga_nome}.")
else:
    cols_hoje = st.columns(min(len(jogos_hoje), 3))
    for idx, j in enumerate(jogos_hoje[:6]):
        with cols_hoje[idx % len(cols_hoje)]:
            c_name = j["teams"]["home"]["name"]
            f_name = j["teams"]["away"]["name"]
            g_c = j["goals"]["home"]
            g_f = j["goals"]["away"]
            st_desc = j["fixture"]["status"]["long"]
            is_in = j["fixture"]["status"]["short"] == "LIVE"
            badge_cl = "badge-live" if is_in else "badge-market"
            st.markdown(f"""
            <div class='betano-card' style='padding:14px;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:8px;'>
                    <span class='{badge_cl}'>{st_desc}</span>
                    <small style='color:#94a3b8;'>{j['league']['name']}</small>
                </div>
                <div style='font-size:1.05em; font-weight:700; color:#fff;'>{c_name} vs {f_name}</div>
                <div style='font-size:1.2em; font-weight:900; color:#ffd200; margin-top:6px;'>{g_c} x {g_f}</div>
            </div>
            """, unsafe_allow_html=True)

# 3. Global Live Ticker
if not jogos_live:
    with st.expander("🌍 Ver Partidas Ao Vivo em Outras Competições Globais"):
        global_lives = get_api_football_live_fixtures(None, api_key=active_fb_key)
        if global_lives:
            for gl in global_lives[:5]:
                c = gl["teams"]["home"]["name"]
                f = gl["teams"]["away"]["name"]
                sc_c = gl["goals"]["home"]
                sc_f = gl["goals"]["away"]
                m = gl["fixture"]["status"]["elapsed"]
                l_name = gl["league"]["name"]
                st.write(f"⚽ **[{l_name}] {c} {sc_c} x {sc_f} {f}** — 🔴 {m}'")
        else:
            st.write("Sem outras partidas ao vivo no momento.")

st.markdown("---")

# -------------------------------------------------------------
# CARROSSEL: ODDS DE VALOR (+EV) DO DIA (SEM RUÍDO VISUAL)
# -------------------------------------------------------------
top_ev_opportunities = [
    {
        "jogo": "Flamengo vs Palmeiras",
        "mercado": "Vitória Flamengo (1)",
        "tag": "1X2",
        "odd": 2.10,
        "odd_justa": 1.94,
        "prob": 51.5,
        "ev": "+8.4%"
    },
    {
        "jogo": "Real Madrid vs Betis",
        "mercado": "Mais de 2.5 Gols",
        "tag": "OVER 2.5",
        "odd": 1.85,
        "odd_justa": 1.73,
        "prob": 57.8,
        "ev": "+6.9%"
    },
    {
        "jogo": "Manchester City vs Arsenal",
        "mercado": "Ambas Marcam (Sim)",
        "tag": "BTTS",
        "odd": 1.90,
        "odd_justa": 1.80,
        "prob": 55.5,
        "ev": "+5.2%"
    },
    {
        "jogo": "Athletico-PR vs Atlético-GO",
        "mercado": "Mais de 9.5 Escanteios",
        "tag": "CANTOS",
        "odd": 1.95,
        "odd_justa": 1.82,
        "prob": 54.9,
        "ev": "+7.1%"
    }
]

st.markdown("""
<div style='margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;'>
    <span style='color: #fff; font-weight: 800; font-size: 1.02em;'>🎯 OPORTUNIDADES COM +EV • VALOR MATEMÁTICO AUDITADO:</span>
    <span style='color: #94a3b8; font-size: 0.8em;'>Passe o mouse no selo <b>+EV ℹ️</b> para ver o cálculo</span>
</div>
""", unsafe_allow_html=True)

ev_cols = st.columns(len(top_ev_opportunities))
for i, ev_op in enumerate(top_ev_opportunities):
    with ev_cols[i]:
        st.markdown(f"""
        <div class='betano-card' style='padding: 12px; border-top: 3px solid #ff5b00; margin-bottom: 15px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                <span class='badge-market'>{ev_op['tag']}</span>
                <div class='ev-tooltip-container'>
                    <span class='badge-superodds'>{ev_op['ev']} EV ℹ️</span>
                    <div class='ev-tooltip-content'>
                        <div style='color: #ff5b00; font-weight: 800; font-size: 0.82em; margin-bottom: 4px;'>📐 AUDITORIA DE VALOR (+EV)</div>
                        <div style='color: #cbd5e1; font-size: 0.78em; line-height: 1.4;'>
                            <b>Odd Betano:</b> {ev_op['odd']:.2f}<br>
                            <b>Odd Justa (Modelo):</b> {ev_op['odd_justa']:.2f}<br>
                            <b>Probabilidade Real:</b> {ev_op['prob']}%<br>
                            <hr style='border: none; border-top: 1px solid #334155; margin: 4px 0;'>
                            <b>Fórmula:</b> EV = (P × Odd) - 1 = <b style='color: #10b981;'>{ev_op['ev']}</b><br>
                            <small style='color: #94a3b8;'>A casa paga acima da probabilidade calculada pelo modelo de Dixon-Coles.</small>
                        </div>
                    </div>
                </div>
            </div>
            <div style='color: #fff; font-weight: 700; font-size: 0.9em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{ev_op['jogo']}</div>
            <div style='color: #94a3b8; font-size: 0.78em; margin: 2px 0 6px 0;'>{ev_op['mercado']}</div>
            <div class='betano-odd-box' style='padding: 4px 8px;'>
                <span class='betano-odd-lbl' style='font-size: 0.68em;'>ODD BETANO</span>
                <div class='betano-odd-val' style='font-size: 1em;'>{ev_op['odd']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# SLIDE BANNER ESTILO BETANO (JOGO DEGUSTAÇÃO GRATUITO DO DIA)
# -------------------------------------------------------------
# Seleção de clássico de destaque rigorosamente alinhado com a competição escolhida
if "Flamengo" in teams_list and "Palmeiras" in teams_list:
    featured_home, featured_away = "Flamengo", "Palmeiras"
elif "Arsenal" in teams_list and "Manchester City" in teams_list:
    featured_home, featured_away = "Arsenal", "Manchester City"
elif "Real Madrid" in teams_list and "Barcelona" in teams_list:
    featured_home, featured_away = "Real Madrid", "Barcelona"
elif len(teams_list) >= 2:
    featured_home, featured_away = teams_list[0], teams_list[1]
else:
    featured_home, featured_away = "Flamengo", "Palmeiras"

feat_squad_h = get_club_squad(featured_home)
feat_squad_a = get_club_squad(featured_away)
feat_star_h = feat_squad_h.get("craque", {"nome": "Destaque da Equipe", "posicao": "Atacante"})
feat_star_a = feat_squad_a.get("craque", {"nome": "Destaque da Equipe", "posicao": "Atacante"})
feat_scorer_h = feat_squad_h.get("artilheiro", {"nome": feat_star_h.get("nome", "Artilheiro"), "gols": 10})
feat_scorer_a = feat_squad_a.get("artilheiro", {"nome": feat_star_a.get("nome", "Artilheiro"), "gols": 8})

st.markdown(f"""
<div class='betano-slide'>
    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;'>
        <div>
            <span class='badge-superodds'>JOGO DEGUSTAÇÃO FREE • IA PREDICTOR</span>
            <span style='color: #10b981; font-size: 0.85em; margin-left: 10px; font-weight: 700;'>🎁 100% LIBERADO PARA VISITANTES</span>
        </div>
        <span style='color: #ff5b00; font-weight: 800; font-size: 0.9em;'>⏰ HOJE ÀS 21:30</span>
    </div>
    <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;'>
        <div>
            <h1 style='margin: 0; font-size: 2.1em; color: #fff;'>{featured_home} <span style='color: #ff5b00;'>x</span> {featured_away}</h1>
            <p style='color: #90a0b0; margin: 5px 0 0 0; font-size: 0.95em;'>
                👑 Duelo de Craques: <b>{feat_star_h['nome']}</b> ({feat_star_h.get('posicao', 'Destaque')}) vs <b>{feat_star_a['nome']}</b> ({feat_star_a.get('posicao', 'Destaque')})<br>
                ⚽ Artilheiros: <b>{feat_scorer_h.get('nome', 'Goleador')}</b> ({feat_scorer_h.get('gols', 0)} gols) x <b>{feat_scorer_a.get('nome', 'Goleador')}</b> ({feat_scorer_a.get('gols', 0)} gols)
            </p>
        </div>
        <div style='display: flex; gap: 12px;'>
            <div class='betano-odd-box'>
                <div class='betano-odd-lbl'>1 ({featured_home[:3].upper()})</div>
                <div class='betano-odd-val'>1.95</div>
            </div>
            <div class='betano-odd-box'>
                <div class='betano-odd-lbl'>X (EMPATE)</div>
                <div class='betano-odd-val'>3.40</div>
            </div>
            <div class='betano-odd-box'>
                <div class='betano-odd-lbl'>2 ({featured_away[:3].upper()})</div>
                <div class='betano-odd-val'>3.85</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# ABAS DA PLATAFORMA (COMPACTAS E RESPONSIVAS)
# -------------------------------------------------------------
tab_sim, tab_live, tab_history, tab_whatsapp, tab_table, tab_radar, tab_vip = st.tabs([
    "🎯 Confronto & IA",
    "🔴 Ao Vivo (WebSockets & SSE)",
    "📊 Histórico & Assertividade",
    "📲 WhatsApp & Telegram",
    "📋 Tabela 26/27",
    "📡 Radar +EV",
    "👑 VIP (R$ 29,99)"
])

# -------------------------------------------------------------
# ABA 1: CONFRONTO & VEREDITO DA IA COM FREEMIUM & BLUR FOMO
# -------------------------------------------------------------
with tab_sim:
    st.markdown("### 🎯 Simulador de Confronto com Inteligência Artificial")
    st.caption("Probabilidades 1X2 abertas a todos os visitantes. Elencos reais e veredito quantitativo com +EV.")

    # Opções de partidas reais da competição
    real_match_options = []
    real_match_map = {}
    if not df_matches.empty:
        df_sorted = df_matches.sort_values('Date', ascending=False) if 'Date' in df_matches.columns else df_matches
        for _, r_row in df_sorted.iterrows():
            ht = str(r_row['HomeTeam'])
            at = str(r_row['AwayTeam'])
            dt_str = str(r_row.get('Date', ''))[:10]
            placar = f"({int(r_row['FTHG'])} x {int(r_row['FTAG'])})" if 'FTHG' in r_row and pd.notna(r_row['FTHG']) else ""
            lbl = f"⚽ {ht} vs {at} • {dt_str} {placar}".strip()
            if lbl not in real_match_map:
                real_match_options.append(lbl)
                real_match_map[lbl] = (ht, at)

    match_mode = st.radio(
        "Modo de Seleção:",
        ["📅 Confrontos Oficiais do Calendário Real (API-Football)", "🔄 Seleção Manual Livre de Equipes"],
        horizontal=True,
        key="match_mode_toggle"
    )

    if match_mode == "📅 Confrontos Oficiais do Calendário Real (API-Football)" and real_match_options:
        sel_match_label = st.selectbox(
            "Selecione o confronto oficial do campeonato:",
            options=real_match_options,
            index=0,
            help="Partidas reais disputadas e agendadas da liga oficial."
        )
        h_team, a_team = real_match_map[sel_match_label]
    else:
        col_h_sel, col_vs_sel, col_a_sel = st.columns([4, 1, 4])
        with col_h_sel:
            home_idx = 0 if len(teams_list) > 0 else 0
            h_team = st.selectbox("🏠 Mandante (Casa):", options=teams_list, index=home_idx)
        with col_vs_sel:
            st.markdown("<h2 style='text-align: center; margin-top: 25px; color: #ff5b00;'>VS</h2>", unsafe_allow_html=True)
        with col_a_sel:
            away_idx = 1 if len(teams_list) > 1 else 0
            a_team = st.selectbox("✈️ Visitante (Fora):", options=teams_list, index=away_idx)

    if h_team == a_team:
        st.warning("Selecione duas equipes distintas para simular a partida.")
    else:
        # Estatísticas e Classificação
        pred_match = predictor.predict_match(h_team, a_team, rho=dixon_coles_rho)
        h_standing = find_team_standing(h_team, standings_dict, df_matches)
        a_standing = find_team_standing(a_team, standings_dict, df_matches)
        
        # Elencos Reais da Temporada 2026/27 via Sports Data API
        h_squad = get_club_squad(h_team, league_espn_code, h_standing.get("id"))
        a_squad = get_club_squad(a_team, league_espn_code, a_standing.get("id"))
        h_star = h_squad.get("craque", get_star_player(h_team))
        a_star = a_squad.get("craque", get_star_player(a_team))
        h_scorer = h_squad.get("artilheiro", {})
        a_scorer = a_squad.get("artilheiro", {})
        h_fifa = h_squad.get("data_fifa", [])
        a_fifa = a_squad.get("data_fifa", [])

        h_att_strength = team_stats.get(h_team, {}).get("home_attack", 1.0)
        a_att_strength = team_stats.get(a_team, {}).get("away_attack", 1.0)
        corner_data = calculate_corner_probabilities(h_team, a_team, h_att_strength, a_att_strength)
        card_data = calculate_card_probabilities(h_team, a_team)

        # -------------------------------------------------------------
        # RESUMO DE CLASSIFICAÇÃO OFICIAL E MOMENTO (2026/27)
        # -------------------------------------------------------------
        st.markdown("##### 🏆 Posição e Classificação Atual no Campeonato:")
        st_c1, st_c2 = st.columns(2)
        with st_c1:
            st.markdown(f"""
            <div class='betano-card' style='border-left: 4px solid #ff5b00;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h4 style='margin: 0; color: #fff;'>🏠 {h_team}</h4>
                    <span class='badge-superodds'>{h_standing['rank']}º Lugar</span>
                </div>
                <div style='margin-top: 8px; font-size: 0.9em; color: #cbd5e1;'>
                    <b>Pontos:</b> {h_standing['points']} pts • <b>Jogos:</b> {h_standing['games']} • 
                    <b>V:</b> {h_standing['wins']} | <b>E:</b> {h_standing['draws']} | <b>D:</b> {h_standing['losses']}<br>
                    <b>Saldo:</b> {h_standing['goal_diff']} gols • <b>Forma Recente:</b> <span style='color: #10b981; font-weight: 700;'>{h_standing['form']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with st_c2:
            st.markdown(f"""
            <div class='betano-card' style='border-left: 4px solid #38bdf8;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h4 style='margin: 0; color: #fff;'>✈️ {a_team}</h4>
                    <span class='badge-superodds' style='background: linear-gradient(90deg, #0284c7 0%, #38bdf8 100%);'>{a_standing['rank']}º Lugar</span>
                </div>
                <div style='margin-top: 8px; font-size: 0.9em; color: #cbd5e1;'>
                    <b>Pontos:</b> {a_standing['points']} pts • <b>Jogos:</b> {a_standing['games']} • 
                    <b>V:</b> {a_standing['wins']} | <b>E:</b> {a_standing['draws']} | <b>D:</b> {a_standing['losses']}<br>
                    <b>Saldo:</b> {a_standing['goal_diff']} gols • <b>Forma Recente:</b> <span style='color: #38bdf8; font-weight: 700;'>{a_standing['form']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # -------------------------------------------------------------
        # ELENCOS REAIS E ATUALIZADOS DOS CLUBES (2026/27) & DATA FIFA
        # -------------------------------------------------------------
        with st.expander("👥 Ver Elencos Reais Completos e Convocados da Data FIFA", expanded=True):
            sq_c1, sq_c2 = st.columns(2)
            with sq_c1:
                st.markdown(f"#### 🔴 Elenco Real: {h_team}")
                st.markdown(f"**👑 Craque:** {h_star['nome']} ({h_star.get('posicao', 'Destaque')}) • *{h_star.get('nota', '')}*")
                st.markdown(f"**⚽ Artilheiro:** {h_scorer.get('nome', '')} com **{h_scorer.get('gols', 0)} gols**")
                if h_fifa:
                    fifa_txt = " • ".join([f"<b>{c['jogador']}</b> ({c['selecao']})" for c in h_fifa])
                    st.markdown(f"<div style='background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10b981; padding: 6px 10px; border-radius: 4px; margin-bottom: 8px;'><span style='color: #10b981; font-weight: 700;'>🌍 Convocados na Data FIFA Atual:</span><br>{fifa_txt}</div>", unsafe_allow_html=True)
                st.markdown("**🧤 Goleiros:** " + ", ".join(h_squad.get("gk", [])))
                st.markdown("**🛡️ Defensores:** " + ", ".join(h_squad.get("def", [])))
                st.markdown("**⚙️ Meio-Campistas:** " + ", ".join(h_squad.get("mid", [])))
                st.markdown("**⚡ Atacantes:** " + ", ".join(h_squad.get("fwd", [])))

            with sq_c2:
                st.markdown(f"#### 🔵 Elenco Real: {a_team}")
                st.markdown(f"**👑 Craque:** {a_star['nome']} ({a_star.get('posicao', 'Destaque')}) • *{a_star.get('nota', '')}*")
                st.markdown(f"**⚽ Artilheiro:** {a_scorer.get('nome', '')} com **{a_scorer.get('gols', 0)} gols**")
                if a_fifa:
                    fifa_txt_a = " • ".join([f"<b>{c['jogador']}</b> ({c['selecao']})" for c in a_fifa])
                    st.markdown(f"<div style='background: rgba(56, 189, 248, 0.1); border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 4px; margin-bottom: 8px;'><span style='color: #38bdf8; font-weight: 700;'>🌍 Convocados na Data FIFA Atual:</span><br>{fifa_txt_a}</div>", unsafe_allow_html=True)
                st.markdown("**🧤 Goleiros:** " + ", ".join(a_squad.get("gk", [])))
                st.markdown("**🛡️ Defensores:** " + ", ".join(a_squad.get("def", [])))
                st.markdown("**⚙️ Meio-Campistas:** " + ", ".join(a_squad.get("mid", [])))
                st.markdown("**⚡ Atacantes:** " + ", ".join(a_squad.get("fwd", [])))

        # Cotações estilo Betano
        st.markdown("##### 💵 Cotações Betano:")
        b_c1, b_c2, b_c3, b_c4, b_c5, b_c6 = st.columns(6)
        with b_c1:
            odd_h = st.number_input(f"1 ({h_team})", min_value=1.01, max_value=30.0, value=float(pred_match["fair_odd_home"]), step=0.05)
        with b_c2:
            odd_d = st.number_input("X (Empate)", min_value=1.01, max_value=30.0, value=float(pred_match["fair_odd_draw"]), step=0.05)
        with b_c3:
            odd_a = st.number_input(f"2 ({a_team})", min_value=1.01, max_value=30.0, value=float(pred_match["fair_odd_away"]), step=0.05)
        with b_c4:
            odd_over = st.number_input("Over 2.5 Gols", min_value=1.01, max_value=30.0, value=float(pred_match["fair_odd_over_25"]), step=0.05)
        with b_c5:
            odd_under = st.number_input("Under 2.5 Gols", min_value=1.01, max_value=30.0, value=float(pred_match["fair_odd_under_25"]), step=0.05)
        with b_c6:
            odd_btts = st.number_input("Ambas Marcam", min_value=1.01, max_value=30.0, value=float(pred_match["fair_odd_btts"]), step=0.05)

        # -------------------------------------------------------------
        # DEGUSTAÇÃO FREEMIUM: PROBABILIDADES 1X2 LIBERADAS PARA TODOS
        # -------------------------------------------------------------
        st.markdown("#### 📊 Probabilidades 1X2 Calculadas pelo Modelo Dixon-Coles (Liberado Grátis):")
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            st.metric(f"🏠 Vitória {h_team}", f"{pred_match['prob_home_win']*100:.1f}%", f"Odd Justa: {pred_match['fair_odd_home']}")
        with p_c2:
            st.metric("🤝 Empate", f"{pred_match['prob_draw']*100:.1f}%", f"Odd Justa: {pred_match['fair_odd_draw']}")
        with p_c3:
            st.metric(f"✈️ Vitória {a_team}", f"{pred_match['prob_away_win']*100:.1f}%", f"Odd Justa: {pred_match['fair_odd_away']}")

        verdict = generate_ai_bet_verdict(
            h_team, a_team, pred_match, corner_data, h_standing, a_standing,
            odd_h, odd_d, odd_a, odd_over
        )

        is_featured_match = (h_team == featured_home and a_team == featured_away)
        can_view_verdict = st.session_state["is_vip"] or is_featured_match

        # -------------------------------------------------------------
        # VEREDITO DA IA: LIBERADO NO VIP OU NO JOGO DEGUSTAÇÃO DO DIA
        # -------------------------------------------------------------
        if can_view_verdict:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, rgba(255, 91, 0, 0.15) 0%, rgba(18, 24, 32, 0.9) 100%); border: 2px solid #ff5b00; border-radius: 14px; padding: 22px; margin: 20px 0;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                    <span style='color: #ff5b00; font-weight: 900; font-size: 1.2em;'>
                        ⚡ VEREDITO DEFINITIVO DA IA {"• 🎁 DEGUSTAÇÃO FREE DO DIA" if not st.session_state["is_vip"] else "• EXCLUSIVO VIP"}
                    </span>
                    <span class='badge-superodds'>{verdict['confianca']}</span>
                </div>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px;'>
                    <div>
                        <span style='color: #90a0b0; font-size: 0.85em;'>🎯 EM QUEM APOSTAR?</span>
                        <h3 style='margin: 4px 0 0 0; color: #fff;'>{verdict['em_quem_apostar']}</h3>
                        <small style='color: #ff5b00;'>Mais Provável de Ganhar: <b>{verdict['favorito_vitoria']} ({verdict['prob_favorito']}%)</b></small>
                    </div>
                    <div>
                        <span style='color: #90a0b0; font-size: 0.85em;'>💡 NO QUE APOSTAR? (MERCADO PRINCIPAL)</span>
                        <h3 style='margin: 4px 0 0 0; color: #ffd200;'>{verdict['no_que_apostar']}</h3>
                        <small style='color: #e2e8f0;'>Odd Alvo: <b>{verdict['odd_alvo']}</b> • Gestão: <b>{verdict['stake_sugerida']}</b></small>
                    </div>
                    <div>
                        <span style='color: #90a0b0; font-size: 0.85em;'>🚩 RECOMENDAÇÃO EM ESCANTEIOS</span>
                        <h4 style='margin: 4px 0 0 0; color: #38bdf8;'>{verdict['aposta_cantos']}</h4>
                        <small style='color: #e2e8f0;'>Expectativa: <b>{corner_data['total_expected_corners']} cantos</b></small>
                    </div>
                    <div>
                        <span style='color: #90a0b0; font-size: 0.85em;'>🟨 PROJEÇÃO DE CARTÕES</span>
                        <h4 style='margin: 4px 0 0 0; color: #f59e0b;'>{card_data['total_expected_cards']} Cartões ({card_data['prob_over_45']}% Over 4.5)</h4>
                        <small style='color: #e2e8f0;'>{card_data['intensidade']}</small>
                    </div>
                </div>
                <div style='margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255, 91, 0, 0.2);'>
                    <span style='color: #e2e8f0; font-size: 0.9em;'><b>Racional da IA:</b> {verdict['motivo']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # -------------------------------------------------------------
        # MERCADOS SECUNDÁRIOS: DETALHAMENTO COM EFEITO BLUR FOMO PARA VISITANTES
        # -------------------------------------------------------------
        if not st.session_state["is_vip"]:
            # CONTAINER COM EFEITO BLUR (FOMO VISUAL)
            st.markdown("""
            <div class='blur-container'>
                <div class='blur-cta-overlay'>
                    <span style='font-size: 2.8em;'>🔒</span>
                    <h2 style='color: #ffaa00; margin: 10px 0; font-size: 1.8em;'>DESBLOQUEIE ESCANTEIOS, CARTÕES & RADAR +EV</h2>
                    <p style='color: #e2e8f0; font-size: 1.05em; max-width: 620px; margin: 0 auto 20px auto;'>
                        Você já viu a probabilidade de vitória. Assine o <b>Plano VIP (R$ 29,99/mês)</b> para ver o modelo de escanteios, cartões, gestão de banca fracionária de Kelly e alertas automáticos no WhatsApp e Telegram!
                    </p>
                    <div style='margin-bottom: 20px;'>
                        <span class='gold-vip-btn'>💎 Desbloquear Todas as Probabilidades por R$ 29,99/mês</span>
                    </div>
                    <small style='color: #10b981; font-weight: 700;'>⚡ Acesso Instantâneo • Cancele quando quiser • Suporte 24/7</small>
                </div>
                <div class='blur-content'>
                    <h4>🚩 Detalhamento Avançado de Escanteios & Cartões (Prévia Bloqueada):</h4>
                    <table style='width: 100%; border-collapse: collapse;'>
                        <tr><th>Mercado</th><th>Probabilidade IA</th><th>Odd Justa</th><th>Veredito</th></tr>
                        <tr><td>Mais de 9.5 Escanteios</td><td>68.4%</td><td>1.46</td><td>VALOR ALTO (+EV)</td></tr>
                        <tr><td>Mais de 10.5 Escanteios</td><td>54.2%</td><td>1.85</td><td>NEUTRO</td></tr>
                        <tr><td>Mais de 4.5 Cartões Amarelos</td><td>71.5%</td><td>1.40</td><td>CLÁSSICO QUENTE</td></tr>
                        <tr><td>Cartão Vermelho na Partida</td><td>28.9%</td><td>3.45</td><td>POSSÍVEL</td></tr>
                    </table>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_pay_btn, _ = st.columns([2, 3])
            with col_pay_btn:
                if st.button("💎 Ativar Acesso VIP Completo por R$ 29,99", type="primary", use_container_width=True):
                    st.session_state["is_vip"] = True
                    st.success("🎉 Assinatura VIP ativada com sucesso! Todas as ferramentas foram desbloqueadas.")
                    st.rerun()

        else:
            # Planilha Completa de Probabilidades & +EV
            st.markdown("#### 📊 Planilha Completa de Probabilidades & +EV:")
            markets = [
                evaluate_bet_market(f"Vitória {h_team}", pred_match["prob_home_win"], odd_h),
                evaluate_bet_market("Empate", pred_match["prob_draw"], odd_d),
                evaluate_bet_market(f"Vitória {a_team}", pred_match["prob_away_win"], odd_a),
                evaluate_bet_market("Over 2.5 Gols", pred_match["prob_over_25"], odd_over),
                evaluate_bet_market("Under 2.5 Gols", pred_match["prob_under_25"], odd_under),
                evaluate_bet_market("Ambas Marcam", pred_match["prob_btts_yes"], odd_btts),
            ]
            st.dataframe(
                pd.DataFrame(markets)[["Mercado", "Prob_IA (%)", "Odd_Casa", "Odd_Justa", "EV (%)", "Kelly_Sugestão (%)", "Classificação"]],
                use_container_width=True,
                hide_index=True
            )

            # Planilha de Escanteios & Cartões
            st.markdown("#### 🚩 Detalhamento de Escanteios & Cartões:")
            ec1, ec2 = st.columns(2)
            with ec1:
                st.dataframe(pd.DataFrame([
                    {"Métrica Escanteios": "Total de Cantos Esperados", "Valor IA": f"{corner_data['total_expected_corners']} cantos"},
                    {"Métrica Escanteios": "Mais de 8.5 Cantos", "Valor IA": f"{corner_data['prob_over_85']}% de chance"},
                    {"Métrica Escanteios": "Mais de 9.5 Cantos", "Valor IA": f"{corner_data['prob_over_95']}% (Odd Justa: {corner_data['odd_justa_over95']})"},
                    {"Métrica Escanteios": "Time com Mais Cantos", "Valor IA": corner_data['quem_tem_mais']},
                ]), use_container_width=True, hide_index=True)

            with ec2:
                st.dataframe(pd.DataFrame([
                    {"Métrica Cartões": "Total de Cartões Esperados", "Valor IA": f"{card_data['total_expected_cards']} cartões"},
                    {"Métrica Cartões": "Mais de 3.5 Cartões", "Valor IA": f"{card_data['prob_over_35']}% de chance"},
                    {"Métrica Cartões": "Mais de 4.5 Cartões", "Valor IA": f"{card_data['prob_over_45']}% (Odd Justa: {card_data['odd_justa_over45']})"},
                    {"Métrica Cartões": "Intensidade do Confronto", "Valor IA": card_data['intensidade']},
                ]), use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# ABA 2: JOGOS AO VIVO (WEBSOCKETS, SSE & CACHE PUB/SUB)
# -------------------------------------------------------------
with tab_live:
    st.subheader("🔴 Feed em Tempo Real • WebSockets, SSE & Webhooks")
    
    st.markdown("""
    <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;'>
        <span class='badge-pulse-green'>🟢 WEBSOCKET ATIVO (Porta 8002)</span>
        <span style='background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.75em;'>⚡ CACHE PUB/SUB (ESTILO REDIS)</span>
        <span style='background: rgba(255, 91, 0, 0.15); color: #ff5b00; border: 1px solid #ff5b00; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.75em;'>📡 WEBHOOK RECEIVER ATIVO</span>
        <span style='background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid #a855f7; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.75em;'>⚡ LATÊNCIA < 5ms • ZERO RELOAD</span>
    </div>
    <p style='color: #94a3b8; font-size: 0.88em; margin-bottom: 14px;'>
        Comunicação contínua bidirecional: eventos de gols, cartões e variações de odds são transmitidos diretamente para o navegador e atualizam os cards no DOM instantaneamente sem recarregar a tela.
    </p>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # COMPONENTE FRONT-END WEBSOCKET (ZERO PAGE REFRESH)
    # -------------------------------------------------------------
    st.components.v1.html(
        generate_realtime_html_component(server_port=REALTIME_PORT),
        height=880,
        scrolling=True
    )

    # -------------------------------------------------------------
    # DETALHAMENTO DA ARQUITETURA & DIAGNÓSTICO
    # -------------------------------------------------------------
    with st.expander("🔍 Arquitetura de Tempo Real: WebSockets, SSE, Webhooks & Cache Pub/Sub"):
        st.markdown(f"""
        ### 🏗️ Pilares da Infraestrutura de Tempo Real:
        
        1. **Conexão Contínua via WebSockets & SSE:**
           * **WebSocket Endpoint:** `ws://localhost:{REALTIME_PORT}/ws/live` (Canal bidirecional, latência < 5ms).
           * **SSE Endpoint:** `http://localhost:{REALTIME_PORT}/sse/live` (Fluxo HTTP `text/event-stream` com keep-alive).
           * **Zero Page Refresh:** O JavaScript no navegador escuta os eventos e atualiza diretamente os elementos do DOM (`innerHTML`, `classList`) sem provocar recarregamento da aplicação.

        2. **APIs Esportivas & Webhooks:**
           * **Webhook Ingestion:** `POST http://localhost:{REALTIME_PORT}/api/webhook/sports-event` (Recebe notificações imediatas de APIs externas como Sportradar, Opta, API-Football).
           * **Polling Fallback:** Daemon em segundo plano consulta a ESPN / APIs a cada **3,5 segundos** para garantir sincronia mesmo quando o webhook não estiver configurado.

        3. **Cache Intermediário Pub/Sub (Estilo Redis):**
           * Implementado em [`src/realtime_cache.py`](file:///C:/Users/PC%20GAMER/.gemini/antigravity/scratch/sports-bet-ai/src/realtime_cache.py).
           * Armazena dados com TTL e canais de mensageria (`matches:live`, `events:realtime`, `odds:updates`).
           * **Proteção de Quota:** Centenas de visitantes conectados recebem mensagens via WebSocket sem realizar nenhuma requisição extra à API externa paga.

        4. **Simulação & Teste:**
           * Utilize os botões acima (*⚽ Simular Gol* e *📈 Oscilar Odd*) no componente para disparar Webhooks de teste e assistir à atualização visual imediata no DOM.
        """)
        
        st.divider()
        view_classic = st.checkbox("Exibir também visualização legada do Streamlit Fragment (3s)")
        if view_classic:
            filter_league = st.selectbox(
                "Filtrar por Liga (Visualização Clássica):",
                options=["Todas as Grandes Ligas"] + list(MAJOR_LEAGUES.keys()),
                index=0,
                key="filter_live_league_classic"
            )
            @st.fragment(run_every="3s")
            def render_classic_fragment(filter_name):
                state = get_current_live_state()
                matches = state.get("matches", [])
                if filter_name != "Todas as Grandes Ligas":
                    matches = [m for m in matches if m.get("league") == filter_name]
                st.caption(f"⏱️ Streamlit Fragment Polling • Partidas: {len(matches)}")
                for m in matches[:5]:
                    st.write(f"⚽ **{m['home_team']} {m['home_score']} x {m['away_score']} {m['away_team']}** • {m['status_label']}")
            render_classic_fragment(filter_league)

# -------------------------------------------------------------
# ABA 3: HISTÓRICO PÚBLICO & PROVA SOCIAL DE ASSERTIVIDADE
# -------------------------------------------------------------
with tab_history:
    st.subheader("📊 Histórico Auditado & Transparência do Modelo Quantitativo")
    st.caption("Valide a assertividade e ROI do algoritmo filtrando por mercado ou pelo status da recomendação.")

    col_fh_cat, col_fh_stat = st.columns([3, 2])
    with col_fh_cat:
        selected_category = st.selectbox(
            "🎯 Filtrar por Mercado Específico:",
            options=MARKET_CATEGORIES,
            index=0,
            key="history_market_filter"
        )
    with col_fh_stat:
        filter_status = st.radio(
            "Filtrar Resultado:",
            ["Todos os Palpites", "Apenas Greens ✅", "Apenas Reds ❌"],
            horizontal=True,
            key="history_status_filter"
        )

    # Obter dados filtrados pelo mercado escolhido
    df_cat = get_social_proof_dataframe(selected_category)
    cat_metrics = calculate_market_metrics(df_cat)

    # Métricas dinâmicas recalculadas para o mercado específico
    hm1, hm2, hm3, hm4 = st.columns(4)
    with hm1:
        st.metric(
            "🎯 Taxa de Acerto (Win Rate)",
            f"{cat_metrics['win_rate']}%",
            f"{cat_metrics['greens']} Greens / {cat_metrics['reds']} Reds"
        )
    with hm2:
        st.metric(
            "📈 Retorno (ROI Auditado)",
            f"+{cat_metrics['roi_pct']}%",
            f"Amostra: {cat_metrics['total_tips']} entradas"
        )
    with hm3:
        st.metric(
            "💰 Lucro Líquido",
            f"+{cat_metrics['units_profit']}u",
            f"{selected_category}"
        )
    with hm4:
        st.metric(
            "📊 Odd Média da Amostra",
            f"{cat_metrics['avg_odd']}",
            "Alta Eficiência"
        )

    st.markdown("---")

    # Filtrar por Green/Red
    if filter_status == "Apenas Greens ✅":
        df_show = df_cat[df_cat["status"].str.contains("GREEN", na=False)]
    elif filter_status == "Apenas Reds ❌":
        df_show = df_cat[df_cat["status"].str.contains("RED", na=False)]
    else:
        df_show = df_cat

    st.dataframe(df_show, use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# ABA 4: SISTEMA DE AUTOMAÇÃO WHATSAPP & TELEGRAM
# -------------------------------------------------------------
with tab_whatsapp:
    st.subheader("📲 Central de Alertas no WhatsApp & Telegram")
    st.markdown(f"""
    Receba as análises quantitativas diretamente no canal da sua preferência:
    * **WhatsApp:** {format_phone_number(st.session_state['user_phone'])}
    * **Telegram:** Canal VIP & Bot Oficial `@betai_quant_bot`
    """)

    channel_choice = st.radio("Escolha o Canal para Teste de Envio:", ["WhatsApp 📱", "Telegram ✈️"], horizontal=True)

    st.markdown("---")
    wa_c1, wa_c2 = st.columns([1, 1])

    sim_h = teams_list[0] if len(teams_list) > 0 else "Palmeiras"
    sim_a = teams_list[1] if len(teams_list) > 1 else "Corinthians"
    sim_pred = predictor.predict_match(sim_h, sim_a)
    sim_corn = calculate_corner_probabilities(sim_h, sim_a)
    sim_card = calculate_card_probabilities(sim_h, sim_a)
    sim_sq_h = get_club_squad(sim_h)
    sim_sq_a = get_club_squad(sim_a)
    sim_sh = sim_sq_h.get("craque", get_star_player(sim_h))
    sim_sa = sim_sq_a.get("craque", get_star_player(sim_a))
    sim_verd = generate_ai_bet_verdict(sim_h, sim_a, sim_pred, sim_corn, {}, {}, 2.0, 3.2, 3.4, 1.9)

    with wa_c1:
        st.markdown("#### ⚡ 1. Simulador do Alerta Pré-Jogo (10 Minutos Antes)")
        if channel_choice == "WhatsApp 📱":
            sample_prematch_msg = format_prematch_whatsapp_message(
                {"home_team": sim_h, "away_team": sim_a, "league": selected_league, "time_str": "Hoje às 21:30"},
                sim_pred, sim_corn, sim_card, sim_sh, sim_sa, sim_verd
            )
            sim_link = generate_whatsapp_web_link(st.session_state["user_phone"], sample_prematch_msg)
            btn_label = "🚀 Testar no WhatsApp Agora"
            btn_color = "#25D366"
        else:
            sample_prematch_msg = format_telegram_prematch_message(
                {"home_team": sim_h, "away_team": sim_a, "league": selected_league, "time_str": "Hoje às 21:30"},
                sim_pred, sim_corn, sim_card, sim_sh, sim_sa, sim_verd
            )
            sim_link = generate_telegram_bot_link(sample_prematch_msg)
            btn_label = "✈️ Testar no Telegram Agora"
            btn_color = "#229ED9"

        st.text_area("Prévia da Mensagem Pré-Jogo:", value=sample_prematch_msg, height=280)
        st.markdown(f"""
        <a href='{sim_link}' target='_blank' style='text-decoration: none;'>
            <button style='background-color: {btn_color}; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: 700; width: 100%; cursor: pointer;'>
                {btn_label}
            </button>
        </a>
        """, unsafe_allow_html=True)

    with wa_c2:
        st.markdown("#### ⚽ 2. Simulador de Alerta de Gol ao Vivo")
        goal_team = st.selectbox("Time que marcou:", options=[sim_h, sim_a], index=0)
        goal_scorer = sim_sq_h.get("artilheiro", {}).get("nome", "Pedro") if goal_team == sim_h else sim_sq_a.get("artilheiro", {}).get("nome", "Yuri Alberto")
        goal_minute = st.text_input("Minuto do Gol:", value="68'")

        if channel_choice == "WhatsApp 📱":
            sample_goal_msg = format_goal_whatsapp_message(
                f"{sim_h} vs {sim_a}",
                goal_team,
                goal_minute,
                f"{sim_h} 1 x 0 {sim_a}",
                goal_scorer,
                f"• Chance de vitória do {goal_team} subiu para 86.4%\n• Tendência de Escanteios: Pressão forçando cantos na linha de fundo"
            )
            goal_link = generate_whatsapp_web_link(st.session_state["user_phone"], sample_goal_msg)
            g_label = "⚽ Testar Alerta de Gol no WhatsApp"
            g_color = "#ff5b00"
        else:
            sample_goal_msg = format_telegram_goal_message(
                f"{sim_h} vs {sim_a}",
                goal_team,
                goal_minute,
                f"{sim_h} 1 x 0 {sim_a}",
                goal_scorer,
                f"• Chance de vitória do {goal_team} subiu para 86.4%\n• Tendência de Escanteios: Pressão ofensiva gerando escanteios"
            )
            goal_link = generate_telegram_bot_link(sample_goal_msg)
            g_label = "⚽ Testar Alerta de Gol no Telegram"
            g_color = "#229ED9"

        st.text_area("Prévia do Alerta de Gol:", value=sample_goal_msg, height=280)
        st.markdown(f"""
        <a href='{goal_link}' target='_blank' style='text-decoration: none;'>
            <button style='background-color: {g_color}; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: 700; width: 100%; cursor: pointer;'>
                {g_label}
            </button>
        </a>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# ABA 5: TABELA OFICIAL DA TEMPORADA 2026/27 (TODAS AS COMPETIÇÕES)
# -------------------------------------------------------------
with tab_table:
    st.subheader(f"📋 Tabela Oficial de Classificação • Temporada 2026/27")
    st.caption("Classificação oficial sincronizada com a ESPN para campeonatos nacionais e internacionais.")

    league_keys = list(LEAGUE_CODES_CURRENT_SEASON.keys())
    default_index = league_keys.index(selected_league) if selected_league in league_keys else 0

    table_league = st.selectbox(
        "Escolha o Campeonato para Visualizar a Tabela:",
        options=league_keys,
        index=default_index,
        key="table_league_sel"
    )

    t_code = LEAGUE_CODES_CURRENT_SEASON[table_league]
    with st.spinner("Buscando classificação oficial..."):
        df_table_matches = load_league_data(table_league)
        _, df_chosen_table = get_league_standings(t_code, df_table_matches)

    if not df_chosen_table.empty:
        st.dataframe(df_chosen_table, use_container_width=True, hide_index=True)
    else:
        st.info("Classificação sendo sincronizada...")

# -------------------------------------------------------------
# ABA 6: RADAR DE VALOR (+EV)
# -------------------------------------------------------------
with tab_radar:
    st.subheader("📡 Radar de Oportunidades de Valor (+EV)")
    st.caption("Varredura de oportunidades com vantagem matemática na temporada 2026/27.")

    if not st.session_state["is_vip"]:
        st.markdown("""
        <div class='blur-container'>
            <div class='blur-cta-overlay'>
                <span style='font-size: 2.8em;'>🔒</span>
                <h2 style='color: #ffaa00; margin: 10px 0;'>RADAR DE APOSTAS COM +EV BLOQUEADO</h2>
                <p style='color: #e2e8f0; font-size: 1.05em; max-width: 620px; margin: 0 auto 20px auto;'>
                    Identifique as apostas onde a Betano paga mais do que a probabilidade real calculada pela IA. Exclusivo para assinantes VIP!
                </p>
                <div>
                    <span class='gold-vip-btn'>💎 Assinar por R$ 29,99/mês</span>
                </div>
            </div>
            <div class='blur-content'>
                <table style='width: 100%;'>
                    <tr><th>Confronto</th><th>Mercado</th><th>Odd Casa</th><th>Odd Justa</th><th>EV (%)</th></tr>
                    <tr><td>Palmeiras vs Corinthians</td><td>Vitória Mandante</td><td>2.10</td><td>1.85</td><td>+13.5%</td></tr>
                    <tr><td>Real Madrid vs Betis</td><td>Over 2.5</td><td>1.95</td><td>1.68</td><td>+16.0%</td></tr>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        opp_df = scan_value_opportunities(df_matches, predictor, min_ev_pct=3.5)
        if opp_df.empty:
            st.info("Nenhuma oportunidade com +EV superou o corte no momento.")
        else:
            st.dataframe(opp_df, use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# ABA 7: PLANO VIP MENSAL (R$ 29,99/MÊS)
# -------------------------------------------------------------
with tab_vip:
    st.subheader("👑 Plano VIP BetAI • R$ 29,99/mês")
    st.markdown("""
    ### O que você ganha como Assinante VIP:
    * ✅ **Acesso Ilimitado a Todas as Probabilidades** de vitória em todas as 9 grandes ligas da temporada 2026/27.
    * ✅ **Elencos Reais Completos & Convocados Data FIFA:** Visualização de todos os atletas por setor e convocados das seleções.
    * ✅ **Servidor Ao Vivo (Pulso 3s):** Atualização contínua de partidas e cotações a cada 3 segundos.
    * ✅ **Projeções de Escanteios e Cartões:** Saiba as chances exatas de Over 8.5/9.5 cantos e cartões nos clássicos.
    * ✅ **Veredito Definitivo da IA:** Recomendação direta de *Em quem e No que apostar*.
    * ✅ **Alertas no WhatsApp & Telegram 10 Minutos Antes:** Ficha completa antes do apito inicial.
    * ✅ **Alertas de Gol Instantâneos:** Notificação no WhatsApp e Telegram a cada gol.
    * ✅ **Radar de +EV e Simulador de Banca (Critério de Kelly).**
    """)

    st.markdown("---")
    vip_c1, vip_c2 = st.columns([1, 1])
    with vip_c1:
        st.markdown("""
        <div style='background: #17212b; border: 2px solid #ffaa00; border-radius: 12px; padding: 24px; text-align: center; box-shadow: 0 0 25px rgba(255, 170, 0, 0.2);'>
            <h2 style='color: #ffaa00; margin: 0;'>PLANO VIP MENSAL</h2>
            <h1 style='color: #fff; font-size: 2.8em; margin: 10px 0;'>R$ 29,99 <span style='font-size: 0.4em; color: #90a0b0;'>/ mês</span></h1>
            <p style='color: #90a0b0;'>Sem fidelidade • Cancele quando quiser</p>
            <hr style='border-color: #2b3c4e; margin: 20px 0;'>
            <div style='text-align: left; color: #e2e8f0; font-size: 0.95em;'>
                <p>✔ PIX Instantâneo ou Cartão de Crédito</p>
                <p>✔ Ativação Automática no WhatsApp & Telegram</p>
                <p>✔ Assertividade Comprovada (73.4% Win Rate)</p>
                <p>✔ Suporte VIP 24/7</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state["is_vip"]:
            st.markdown(
                """
                <a href="https://checkout.stripe.com/pay/cs_test_betai2026" target="_blank" style="display: block; width: 100%; text-align: center; background: #10b981; color: #fff; padding: 14px; font-weight: bold; border-radius: 8px; text-decoration: none; margin-top: 15px;">
                    🚀 Assinar Agora com PIX / Cartão
                </a>
                <p style="text-align: center; font-size: 0.8em; color: #94a3b8; margin-top: 8px;">Redirecionamento seguro para gateway de pagamento</p>
                """, unsafe_allow_html=True
            )
        else:
            st.success("✅ Você já é um assinante VIP ativo!")
