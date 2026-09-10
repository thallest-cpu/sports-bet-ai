from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src.current_model import calculate_current_probabilities, calculate_ev, extract_match_winner_odds
from src.nba_intelligence import (
    get_nba_games_today,
    get_nba_live_box_scores,
    get_nba_players,
    get_nba_teams,
    nba_key_configured,
)
from src.sports_data_api import (
    API_FOOTBALL_LEAGUES,
    APP_TIMEZONE,
    api_key_configured,
    clear_api_cache,
    get_api_football_all_live,
    get_api_football_fixture_details,
    get_api_football_fixture_events,
    get_api_football_fixture_lineups,
    get_api_football_fixture_players,
    get_api_football_fixture_statistics,
    get_api_football_fixtures_by_league,
    get_api_football_odds,
    get_api_football_squad,
    get_api_football_standings,
    get_api_football_team_statistics,
    get_api_football_teams,
    get_api_football_today_fixtures,
    get_api_status,
)

st.set_page_config(
    page_title="BetAI Quant Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

NOW = datetime.now(ZoneInfo(APP_TIMEZONE))
SEASON = 2026

# ------------------------------
# Visual
# ------------------------------
st.markdown(
    """
<style>
:root {
  --bg: #0a0e14;
  --panel: #111827;
  --panel2: #151f2e;
  --border: #223047;
  --muted: #94a3b8;
  --text: #f8fafc;
  --accent: #ff6b00;
  --green: #22c55e;
  --red: #ef4444;
  --yellow: #f59e0b;
}
.stApp { background: radial-gradient(circle at 80% 0%, #142034 0%, var(--bg) 36%); color: var(--text); }
[data-testid="stSidebar"] { background: #0d131d; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] * { color: #e5e7eb; }
.block-container { padding-top: 1.2rem; max-width: 1500px; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.brand { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.brand-mark { width:42px; height:42px; border-radius:12px; display:grid; place-items:center; background:linear-gradient(135deg,#ff7a00,#ff3d00); font-size:22px; box-shadow:0 8px 24px rgba(255,107,0,.25); }
.brand-title { font-weight:900; letter-spacing:.3px; font-size:1.05rem; }
.brand-sub { color:var(--muted); font-size:.73rem; }

.hero { background:linear-gradient(135deg,rgba(255,107,0,.13),rgba(17,24,39,.96) 42%,rgba(12,18,28,.98)); border:1px solid var(--border); border-radius:20px; padding:22px 24px; margin:4px 0 18px; box-shadow:0 16px 45px rgba(0,0,0,.2); }
.hero h1 { margin:0; font-size:1.75rem; }
.hero p { margin:7px 0 0; color:var(--muted); }
.status-row { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
.pill { display:inline-flex; align-items:center; gap:6px; border:1px solid var(--border); background:#0d1520; border-radius:999px; padding:6px 10px; color:#cbd5e1; font-size:.78rem; font-weight:700; }
.pill.live { color:#bbf7d0; border-color:rgba(34,197,94,.4); background:rgba(34,197,94,.09); }
.pill.warn { color:#fde68a; border-color:rgba(245,158,11,.4); background:rgba(245,158,11,.09); }

.match-card { border:1px solid var(--border); background:linear-gradient(180deg,#121b28,#0e1621); border-radius:16px; padding:14px 16px; margin:9px 0; }
.match-top { display:flex; justify-content:space-between; gap:12px; align-items:center; color:var(--muted); font-size:.76rem; margin-bottom:9px; }
.match-main { display:grid; grid-template-columns:1fr auto 1fr; gap:14px; align-items:center; }
.team { display:flex; gap:9px; align-items:center; font-weight:800; min-width:0; }
.team.away { justify-content:flex-end; text-align:right; }
.team img { width:30px; height:30px; object-fit:contain; }
.score { font-size:1.35rem; font-weight:950; padding:4px 12px; border-radius:10px; background:#0a1018; border:1px solid #2c3a4f; white-space:nowrap; }
.live-clock { color:#fecaca; font-weight:900; }

.section-title { margin:10px 0 4px; font-size:1.18rem; font-weight:900; }
.muted { color:var(--muted); }
.metric-card { border:1px solid var(--border); background:var(--panel); border-radius:15px; padding:15px; min-height:105px; }
.metric-label { color:var(--muted); font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:.4px; }
.metric-value { margin-top:6px; font-size:1.7rem; font-weight:950; }
.metric-sub { margin-top:2px; color:#cbd5e1; font-size:.77rem; }

.event { border-left:2px solid #334155; padding:5px 0 5px 12px; margin:5px 0; }
.event-time { color:#fbbf24; font-weight:900; display:inline-block; min-width:48px; }
.source-note { border:1px solid var(--border); background:#0d1520; border-radius:12px; padding:10px 12px; color:var(--muted); font-size:.78rem; }

div[data-testid="stRadio"] > div { gap:5px; }
div[data-testid="stRadio"] label { background:#111827; border:1px solid #223047; border-radius:10px; padding:4px 9px; }
div[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
.stButton > button { border-radius:10px; font-weight:800; }

@media (max-width: 800px) {
  .block-container { padding-left: .8rem; padding-right: .8rem; }
  .hero { padding:17px; }
  .hero h1 { font-size:1.35rem; }
  .match-main { grid-template-columns:1fr auto 1fr; gap:7px; }
  .team { font-size:.82rem; }
  .team img { width:24px; height:24px; }
  .score { font-size:1.05rem; padding:4px 8px; }
}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value) -> str:
    return html.escape(str(value or ""))


def fmt_datetime(value: str) -> str:
    if not value:
        return "Horário não disponível"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo(APP_TIMEZONE)).strftime("%d/%m • %H:%M")
    except Exception:
        return str(value)[:16]


def fixture_status(fx: dict) -> tuple[str, bool]:
    status = (fx.get("fixture") or {}).get("status") or {}
    short = str(status.get("short") or "NS")
    live = short in {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}
    elapsed = status.get("elapsed")
    if short == "HT":
        label = "INTERVALO"
    elif live and elapsed is not None:
        label = f"{elapsed}'"
    elif short == "FT":
        label = "ENCERRADO"
    else:
        label = status.get("long") or short
    return str(label), live


def render_match_card(fx: dict) -> None:
    fixture = fx.get("fixture") or {}
    league = fx.get("league") or {}
    teams = fx.get("teams") or {}
    goals = fx.get("goals") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    status_label, is_live = fixture_status(fx)
    score_home = goals.get("home")
    score_away = goals.get("away")
    if score_home is None and score_away is None:
        score = "vs"
    else:
        score = f"{score_home if score_home is not None else 0}  –  {score_away if score_away is not None else 0}"
    logo_h = esc(home.get("logo"))
    logo_a = esc(away.get("logo"))
    logo_h_html = f"<img src='{logo_h}' alt=''>" if logo_h else ""
    logo_a_html = f"<img src='{logo_a}' alt=''>" if logo_a else ""
    status_class = "live-clock" if is_live else ""
    top_right = status_label if is_live or str((fixture.get("status") or {}).get("short")) == "FT" else fmt_datetime(fixture.get("date", ""))

    st.markdown(
        f"""
<div class="match-card">
  <div class="match-top">
    <span>{esc(league.get('country'))} · {esc(league.get('name'))}</span>
    <span class="{status_class}">{esc(top_right)}</span>
  </div>
  <div class="match-main">
    <div class="team">{logo_h_html}<span>{esc(home.get('name','Mandante'))}</span></div>
    <div class="score">{esc(score)}</div>
    <div class="team away"><span>{esc(away.get('name','Visitante'))}</span>{logo_a_html}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def fixture_label(fx: dict) -> str:
    fixture = fx.get("fixture") or {}
    teams = fx.get("teams") or {}
    home = (teams.get("home") or {}).get("name", "Mandante")
    away = (teams.get("away") or {}).get("name", "Visitante")
    status, live = fixture_status(fx)
    when = status if live else fmt_datetime(fixture.get("date", ""))
    return f"{home} × {away} — {when}"


def stat_map(block: dict) -> dict:
    return {str(x.get("type")): x.get("value") for x in block.get("statistics", []) or [] if x.get("type")}


def render_fixture_details(fixture_id: int) -> None:
    detail = get_api_football_fixture_details(fixture_id)
    if not detail:
        st.info("Detalhes avançados não disponíveis nesta fonte/partida.")
        return

    teams = detail.get("teams") or {}
    home_name = (teams.get("home") or {}).get("name", "Mandante")
    away_name = (teams.get("away") or {}).get("name", "Visitante")

    events = detail.get("events") or get_api_football_fixture_events(fixture_id)
    stats = detail.get("statistics") or get_api_football_fixture_statistics(fixture_id)
    lineups = detail.get("lineups") or get_api_football_fixture_lineups(fixture_id)
    players = detail.get("players") or get_api_football_fixture_players(fixture_id)

    d1, d2, d3, d4 = st.tabs(["Linha do tempo", "Estatísticas", "Escalações", "Jogadores"])

    with d1:
        if not events:
            st.info("Nenhum evento disponibilizado ainda.")
        for ev in events:
            tm = ev.get("time") or {}
            elapsed = tm.get("elapsed")
            extra = tm.get("extra")
            minute = "?" if elapsed is None else f"{elapsed}+{extra}'" if extra else f"{elapsed}'"
            typ = str(ev.get("type") or "Evento")
            detail_text = str(ev.get("detail") or typ)
            player = (ev.get("player") or {}).get("name") or ""
            assist = (ev.get("assist") or {}).get("name") or ""
            team = (ev.get("team") or {}).get("name") or ""
            lower = typ.lower()
            icon = "⚽" if lower == "goal" else "🟥" if lower == "card" and "red" in detail_text.lower() else "🟨" if lower == "card" else "🔄" if lower in {"subst", "substitution"} else "•"
            text = f"{icon} {detail_text}"
            if player:
                text += f" — {player}"
            if assist and lower == "goal":
                text += f" (assist. {assist})"
            st.markdown(f"<div class='event'><span class='event-time'>{esc(minute)}</span> {esc(team)} · {esc(text)}</div>", unsafe_allow_html=True)

    with d2:
        if len(stats) < 2:
            st.info("Estatísticas da partida ainda não foram disponibilizadas.")
        else:
            blocks = {((b.get("team") or {}).get("name") or ""): stat_map(b) for b in stats}
            metric_names = []
            for vals in blocks.values():
                for key in vals:
                    if key not in metric_names:
                        metric_names.append(key)
            rows = [{
                "Métrica": metric,
                home_name: blocks.get(home_name, {}).get(metric, "—"),
                away_name: blocks.get(away_name, {}).get(metric, "—"),
            } for metric in metric_names]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with d3:
        if not lineups:
            st.info("Escalações ainda não disponíveis. Normalmente são publicadas perto do início da partida.")
        else:
            cols = st.columns(min(2, len(lineups)))
            for idx, lineup in enumerate(lineups[:2]):
                with cols[idx]:
                    team = lineup.get("team") or {}
                    st.subheader(team.get("name") or "Equipe")
                    st.caption(f"Formação: {lineup.get('formation') or 'não disponível'}")
                    coach = lineup.get("coach") or {}
                    if coach.get("name"):
                        st.write(f"Técnico: **{coach['name']}**")
                    for item in lineup.get("startXI", []) or []:
                        pl = item.get("player") or {}
                        st.write(f"{pl.get('number') or ''} · {pl.get('name') or 'Jogador'}")

    with d4:
        if not players:
            st.info("Estatísticas individuais ainda não disponíveis.")
        else:
            for team_block in players:
                team = team_block.get("team") or {}
                st.markdown(f"### {team.get('name') or 'Equipe'}")
                rows = []
                for item in team_block.get("players", []) or []:
                    p = item.get("player") or {}
                    stat_list = item.get("statistics") or []
                    s = stat_list[0] if stat_list else {}
                    games = s.get("games") or {}
                    goals = s.get("goals") or {}
                    passes = s.get("passes") or {}
                    shots = s.get("shots") or {}
                    cards = s.get("cards") or {}
                    rows.append({
                        "Jogador": p.get("name") or "—",
                        "Nota": games.get("rating") or "—",
                        "Min": games.get("minutes") or 0,
                        "Gols": goals.get("total") or 0,
                        "Assist.": goals.get("assists") or 0,
                        "Chutes": shots.get("total") or 0,
                        "Passes": passes.get("total") or 0,
                        "Amarelos": cards.get("yellow") or 0,
                    })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def source_badge() -> str:
    status = get_api_status()
    source = status.get("source") or "—"
    return f"{source}: {status.get('message') or ''}"


# ------------------------------
# Sidebar
# ------------------------------
with st.sidebar:
    st.markdown(
        """
<div class="brand">
  <div class="brand-mark">⚡</div>
  <div><div class="brand-title">BetAI Quant Pro</div><div class="brand-sub">dados atuais · modelo transparente</div></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()
    selected_league_name = st.selectbox("Competição", list(API_FOOTBALL_LEAGUES.keys()), index=0)
    selected_league_id = API_FOOTBALL_LEAGUES[selected_league_name]
    st.caption(f"Temporada de referência: {SEASON}")

    if api_key_configured():
        st.success("API-Football configurada", icon="✅")
    else:
        st.warning("API-Football sem chave. Fixtures usam fallback ESPN; elencos/estatísticas avançadas ficam indisponíveis.", icon="⚠️")

    if st.button("Atualizar dados agora", use_container_width=True):
        clear_api_cache()
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Nenhum elenco local antigo é apresentado como atual. Quando a fonte não responde, o painel informa indisponibilidade.")

# Header
st.markdown(
    f"""
<div class="hero">
  <h1>Central esportiva em tempo real</h1>
  <p>Jogos atuais, eventos, escalações, jogadores e análise quantitativa sem misturar histórico com informação ao vivo.</p>
  <div class="status-row">
    <span class="pill live">● ONLINE</span>
    <span class="pill">{esc(selected_league_name)}</span>
    <span class="pill">Brasília · {NOW.strftime('%d/%m/%Y %H:%M')}</span>
    <span class="pill {'live' if api_key_configured() else 'warn'}">{'API-Football ativa' if api_key_configured() else 'Fallback limitado'}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

page = st.radio(
    "Navegação",
    ["🔴 Ao vivo", "📅 Hoje", "👥 Times e jogadores", "📈 Análise", "🏆 Tabela", "🏀 NBA"],
    horizontal=True,
    label_visibility="collapsed",
)

# ------------------------------
# Live
# ------------------------------
if page == "🔴 Ao vivo":
    st.markdown("<div class='section-title'>Jogos acontecendo agora</div>", unsafe_allow_html=True)
    st.caption("Atualização automática a cada 15 segundos. O feed principal é global; você pode filtrar pela competição escolhida.")
    only_selected = st.toggle(f"Mostrar somente {selected_league_name}", value=False)

    @st.fragment(run_every="15s")
    def live_fragment():
        matches = get_api_football_all_live()
        if only_selected:
            matches = [m for m in matches if (m.get("league") or {}).get("id") == selected_league_id or (m.get("league") or {}).get("name") == selected_league_name]

        c1, c2, c3 = st.columns(3)
        c1.metric("Ao vivo agora", len(matches))
        c2.metric("Fonte", get_api_status().get("source") or "—")
        c3.metric("Atualizado", datetime.now(ZoneInfo(APP_TIMEZONE)).strftime("%H:%M:%S"))

        if not matches:
            st.info("Nenhuma partida ao vivo no filtro atual. O painel continuará verificando automaticamente.")
            return

        for match in matches[:80]:
            render_match_card(match)

        options = {fixture_label(m): m for m in matches if (m.get("fixture") or {}).get("id")}
        if options:
            st.markdown("### Match Center")
            label = st.selectbox("Abra uma partida", list(options.keys()), key="live_selected_match")
            chosen = options[label]
            fixture_id = int((chosen.get("fixture") or {}).get("id"))
            render_fixture_details(fixture_id)

    live_fragment()

# ------------------------------
# Today
# ------------------------------
elif page == "📅 Hoje":
    st.markdown(f"<div class='section-title'>Jogos de hoje · {esc(selected_league_name)}</div>", unsafe_allow_html=True)
    st.caption(f"Data local: {NOW.strftime('%d/%m/%Y')} · nenhuma partida histórica é usada como 'jogo de hoje'.")

    @st.fragment(run_every="60s")
    def today_fragment():
        fixtures = get_api_football_today_fixtures(selected_league_id)
        if not fixtures:
            st.info("Nenhuma partida encontrada hoje nesta competição.")
            upcoming = get_api_football_fixtures_by_league(selected_league_id, season=SEASON, next_games=10)
            if upcoming:
                st.markdown("### Próximas partidas")
                for fx in upcoming:
                    render_match_card(fx)
            return
        for fx in fixtures:
            render_match_card(fx)

    today_fragment()

# ------------------------------
# Teams
# ------------------------------
elif page == "👥 Times e jogadores":
    st.markdown(f"<div class='section-title'>Times e elenco atual · {esc(selected_league_name)}</div>", unsafe_allow_html=True)
    teams = get_api_football_teams(selected_league_id, season=SEASON)
    if not teams:
        st.warning("Não foi possível obter a lista atual de times pela API-Football. Para evitar informação antiga, nenhum snapshot local será exibido como elenco atual.")
    else:
        team_map = {(t.get("team") or {}).get("name", "Equipe"): t for t in teams}
        team_name = st.selectbox("Escolha um time", sorted(team_map.keys()))
        chosen = team_map[team_name]
        team = chosen.get("team") or {}
        venue = chosen.get("venue") or {}

        h1, h2 = st.columns([1, 5])
        with h1:
            if team.get("logo"):
                st.image(team["logo"], width=92)
        with h2:
            st.title(team.get("name") or team_name)
            bits = [team.get("country"), f"Fundado em {team.get('founded')}" if team.get("founded") else None, venue.get("name")]
            st.caption(" · ".join(str(x) for x in bits if x))

        players = get_api_football_squad(int(team.get("id"))) if team.get("id") else []
        if not players:
            st.info("Elenco atual não disponibilizado pela API neste momento. O sistema não substitui isso por uma lista antiga.")
        else:
            st.success(f"Elenco registrado na fonte atual: {len(players)} jogadores")
            pos_order = ["Goalkeeper", "Defender", "Midfielder", "Attacker"]
            translations = {"Goalkeeper": "Goleiros", "Defender": "Defensores", "Midfielder": "Meio-campistas", "Attacker": "Atacantes"}
            for pos in pos_order:
                group = [p for p in players if p.get("position") == pos]
                if not group:
                    continue
                st.markdown(f"### {translations[pos]}")
                rows = [{
                    "Foto": p.get("photo") or "",
                    "Nº": p.get("number") or "—",
                    "Jogador": p.get("name") or "—",
                    "Idade": p.get("age") or "—",
                } for p in group]
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Foto": st.column_config.ImageColumn("", width="small")},
                )

# ------------------------------
# Analysis
# ------------------------------
elif page == "📈 Análise":
    st.markdown(f"<div class='section-title'>Análise quantitativa · {esc(selected_league_name)}</div>", unsafe_allow_html=True)
    st.caption("Probabilidades calculadas com médias de gols da temporada atual retornadas pela API. Sem odds fictícias e sem confronto histórico apresentado como atual.")

    fixtures = get_api_football_fixtures_by_league(selected_league_id, season=SEASON, next_games=20)
    if not fixtures:
        st.info("Próximas partidas não disponíveis na API neste momento.")
    else:
        options = {fixture_label(fx): fx for fx in fixtures}
        label = st.selectbox("Próxima partida", list(options.keys()))
        match = options[label]
        render_match_card(match)
        fixture = match.get("fixture") or {}
        teams = match.get("teams") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}

        home_stats = get_api_football_team_statistics(selected_league_id, int(home.get("id")), season=SEASON) if home.get("id") else None
        away_stats = get_api_football_team_statistics(selected_league_id, int(away.get("id")), season=SEASON) if away.get("id") else None
        probs = calculate_current_probabilities(home_stats or {}, away_stats or {}) if home_stats and away_stats else None

        if not probs:
            st.warning("A fonte não forneceu estatísticas suficientes da temporada atual para calcular o modelo sem inventar dados.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>{esc(home.get('name'))}</div><div class='metric-value'>{probs['home']}%</div><div class='metric-sub'>Odd justa {probs['fair_home']}</div></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Empate</div><div class='metric-value'>{probs['draw']}%</div><div class='metric-sub'>Odd justa {probs['fair_draw']}</div></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>{esc(away.get('name'))}</div><div class='metric-value'>{probs['away']}%</div><div class='metric-sub'>Odd justa {probs['fair_away']}</div></div>", unsafe_allow_html=True)

            a, b, c, d = st.columns(4)
            a.metric("xG casa", probs["xg_home"])
            b.metric("xG fora", probs["xg_away"])
            c.metric("Over 2.5", f"{probs['over25']}%")
            d.metric("Ambas marcam", f"{probs['btts']}%")

            odds_payload = get_api_football_odds(int(fixture.get("id"))) if fixture.get("id") else []
            odds = extract_match_winner_odds(odds_payload)
            if odds:
                probability_map = {
                    "Home": probs["home"], "1": probs["home"], home.get("name", ""): probs["home"],
                    "Draw": probs["draw"], "X": probs["draw"],
                    "Away": probs["away"], "2": probs["away"], away.get("name", ""): probs["away"],
                }
                ev_rows = []
                for row in odds:
                    sel = str(row["selection"])
                    prob = probability_map.get(sel)
                    if prob is None:
                        lower = sel.lower()
                        if lower in {"home", "1"}: prob = probs["home"]
                        elif lower in {"draw", "x"}: prob = probs["draw"]
                        elif lower in {"away", "2"}: prob = probs["away"]
                    if prob is not None:
                        ev_rows.append({**row, "prob_modelo": prob, "ev_pct": calculate_ev(prob, row["odd"])})
                if ev_rows:
                    df = pd.DataFrame(ev_rows).sort_values("ev_pct", ascending=False)
                    st.markdown("### Odds e valor esperado")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption("EV é uma estimativa matemática baseada no modelo; não é garantia de retorno.")
            else:
                st.info("Odds não disponíveis para esta partida/plano da API. Nenhuma cotação fictícia será criada.")

# ------------------------------
# Standings
# ------------------------------
elif page == "🏆 Tabela":
    st.markdown(f"<div class='section-title'>Classificação atual · {esc(selected_league_name)}</div>", unsafe_allow_html=True)
    groups = get_api_football_standings(selected_league_id, season=SEASON)
    if not groups:
        st.info("Tabela atual não disponível pela API neste momento.")
    else:
        for group_index, group in enumerate(groups):
            if len(groups) > 1:
                st.markdown(f"### Grupo {group_index + 1}")
            rows = []
            for item in group:
                team = item.get("team") or {}
                all_stats = item.get("all") or {}
                goals = all_stats.get("goals") or {}
                rows.append({
                    "#": item.get("rank"),
                    "Time": team.get("name"),
                    "J": all_stats.get("played"),
                    "V": all_stats.get("win"),
                    "E": all_stats.get("draw"),
                    "D": all_stats.get("lose"),
                    "GP": goals.get("for"),
                    "GC": goals.get("against"),
                    "SG": item.get("goalsDiff"),
                    "Pts": item.get("points"),
                    "Forma": item.get("form") or "—",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ------------------------------
# NBA
# ------------------------------
elif page == "🏀 NBA":
    st.markdown("<div class='section-title'>NBA · jogos e elencos</div>", unsafe_allow_html=True)
    if not nba_key_configured():
        st.warning("BALLDONTLIE_API_KEY não configurada nos Secrets. A seção NBA foi mantida, mas não exibe dados fictícios.")
    else:
        live = get_nba_live_box_scores()
        games = live or get_nba_games_today()
        if live:
            st.success(f"{len(live)} jogo(s) ao vivo")
        elif not games:
            st.info("Nenhum jogo NBA encontrado hoje.")
        for game in games:
            home = game.get("home_team") or {}
            away = game.get("visitor_team") or {}
            st.markdown(f"**{away.get('full_name','Visitante')} {game.get('visitor_team_score',0)} × {game.get('home_team_score',0)} {home.get('full_name','Casa')}** · {game.get('status','')}")

        teams = get_nba_teams()
        if teams:
            names = {(t.get("full_name") or t.get("name") or "Equipe"): t for t in teams}
            selected = st.selectbox("Franquia", sorted(names.keys()))
            team = names[selected]
            players = get_nba_players(int(team.get("id"))) if team.get("id") else []
            if players:
                rows = [{"Jogador": f"{p.get('first_name','')} {p.get('last_name','')}".strip(), "Posição": p.get("position") or "—", "Altura": p.get("height") or "—"} for p in players]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
st.markdown(
    f"<div class='source-note'>Fonte consultada nesta sessão: {esc(source_badge())}. Dados LIVE podem variar conforme a cobertura da competição e o plano do provedor. Última renderização: {NOW.strftime('%d/%m/%Y %H:%M:%S')} (Brasília).</div>",
    unsafe_allow_html=True,
)
