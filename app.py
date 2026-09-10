from __future__ import annotations

import html
from src.audit import match_state
from src.dashboard import theme, yesterday, leaders, history, match_slides, ledger_resource
from src.prediction_service import evidence_for
from src.settings import licensed_photo
from src.sports_data_api import source_label, fixtures_on_date
from datetime import datetime
from typing import Any, Dict, List
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
    nba_status,
)
from src.sports_data_api import (
    API_FOOTBALL_LEAGUES,
    APP_TIMEZONE,
    api_daily_quota,
    api_key_configured,
    clear_api_cache,
    current_season,
    get_api_football_fixtures_by_league,
    get_analysis_fixtures,
    get_api_football_odds,
    get_api_football_squad,
    get_api_football_standings,
    get_api_football_team_statistics,
    get_api_football_teams,
    get_api_football_today_fixtures,
    get_api_status,
    football_source_state,
    get_fixture_bundle,
    get_realtime_live_fixtures,
    now_local,
)

st.set_page_config(
    page_title="BetAI Quant Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Theme
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
:root {
  --bg: #080c12;
  --panel: #0f1722;
  --panel2: #121d2b;
  --border: #223047;
  --muted: #8ea0b7;
  --text: #f5f7fb;
  --accent: #ff6b00;
  --green: #24c46b;
  --red: #ff5b68;
  --yellow: #f7bf45;
  --blue: #4ca8ff;
}
html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }
.stApp { background: radial-gradient(circle at 80% -10%, #18243a 0%, var(--bg) 33%); color: var(--text); }
[data-testid="stSidebar"] { background: #0b111a; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] * { color: #e5e7eb; }
.block-container { padding-top: 1.05rem; max-width: 1480px; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.brand { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.brand-mark { width:44px; height:44px; border-radius:13px; display:grid; place-items:center; background:linear-gradient(135deg,#ff7a00,#ff3d00); font-size:23px; box-shadow:0 10px 28px rgba(255,107,0,.26); }
.brand-title { font-weight:950; letter-spacing:.3px; font-size:1.05rem; }
.brand-sub { color:var(--muted); font-size:.72rem; }

.hero { background:linear-gradient(135deg,rgba(255,107,0,.13),rgba(15,23,34,.97) 45%,rgba(9,14,22,.99)); border:1px solid var(--border); border-radius:20px; padding:21px 23px; margin:4px 0 15px; box-shadow:0 16px 45px rgba(0,0,0,.22); }
.hero-top { display:flex; justify-content:space-between; gap:20px; align-items:flex-start; flex-wrap:wrap; }
.hero h1 { margin:0; font-size:1.72rem; line-height:1.1; }
.hero p { margin:7px 0 0; color:var(--muted); max-width:860px; }
.status-row { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
.pill { display:inline-flex; align-items:center; gap:6px; border:1px solid var(--border); background:#0d1520; border-radius:999px; padding:6px 10px; color:#cbd5e1; font-size:.76rem; font-weight:800; }
.pill.live { color:#bbf7d0; border-color:rgba(36,196,107,.40); background:rgba(36,196,107,.08); }
.pill.warn { color:#fde68a; border-color:rgba(247,191,69,.40); background:rgba(247,191,69,.08); }

.match-card { border:1px solid var(--border); background:linear-gradient(180deg,#111b29,#0c141f); border-radius:16px; padding:14px 16px; margin:9px 0; box-shadow:0 8px 26px rgba(0,0,0,.10); }
.match-card.live { border-color:rgba(255,91,104,.34); }
.match-top { display:flex; justify-content:space-between; gap:12px; align-items:center; color:var(--muted); font-size:.75rem; margin-bottom:9px; }
.match-main { display:grid; grid-template-columns:1fr auto 1fr; gap:14px; align-items:center; }
.team { display:flex; gap:9px; align-items:center; font-weight:850; min-width:0; }
.team.away { justify-content:flex-end; text-align:right; }
.team img { width:31px; height:31px; object-fit:contain; }
.score { font-size:1.32rem; font-weight:950; padding:5px 12px; border-radius:10px; background:#070d14; border:1px solid #2c3a4f; white-space:nowrap; }
.live-clock { color:#ff9ba4; font-weight:950; }

.section-head { display:flex; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:8px; margin:10px 0 6px; }
.section-title { font-size:1.18rem; font-weight:950; }
.section-sub { color:var(--muted); font-size:.8rem; }
.metric-card { border:1px solid var(--border); background:linear-gradient(180deg,#111b29,#0e1621); border-radius:15px; padding:15px; min-height:108px; }
.metric-label { color:var(--muted); font-size:.76rem; font-weight:800; text-transform:uppercase; letter-spacing:.45px; }
.metric-value { margin-top:6px; font-size:1.65rem; font-weight:950; }
.metric-sub { margin-top:2px; color:#cbd5e1; font-size:.76rem; }
.event { border-left:2px solid #334155; padding:6px 0 6px 12px; margin:4px 0; }
.event-time { color:#f7bf45; font-weight:950; display:inline-block; min-width:48px; }
.source-note { border:1px solid var(--border); background:#0d1520; border-radius:12px; padding:10px 12px; color:var(--muted); font-size:.77rem; }
.provider-card { border:1px solid var(--border); background:#0d1520; border-radius:13px; padding:12px; }
.provider-ok { color:#86efac; font-weight:900; }
.provider-warn { color:#fde68a; font-weight:900; }

[data-testid="stMetric"] { background:#0f1722; border:1px solid #223047; padding:10px 12px; border-radius:12px; }
div[data-testid="stRadio"] > div { gap:5px; }
div[data-testid="stRadio"] label { background:#111827; border:1px solid #223047; border-radius:10px; padding:4px 9px; }
div[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
.stButton > button { border-radius:10px; font-weight:850; border-color:#334155; }
.stButton > button[kind="primary"] { background:linear-gradient(135deg,#ff7500,#ff4d00); border:0; }

@media (max-width: 800px) {
  .block-container { padding-left:.75rem; padding-right:.75rem; }
  .hero { padding:16px; }
  .hero h1 { font-size:1.35rem; }
  .match-main { grid-template-columns:1fr auto 1fr; gap:6px; }
  .team { font-size:.80rem; gap:5px; }
  .team img { width:24px; height:24px; }
  .score { font-size:1.02rem; padding:4px 7px; }
  .match-card { padding:12px 10px; }
}
</style>
""",
    unsafe_allow_html=True,
)


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def local_now() -> datetime:
    return datetime.now(ZoneInfo(APP_TIMEZONE))


def fmt_datetime(value: str) -> str:
    if not value:
        return "Horário não disponível"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo(APP_TIMEZONE)).strftime("%d/%m • %H:%M")
    except Exception:
        return str(value)[:16]


def fixture_status(fx: Dict[str, Any]) -> tuple[str, bool]:
    status = (fx.get("fixture") or {}).get("status") or {}
    short = str(status.get("short") or "NS").upper()
    live = short in {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}
    elapsed = status.get("elapsed")
    if short == "HT":
        label = "INTERVALO"
    elif live and elapsed is not None:
        label = f"{elapsed}'"
    elif short in {"FT", "AET", "PEN"}:
        label = "ENCERRADO"
    elif short in {"PST", "CANC", "ABD", "SUSP"}:
        label = status.get("long") or short
    else:
        label = status.get("long") or short
    return str(label), live


def fixture_source(fx: Dict[str, Any]) -> str:
    return str((fx.get("fixture") or {}).get("source") or "API-Football")


def render_match_card(fx: Dict[str, Any]) -> None:
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
        score = f"{score_home if score_home is not None else '—'}  –  {score_away if score_away is not None else '—'}"
    logo_h = esc(home.get("logo"))
    logo_a = esc(away.get("logo"))
    logo_h_html = f"<img src='{logo_h}' alt=''>" if logo_h else ""
    logo_a_html = f"<img src='{logo_a}' alt=''>" if logo_a else ""
    status_class = "live-clock" if is_live else ""
    short = str((fixture.get("status") or {}).get("short") or "")
    status_label = match_state(fx) if not is_live else status_label
    top_right = status_label if is_live or short in {"FT", "AET", "PEN"} else f"{status_label} · {fmt_datetime(fixture.get("date", ""))}"
    country = league.get("country") or ""
    comp = league.get("name") or "Competição"
    source = fixture_source(fx)

    st.markdown(
        f"""
<div class="match-card {'live' if is_live else ''}">
  <div class="match-top">
    <span>{esc(country)}{' · ' if country else ''}{esc(comp)} · {esc(source)}</span>
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


def fixture_label(fx: Dict[str, Any]) -> str:
    fixture = fx.get("fixture") or {}
    teams = fx.get("teams") or {}
    home = (teams.get("home") or {}).get("name", "Mandante")
    away = (teams.get("away") or {}).get("name", "Visitante")
    status, live = fixture_status(fx)
    when = status if live else fmt_datetime(fixture.get("date", ""))
    return f"{home} × {away} — {when}"


def stat_map(block: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(x.get("type")): x.get("value")
        for x in block.get("statistics", []) or []
        if isinstance(x, dict) and x.get("type")
    }


def event_icon(event_type: str, detail: str) -> str:
    text = f"{event_type} {detail}".lower()
    if "goal" in text or "gol" in text:
        return "⚽"
    if "red" in text or "vermel" in text:
        return "🟥"
    if "yellow" in text or "amare" in text or "card" in text or "cart" in text:
        return "🟨"
    if "subst" in text or "substitution" in text:
        return "🔄"
    if "var" in text:
        return "📺"
    return "•"


def render_fixture_details(fixture: Dict[str, Any]) -> None:
    bundle = get_fixture_bundle(fixture)
    if not bundle:
        st.info("Detalhes avançados não estão disponíveis nesta fonte/partida agora.")
        return

    teams = fixture.get("teams") or {}
    home_name = (teams.get("home") or {}).get("name", "Mandante")
    away_name = (teams.get("away") or {}).get("name", "Visitante")
    source = bundle.get("source") or fixture_source(fixture)
    st.caption(f"Detalhes carregados de {source}. Atualização sujeita à cobertura do provedor.")

    events = bundle.get("events") or []
    stats = bundle.get("statistics") or []
    lineups = bundle.get("lineups") or []
    players = bundle.get("players") or []

    d1, d2, d3, d4 = st.tabs(["Linha do tempo", "Estatísticas", "Escalações", "Jogadores"])

    with d1:
        if not events:
            st.info("Nenhum evento disponibilizado ainda.")
        else:
            def _event_sort(ev: Dict[str, Any]) -> tuple:
                tm = ev.get("time") or {}
                return (tm.get("elapsed") if tm.get("elapsed") is not None else 999, tm.get("extra") or 0)

            for ev in sorted(events, key=_event_sort):
                tm = ev.get("time") or {}
                elapsed = tm.get("elapsed")
                extra = tm.get("extra")
                minute = "?" if elapsed is None else f"{elapsed}+{extra}'" if extra else f"{elapsed}'"
                typ = str(ev.get("type") or "Evento")
                detail_text = str(ev.get("detail") or typ)
                player = (ev.get("player") or {}).get("name") or ""
                assist = (ev.get("assist") or {}).get("name") or ""
                team = (ev.get("team") or {}).get("name") or ""
                icon = event_icon(typ, detail_text)
                text = f"{icon} {detail_text}"
                if player:
                    text += f" — {player}"
                if assist and "goal" in typ.lower():
                    text += f" (assist. {assist})"
                st.markdown(
                    f"<div class='event'><span class='event-time'>{esc(minute)}</span> {esc(team)} · {esc(text)}</div>",
                    unsafe_allow_html=True,
                )

    with d2:
        if len(stats) < 2:
            st.info("Estatísticas da partida ainda não foram disponibilizadas.")
        else:
            blocks = {((b.get("team") or {}).get("name") or ""): stat_map(b) for b in stats}
            metric_names: List[str] = []
            for values in blocks.values():
                for key in values:
                    if key not in metric_names:
                        metric_names.append(key)
            rows = [{
                "Métrica": metric,
                home_name: blocks.get(home_name, {}).get(metric, "—"),
                away_name: blocks.get(away_name, {}).get(metric, "—"),
            } for metric in metric_names]
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("A fonte não retornou métricas utilizáveis.")

    with d3:
        if not lineups:
            st.info("Escalações ainda não disponíveis. Elas normalmente aparecem perto do início da partida.")
        else:
            cols = st.columns(min(2, len(lineups)))
            for idx, lineup in enumerate(lineups[:2]):
                with cols[idx]:
                    team = lineup.get("team") or {}
                    st.subheader(team.get("name") or "Equipe")
                    formation = lineup.get("formation")
                    if formation:
                        st.caption(f"Formação: {formation}")
                    coach = lineup.get("coach") or {}
                    if coach.get("name"):
                        st.write(f"Técnico: **{coach['name']}**")
                    starters = lineup.get("startXI", []) or []
                    if not starters:
                        st.caption("Titulares ainda não informados.")
                    for item in starters:
                        pl = item.get("player") or {}
                        number = pl.get("number") or ""
                        pos = pl.get("pos") or ""
                        suffix = f" · {pos}" if pos else ""
                        st.write(f"{number} · {pl.get('name') or 'Jogador'}{suffix}")

    with d4:
        if not players:
            st.info("Jogadores da partida ainda não disponíveis.")
        else:
            for team_block in players:
                team = team_block.get("team") or {}
                st.markdown(f"### {team.get('name') or 'Equipe'}")
                rows = []
                has_match_stats = False
                for item in team_block.get("players", []) or []:
                    p = item.get("player") or {}
                    stat_list = item.get("statistics") or []
                    if stat_list:
                        has_match_stats = True
                        s = stat_list[0] or {}
                        games = s.get("games") or {}
                        goals = s.get("goals") or {}
                        passes = s.get("passes") or {}
                        shots = s.get("shots") or {}
                        cards = s.get("cards") or {}
                        rows.append({
                            "Jogador": p.get("name") or "—",
                            "Nota": games.get("rating") or "—",
                            "Min": games.get("minutes") if games.get("minutes") is not None else "—",
                            "Gols": goals.get("total") if goals.get("total") is not None else "—",
                            "Assist.": goals.get("assists") if goals.get("assists") is not None else "—",
                            "Chutes": shots.get("total") if shots.get("total") is not None else "—",
                            "Passes": passes.get("total") if passes.get("total") is not None else "—",
                            "Amarelos": cards.get("yellow") if cards.get("yellow") is not None else "—",
                        })
                    else:
                        rows.append({
                            "Jogador": p.get("name") or "—",
                            "Nº": p.get("number") or "—",
                            "Posição": p.get("pos") or "—",
                            "Titular": "Sim" if p.get("starter") else "—",
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if not has_match_stats and rows:
                    st.caption("Esta fonte disponibilizou a relação de atletas, mas não estatísticas individuais completas.")


def provider_summary() -> str:
    state = football_source_state()
    espn = state["espn"]
    api = state["api"]

    if espn.get("ok") is True:
        espn_txt = "ESPN OK"
    elif espn.get("ok") is False:
        espn_txt = "ESPN indisponível"
    else:
        espn_txt = "ESPN ainda não verificada"

    if api.get("ok") is True:
        api_txt = "API-Football OK"
    elif api.get("ok") is False:
        api_txt = "API-Football indisponível"
    elif state["configured"]:
        api_txt = "API-Football configurada"
    else:
        api_txt = "API-Football sem chave"
    return f"{espn_txt} · {api_txt}"


def provider_pill_class() -> str:
    state = football_source_state()
    return "live" if state["usable"] else "warn"


# -----------------------------------------------------------------------------
# Sidebar and navigation
# -----------------------------------------------------------------------------
theme()

with st.sidebar:
    st.markdown(
        """
<div class="brand">
  <div class="brand-mark">⚡</div>
  <div><div class="brand-title">BetAI Quant Pro</div><div class="brand-sub">V5 · histórico auditável</div></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()
    selected_league_name = st.selectbox("Competição", list(API_FOOTBALL_LEAGUES.keys()), index=0)
    selected_league_id = API_FOOTBALL_LEAGUES[selected_league_name]
    season = current_season(selected_league_id)
    season_label = str(season) if selected_league_id in {71, 13, 11} else f"{season}/{str(season + 1)[-2:]}"
    st.caption(f"Temporada: {season_label}")

    # Pré-valida a fonte gratuita no carregamento da página. A resposta fica
    # em cache, então isso não gera chamadas repetidas a cada componente.
    try:
        get_api_football_today_fixtures(selected_league_id)
    except Exception:
        pass

    source_state = football_source_state()
    api_state = source_state["api"]
    if api_key_configured():
        if api_state.get("ok") is True:
            st.success("API-Football disponível", icon="✅")
        elif api_state.get("ok") is False:
            st.warning("API-Football configurada, mas indisponível agora", icon="⚠️")
        else:
            st.info("API-Football configurada; aguardando primeira validação.", icon="ℹ️")
        quota = api_daily_quota()
        if quota and quota[1] > 0:
            current, limit_day = quota
            st.caption(f"Uso da API hoje: {current}/{limit_day}")
    else:
        st.info("Placar, calendário, times e elencos podem usar ESPN. Análise avançada/odds exige API-Football.", icon="ℹ️")

    if st.button("Atualizar dados agora", use_container_width=True, type="primary"):
        # Keep paid cache and quota protection across manual refreshes.
        from src.sports_data_api import _CACHE
        for cache_key in list(_CACHE):
            if cache_key.startswith("espn|"):
                _CACHE.pop(cache_key, None)
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun()

    with st.expander("Diagnóstico das fontes"):
        status = get_api_status()
        providers = status.get("providers") or {}
        for name, item in providers.items():
            label = "API-Football" if name == "api_football" else "ESPN"
            ok = item.get("ok")
            icon = "✅" if ok is True else "⚠️" if ok is False else "•"
            st.caption(f"{icon} {label}: {item.get('message') or 'aguardando'}")
        st.caption("Nenhum CSV histórico é usado como elenco ou partida atual.")

# Hero
now = local_now()
st.markdown(
    f"""
<div class="hero">
  <div class="hero-top">
    <div>
      <h1>Dados reais. Previsões transparentes.</h1>
      <p>Placar, calendário, elencos, escalações, eventos e análise quantitativa com separação rigorosa entre dados atuais e históricos.</p>
    </div>
  </div>
  <div class="status-row">
    <span class="pill live">● APP ONLINE</span>
    <span class="pill">{esc(selected_league_name)}</span>
    <span class="pill">Brasília · {now.strftime('%d/%m/%Y %H:%M')}</span>
    <span class="pill {provider_pill_class()}">{esc(provider_summary())}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

page = st.radio(
    "Navegação",
    ["🔴 Ao vivo", "📅 Hoje", "🗓 Ontem / Resultados", "👥 Times e jogadores", "📈 Análise", "🏆 Tabela", "🏀 NBA"],
    horizontal=True,
    label_visibility="collapsed",
)

# -----------------------------------------------------------------------------
# Live
# -----------------------------------------------------------------------------
if page == "🔴 Ao vivo":
    st.markdown(
        "<div class='section-head'><div><div class='section-title'>Jogos acontecendo agora</div><div class='section-sub'>Placar atualizado automaticamente nas competições monitoradas.</div></div></div>",
        unsafe_allow_html=True,
    )
    only_selected = st.toggle(f"Mostrar somente {selected_league_name}", value=False)

    @st.fragment(run_every="15s")
    def live_fragment() -> None:
        matches = get_realtime_live_fixtures(selected_league_id if only_selected else None)
        now_live = local_now()

        c1, c2, c3 = st.columns(3)
        c1.metric("Ao vivo agora", len(matches))
        c2.metric("Cobertura", "1 liga" if only_selected else f"{len(API_FOOTBALL_LEAGUES)} ligas",
                  help=selected_league_name if only_selected else "Competições monitoradas")
        c3.metric("Painel consultado", now_live.strftime("%H:%M:%S"))

        if not matches:
            live_state = football_source_state()
            espn_ok = live_state["espn"].get("ok") is True
            api_ok = live_state["api"].get("ok") is True
            if espn_ok or api_ok:
                st.info("Consulta concluída: nenhuma partida ao vivo encontrada no filtro atual. O painel continuará verificando automaticamente.")
            else:
                st.warning("Não foi possível confirmar partidas ao vivo agora porque as fontes estão indisponíveis. Tente novamente mais tarde.")
            upcoming = get_api_football_fixtures_by_league(
                selected_league_id, season=season, next_games=3
            )
            if upcoming:
                st.markdown("### Próximos jogos da competição selecionada")
                for fx in upcoming[:3]:
                    render_match_card(fx)
            return

        for match in matches[:80]:
            render_match_card(match)

        options = {fixture_label(m): m for m in matches if (m.get("fixture") or {}).get("id")}
        if options:
            st.markdown("### Match Center")
            label = st.selectbox("Abra uma partida", list(options.keys()), key="live_selected_match")
            chosen = options[label]
            render_fixture_details(chosen)

    live_fragment()

# -----------------------------------------------------------------------------
# Today
# -----------------------------------------------------------------------------
elif page == "📅 Hoje":
    now_today = local_now()
    st.markdown(
        f"<div class='section-head'><div><div class='section-title'>Jogos de hoje · {esc(selected_league_name)}</div><div class='section-sub'>{now_today.strftime('%d/%m/%Y')} · horário de Brasília</div></div></div>",
        unsafe_allow_html=True,
    )

    @st.fragment(run_every="60s")
    def today_fragment() -> None:
        fixtures, today_ok = fixtures_on_date(selected_league_id, local_now().date())
        if not fixtures:
            today_state = football_source_state()
            if today_ok:
                st.info("Consulta concluída: nenhuma partida encontrada hoje nesta competição.")
            else:
                st.warning("Não foi possível consultar o calendário desta competição agora. Isso não confirma ausência de jogos.")
            upcoming = get_api_football_fixtures_by_league(selected_league_id, season=season, next_games=10)
            if upcoming:
                st.markdown("### Próximas partidas")
                for fx in upcoming:
                    render_match_card(fx)
            return
        match_slides(fixtures)

        options = {fixture_label(fx): fx for fx in fixtures if (fx.get("fixture") or {}).get("id")}
        if options:
            with st.expander("Abrir detalhes de uma partida", expanded=False):
                selected = st.selectbox("Partida", list(options.keys()), key="today_detail_match")
                render_fixture_details(options[selected])

    today_fragment()
    st.subheader("Previsões e resultados auditáveis")
    history(selected_league_id)

# -----------------------------------------------------------------------------
# Teams / current roster
# -----------------------------------------------------------------------------
elif page == "🗓 Ontem / Resultados":
    yesterday(selected_league_id)

elif page == "👥 Times e jogadores":
    leaders(selected_league_id, season)
    st.markdown(
        f"<div class='section-head'><div><div class='section-title'>Times e elenco atual · {esc(selected_league_name)}</div><div class='section-sub'>Elenco consultado na fonte online; sem lista fixa local.</div></div></div>",
        unsafe_allow_html=True,
    )
    teams = get_api_football_teams(selected_league_id, season=season)
    if not teams:
        st.warning("Não foi possível obter a lista atual de times. Para evitar informação antiga, nenhum snapshot local será exibido.")
    else:
        team_map = {(t.get("team") or {}).get("name", "Equipe"): t for t in teams}
        team_name = st.selectbox("Escolha um time", sorted(team_map.keys()))
        chosen = team_map[team_name]
        team = chosen.get("team") or {}
        venue = chosen.get("venue") or {}
        source_hint = team.get("source") or "API-Football"

        h1, h2 = st.columns([1, 5])
        with h1:
            if team.get("logo"):
                st.image(team["logo"], width=92)
        with h2:
            st.title(team.get("name") or team_name)
            bits = [
                team.get("country"),
                f"Fundado em {team.get('founded')}" if team.get("founded") else None,
                venue.get("name"),
                f"Fonte: {source_hint}",
            ]
            st.caption(" · ".join(str(x) for x in bits if x))

        team_id = team.get("id")
        players = get_api_football_squad(
            int(team_id),
            league_id=selected_league_id,
            source_hint=source_hint,
        ) if team_id else []

        if not players:
            st.info("Elenco atual não disponibilizado pela fonte neste momento. O sistema não substitui isso por uma lista antiga.")
        else:
            source_set = sorted({str(p.get("source") or source_hint) for p in players})
            st.success(f"{len(players)} jogadores · fonte: {', '.join(source_set)}")
            pos_order = ["Goalkeeper", "Defender", "Midfielder", "Attacker", "Other"]
            translations = {
                "Goalkeeper": "Goleiros",
                "Defender": "Defensores",
                "Midfielder": "Meio-campistas",
                "Attacker": "Atacantes",
                "Other": "Outros",
            }
            rendered = set()
            for pos in pos_order:
                group = [p for p in players if (p.get("position") or "Other") == pos]
                if not group:
                    continue
                rendered.update(id(p) for p in group)
                st.markdown(f"### {translations[pos]}")
                rows = [{
                    "Foto": licensed_photo(p.get("photo"), p.get("source") or source_hint),
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
            leftover = [p for p in players if id(p) not in rendered]
            if leftover:
                st.markdown("### Outros")
                st.dataframe(pd.DataFrame([{"Jogador": p.get("name") or "—", "Posição": p.get("position") or "—"} for p in leftover]), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
elif page == "📈 Análise":
    st.markdown(
        f"<div class='section-head'><div><div class='section-title'>Análise quantitativa · {esc(selected_league_name)}</div><div class='section-sub'>Modelo Poisson transparente com estatísticas da temporada atual.</div></div></div>",
        unsafe_allow_html=True,
    )
    with st.expander('Como calculamos as probabilidades', expanded=True):
        st.write('Modelo Poisson v1: média entre gols marcados em casa pelo mandante e sofridos fora pelo visitante; cálculo inverso para o visitante. Mínimo de três jogos em cada recorte na temporada selecionada. As médias esperadas ficam entre 0,15 e 4,5 gols; grade de 0 a 14 gols normalizada para 100%.')
        st.write('1 = vitória da casa; X = empate; 2 = vitória de fora em 90 minutos + acréscimos. Prorrogação e pênaltis excluídos. Arredondamentos podem causar diferença de 0,1 ponto. Sem ajuste por lesões, escalações ou força dos adversários, nem calibração comprovada; amostras pequenas são instáveis.')
        st.caption('Uma estimativa de 60% não é 60% de acerto comprovado e não garante retorno. Só o histórico registrado antes do jogo pode produzir uma taxa observada.')
    st.caption("A análise só é exibida quando a API fornece estatísticas atuais suficientes. Odds inexistentes nunca são simuladas.")

    fixtures = get_analysis_fixtures(selected_league_id, season=season, next_games=20)
    if not fixtures:
        st.info("Próximas partidas não disponíveis neste momento.")
    else:
        options = {fixture_label(fx): fx for fx in fixtures}
        label = st.selectbox("Próxima partida", list(options.keys()))
        match = options[label]
        render_match_card(match)
        fixture = match.get("fixture") or {}
        teams = match.get("teams") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}

        # IDs ESPN não são IDs API-Football. Portanto, a análise só roda quando
        # os IDs da fixture vieram da API-Football. Isso evita consultar time errado.
        if fixture_source(match).upper() == "ESPN":
            st.info("O calendário desta partida veio da ESPN. Para calcular o modelo sem misturar IDs de provedores, selecione uma partida quando a API-Football estiver disponível como fonte de fixtures avançadas.")
        else:
            home_stats = get_api_football_team_statistics(selected_league_id, int(home.get("id")), season=season) if home.get("id") else None
            away_stats = get_api_football_team_statistics(selected_league_id, int(away.get("id")), season=season) if away.get("id") else None
            evidence = evidence_for(home_stats or {}, away_stats or {}, selected_league_id, season)
            probs = calculate_current_probabilities(home_stats or {}, away_stats or {}) if evidence and match_state(match) == 'Agendado' else None

            if not probs:
                st.warning("A fonte não forneceu estatísticas suficientes da temporada atual para calcular o modelo sem inventar dados.")
            else:
                ledger, storage_error = ledger_resource()
                if ledger:
                    try:
                        inserted = ledger.record(match, probs, evidence)
                        st.caption('Previsão pré-jogo registrada com evidências.' if inserted else 'O registro original é preservado; esta consulta não o substitui.')
                    except Exception:
                        st.warning('Não foi possível registrar a previsão. Esta estimativa não entra na taxa de acerto.')
                else:
                    st.info(storage_error or 'Estimativa não registrada: histórico permanente aguardando banco de dados.')
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"<div class='metric-card'><div class='metric-label'>{esc(home.get('name'))}</div><div class='metric-value'>{probs['home']}%</div><div class='metric-sub'>Odd justa {probs['fair_home']}</div></div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div class='metric-card'><div class='metric-label'>Empate</div><div class='metric-value'>{probs['draw']}%</div><div class='metric-sub'>Odd justa {probs['fair_draw']}</div></div>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<div class='metric-card'><div class='metric-label'>{esc(away.get('name'))}</div><div class='metric-value'>{probs['away']}%</div><div class='metric-sub'>Odd justa {probs['fair_away']}</div></div>", unsafe_allow_html=True)

                a, b, c, d = st.columns(4)
                a.metric("Gols esperados · casa", probs["xg_home"])
                b.metric("Gols esperados · fora", probs["xg_away"])
                c.metric("Over 2.5", f"{probs['over25']}%")
                d.metric("Ambas marcam", f"{probs['btts']}%")

                fixture_id = fixture.get("id")
                odds_payload = get_api_football_odds(int(fixture_id)) if fixture_id else []
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
                            if lower in {"home", "1"}:
                                prob = probs["home"]
                            elif lower in {"draw", "x"}:
                                prob = probs["draw"]
                            elif lower in {"away", "2"}:
                                prob = probs["away"]
                        if prob is not None:
                            ev_rows.append({**row, "Prob. modelo (%)": prob, "EV (%)": calculate_ev(prob, row["odd"])})
                    if ev_rows:
                        df = pd.DataFrame(ev_rows).sort_values("EV (%)", ascending=False)
                        st.markdown("### Odds e valor esperado")
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.caption("EV é estimativa matemática, não promessa de lucro. Aposte com responsabilidade.")
                else:
                    st.info("Odds não disponíveis para esta partida/plano da API. Nenhuma cotação fictícia será criada.")

# -----------------------------------------------------------------------------
# Standings
# -----------------------------------------------------------------------------
elif page == "🏆 Tabela":
    st.markdown(
        f"<div class='section-head'><div><div class='section-title'>Classificação atual · {esc(selected_league_name)}</div><div class='section-sub'>Tabela consultada online.</div></div></div>",
        unsafe_allow_html=True,
    )
    groups = get_api_football_standings(selected_league_id, season=season)
    if not groups:
        st.info("Tabela atual não disponível neste momento.")
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

# -----------------------------------------------------------------------------
# NBA
# -----------------------------------------------------------------------------
elif page == "🏀 NBA":
    st.markdown("<div class='section-head'><div><div class='section-title'>NBA</div><div class='section-sub'>Jogos e elencos sem dados de demonstração.</div></div></div>", unsafe_allow_html=True)
    if not nba_key_configured():
        st.info("NBA ainda não está ativada neste site. O administrador precisa conectar a fonte de dados da NBA antes de liberar jogos e elencos.")
    else:
        live = get_nba_live_box_scores()
        games = live or get_nba_games_today()
        if live:
            st.success(f"{len(live)} jogo(s) ao vivo")
        elif not games:
            state = nba_status('games')
            (st.info if state.get('ok') else st.warning)('Consulta concluída: nenhum jogo NBA encontrado hoje.' if state.get('ok') else state.get('message'))
        for game in games:
            home = game.get("home_team") or {}
            away = game.get("visitor_team") or {}
            hs = game.get("home_team_score")
            vs = game.get("visitor_team_score")
            score = f"{vs if vs is not None else '—'} × {hs if hs is not None else '—'}"
            st.markdown(f"**{away.get('full_name','Visitante')} {score} {home.get('full_name','Casa')}** · {game.get('status','')}")

        teams = get_nba_teams()
        if teams:
            names = {(t.get("full_name") or t.get("name") or "Equipe"): t for t in teams}
            selected = st.selectbox("Franquia", sorted(names.keys()))
            team = names[selected]
            players = get_nba_players(int(team.get("id"))) if team.get("id") else []
            if not players:
                st.info("Elenco ativo não disponibilizado pela fonte/plano. Jogadores históricos não são usados como elenco atual.")
            if players:
                rows = [{
                    "Jogador": f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                    "Posição": p.get("position") or "—",
                    "Altura": p.get("height") or "—",
                } for p in players]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
for provider, state in get_api_status().get('providers', {}).items():
    st.caption(f"{'API-Football' if provider == 'api_football' else 'ESPN'} · {source_label(state)} · {state.get('message')} · {state.get('at') or 'Sem consulta'}")
footer_now = local_now()
st.markdown(
    f"<div class='source-note'><b>Fontes:</b> {esc(provider_summary())}. Placar ao vivo prioriza ESPN para preservar a quota diária da API-Football; dados avançados usam API-Football quando disponível. Nenhum CSV histórico é apresentado como dado atual. Página renderizada: {footer_now.strftime('%d/%m/%Y %H:%M:%S')} (Brasília). Consultas podem usar cache dentro do prazo; o horário do painel não garante atualização interna do provedor.<br><br><b>Aviso:</b> probabilidades são estimativas estatísticas e não garantem resultados financeiros.</div>",
    unsafe_allow_html=True,
)
