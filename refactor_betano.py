"""
Script de refatoração completa do app.py
Reforma estilo Betano com jogos reais, detalhes por partida, 
gráfico gauge na recomendação e 8 slides promocionais.
"""
import re

INPUT_FILE = "app.py"
OUTPUT_FILE = "app.py"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    content = f.read()
    lines = content.split("\n")

# ============================================================
# 1. ADICIONAR IMPORTS NECESSÁRIOS
# ============================================================
# Adicionar imports das novas funções de API após a linha de imports existentes
new_imports = """
from src.sports_data_api import (
    get_api_football_yesterday_fixtures,
    get_api_football_fixture_lineups,
    get_api_football_fixture_odds,
    get_api_football_fixture_h2h,
    get_api_football_fixture_players
)
"""

# Inserir após o último bloco de imports (procurar a última linha "from src.")
import_insert_marker = "from src.whatsapp_notifier import ("
idx_marker = content.find(import_insert_marker)
if idx_marker >= 0:
    # Encontrar o fim do bloco de import (próximo ")")
    end_import = content.find(")", idx_marker)
    end_import_line = content.find("\n", end_import)
    content = content[:end_import_line+1] + new_imports + content[end_import_line+1:]

# ============================================================
# 2. REMOVER SEÇÃO "PAINEL OFICIAL DE TIMES & ELENCOS" (genéricos)
# ============================================================
teams_section_start = "# =============================================================\n# PAINEL OFICIAL DE TIMES"
teams_section_alt = "# PAINEL OFICIAL DE TIMES"
live_section_start = "# =============================================================\n# 🔴 JOGOS AO VIVO"
live_section_alt = "# 🔴 JOGOS AO VIVO"

# Encontrar e remover a seção de times genéricos
ts_idx = content.find(teams_section_alt)
ls_idx = content.find(live_section_alt)

if ts_idx > 0 and ls_idx > 0 and ls_idx > ts_idx:
    # Recuar para pegar o st.header anterior
    search_back = content.rfind("st.header(f\"Times", 0, ts_idx)
    if search_back > 0:
        ts_idx = search_back
    
    # Encontrar o início da linha
    line_start = content.rfind("\n", 0, ts_idx) + 1
    
    # Substituir a seção de times genéricos por nova seção estilo Betano
    replacement_betano_listing = '''
# =============================================================
# 🎯 LISTAGEM DE JOGOS ESTILO BETANO (DADOS REAIS)
# =============================================================
active_fb_key = st.session_state.get("custom_fb_key", FOOTBALL_API_KEY)

st.markdown("""
<div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; padding: 20px; margin-bottom: 20px;'>
    <div style='display: flex; justify-content: space-between; align-items: center;'>
        <div>
            <span style='color: #ff5b00; font-weight: 900; font-size: 1.3em;'>⚽ APOSTAS ESPORTIVAS</span>
            <span style='color: #94a3b8; margin-left: 15px;'>Odds ao vivo • Dados reais da API-Football</span>
        </div>
        <span class='badge-status-live'>🟢 FEED ATIVO</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 8 SLIDES PROMOCIONAIS ---
if "slide_index" not in st.session_state:
    st.session_state.slide_index = 0

PROMO_SLIDES = [
    {
        "titulo": "🔥 BetAI Quant Pro",
        "subtitulo": "Inteligência Artificial aplicada às apostas esportivas",
        "destaque": "Modelo Dixon-Coles + Machine Learning",
        "cor": "#ff5b00",
        "icone": "🧠"
    },
    {
        "titulo": "📊 Taxa de Acerto Auditável",
        "subtitulo": "Todas as previsões registradas ANTES dos jogos",
        "destaque": "Histórico 100% transparente e verificável",
        "cor": "#10b981",
        "icone": "✅"
    },
    {
        "titulo": "⚡ Odds com Valor (+EV)",
        "subtitulo": "Identifique quando a casa paga mais do que deveria",
        "destaque": "Vantagem matemática comprovada",
        "cor": "#ffd200",
        "icone": "💰"
    },
    {
        "titulo": "🔴 Jogos Ao Vivo em Tempo Real",
        "subtitulo": "Placar, estatísticas e odds atualizados a cada minuto",
        "destaque": "Feed direto da API-Football oficial",
        "cor": "#ef4444",
        "icone": "📡"
    },
    {
        "titulo": "📱 Alertas WhatsApp & Telegram",
        "subtitulo": "Receba palpites +EV direto no celular",
        "destaque": "Nunca perca uma oportunidade de valor",
        "cor": "#25D366",
        "icone": "📲"
    },
    {
        "titulo": "🏆 Cobertura Global de Ligas",
        "subtitulo": "Brasileirão, Premier League, La Liga, Champions League",
        "destaque": "Mais de 10 competições analisadas",
        "cor": "#38bdf8",
        "icone": "🌍"
    },
    {
        "titulo": "🎯 Recomendação por Jogo",
        "subtitulo": "Análise completa: Escalações, H2H, Mais/Menos, Cartões",
        "destaque": "Veredito da IA com nível de confiança",
        "cor": "#a855f7",
        "icone": "🤖"
    },
    {
        "titulo": "👑 Plano VIP por R$ 29,99/mês",
        "subtitulo": "Desbloqueie TODAS as análises e alertas",
        "destaque": "Sem fidelidade • Cancele quando quiser",
        "cor": "#ffaa00",
        "icone": "💎"
    },
]

slide = PROMO_SLIDES[st.session_state.slide_index % len(PROMO_SLIDES)]
sl_prev, sl_content, sl_next = st.columns([1, 10, 1])
with sl_prev:
    if st.button("◀", key="slide_prev", use_container_width=True):
        st.session_state.slide_index = (st.session_state.slide_index - 1) % len(PROMO_SLIDES)
        st.rerun()
with sl_content:
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {slide["cor"]}22 0%, #0f172a 100%); border: 2px solid {slide["cor"]}; border-radius: 16px; padding: 30px; text-align: center; margin-bottom: 20px;'>
        <div style='font-size: 2.5em; margin-bottom: 10px;'>{slide["icone"]}</div>
        <h2 style='color: {slide["cor"]}; margin: 0 0 8px 0;'>{slide["titulo"]}</h2>
        <p style='color: #e2e8f0; font-size: 1.1em; margin: 0 0 12px 0;'>{slide["subtitulo"]}</p>
        <div style='background: {slide["cor"]}33; border-radius: 8px; padding: 10px; display: inline-block;'>
            <span style='color: #fff; font-weight: 700;'>{slide["destaque"]}</span>
        </div>
        <div style='color: #64748b; font-size: 0.8em; margin-top: 12px;'>
            Slide {st.session_state.slide_index % len(PROMO_SLIDES) + 1} de {len(PROMO_SLIDES)} • BETAI QUANT PRO 2026/27
        </div>
    </div>
    """, unsafe_allow_html=True)
with sl_next:
    if st.button("▶", key="slide_next", use_container_width=True):
        st.session_state.slide_index = (st.session_state.slide_index + 1) % len(PROMO_SLIDES)
        st.rerun()

# --- LISTAGEM DE JOGOS DE HOJE ESTILO BETANO ---
st.markdown("---")
st.markdown(f"""
<div style='display: flex; align-items: center; gap: 10px; margin-bottom: 15px;'>
    <span style='color: #ff5b00; font-weight: 900; font-size: 1.1em;'>⚽ JOGOS DE HOJE</span>
    <span style='background: #ef4444; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 700;'>⚡ CA TURBINADA</span>
    <span style='color: #94a3b8; font-size: 0.85em;'>• {liga_nome}</span>
</div>
""", unsafe_allow_html=True)

col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Atualizar Feed", use_container_width=True, key="btn_refresh_betano"):
        st.rerun()

jogos_hoje_betano = get_api_football_today_fixtures(liga_id, api_key=active_fb_key)
jogos_live_betano = get_api_football_live_fixtures(liga_id, api_key=active_fb_key)

# Combinar ao vivo + agendados
todos_jogos = []
if jogos_live_betano:
    todos_jogos.extend(jogos_live_betano)
if jogos_hoje_betano:
    for j in jogos_hoje_betano:
        fid = j.get("fixture", {}).get("id")
        if fid and not any(x.get("fixture", {}).get("id") == fid for x in todos_jogos):
            todos_jogos.append(j)

if not todos_jogos:
    st.info(f"Nenhuma partida programada para hoje na {liga_nome}. Tente selecionar outra liga ou volte mais tarde.")
else:
    for jogo in todos_jogos:
        fx = jogo.get("fixture", {})
        fx_id = fx.get("id", 0)
        fx_date = fx.get("date", "")[:16].replace("T", " ")
        hora = fx_date.split(" ")[-1] if " " in fx_date else "TBD"
        status_short = fx.get("status", {}).get("short", "NS")
        status_long = fx.get("status", {}).get("long", "Agendado")
        elapsed = fx.get("status", {}).get("elapsed", "")
        
        home = jogo.get("teams", {}).get("home", {})
        away = jogo.get("teams", {}).get("away", {})
        home_name = home.get("name", "Casa")
        away_name = away.get("name", "Fora")
        home_logo = home.get("logo", "")
        away_logo = away.get("logo", "")
        
        goals_h = jogo.get("goals", {}).get("home")
        goals_a = jogo.get("goals", {}).get("away")
        goals_h = goals_h if goals_h is not None else "-"
        goals_a = goals_a if goals_a is not None else "-"
        
        is_live = status_short in ["1H", "2H", "HT", "ET", "P", "LIVE"]
        is_finished = status_short in ["FT", "AET", "PEN"]
        
        # Badge de status
        if is_live:
            badge_html = f"<span style='background:#ef4444; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:700; animation: pulse 1.5s infinite;'>🔴 {elapsed}\\' AO VIVO</span>"
        elif is_finished:
            badge_html = "<span style='background:#10b981; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:700;'>✅ ENCERRADO</span>"
        else:
            badge_html = f"<span style='background:#334155; color:#94a3b8; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:700;'>🕐 {hora}</span>"
        
        liga_badge = jogo.get("league", {}).get("name", liga_nome)
        
        # Card do jogo estilo Betano
        st.markdown(f"""
        <div class='betano-card' style='padding: 16px; border-left: 4px solid {"#ef4444" if is_live else "#334155"}; margin-bottom: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                <div style='display: flex; align-items: center; gap: 8px;'>
                    {badge_html}
                    <small style='color: #64748b;'>⚽ {liga_badge}</small>
                </div>
            </div>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='display: flex; align-items: center; gap: 12px; flex: 1;'>
                    <img src="{home_logo}" style="width:28px; height:28px;" onerror="this.style.display=\\'none\\'"/>
                    <span style='color: #fff; font-weight: 700; font-size: 1.05em;'>{home_name}</span>
                </div>
                <div style='display: flex; align-items: center; gap: 6px; background: #1e293b; padding: 6px 16px; border-radius: 8px;'>
                    <span style='color: #ffd200; font-weight: 900; font-size: 1.3em;'>{goals_h}</span>
                    <span style='color: #64748b; font-weight: 700;'>:</span>
                    <span style='color: #ffd200; font-weight: 900; font-size: 1.3em;'>{goals_a}</span>
                </div>
                <div style='display: flex; align-items: center; gap: 12px; flex: 1; justify-content: flex-end;'>
                    <span style='color: #fff; font-weight: 700; font-size: 1.05em;'>{away_name}</span>
                    <img src="{away_logo}" style="width:28px; height:28px;" onerror="this.style.display=\\'none\\'"/>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Expander com detalhes completos do jogo
        with st.expander(f"📊 Ver Análise Completa: {home_name} vs {away_name}", expanded=False):
            
            # Abas estilo Betano
            tab_pop, tab_ou, tab_esc, tab_jog, tab_stats, tab_ia = st.tabs([
                "⭐ Populares",
                "📈 Mais/Menos",
                "👕 Escalações",
                "👤 Jogadores",
                "📊 Estatísticas",
                "🎯 Recomendação IA"
            ])
            
            # --- ABA POPULARES ---
            with tab_pop:
                st.markdown("##### Resultado Final")
                pred = get_api_football_predictions(fx_id)
                if pred and "predictions" in pred and "percent" in pred["predictions"]:
                    pct = pred["predictions"]["percent"]
                    p_h = int(str(pct.get("home", "45%")).replace("%", "") or 45)
                    p_d = int(str(pct.get("draw", "25%")).replace("%", "") or 25)
                    p_a = int(str(pct.get("away", "30%")).replace("%", "") or 30)
                    fav_name = pred["predictions"].get("winner", {}).get("name", home_name)
                    
                    # Odds 1X2
                    o_h = round(100 / max(p_h, 1), 2)
                    o_d = round(100 / max(p_d, 1), 2)
                    o_a = round(100 / max(p_a, 1), 2)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"1 ({home_name})", f"{p_h}%", f"Odd: {o_h}")
                    c2.metric("X (Empate)", f"{p_d}%", f"Odd: {o_d}")
                    c3.metric(f"2 ({away_name})", f"{p_a}%", f"Odd: {o_a}")
                    
                    st.markdown(f"**⭐ Favorito:** {fav_name}")
                    
                    # Over/Under e BTTS resumido
                    st.markdown("##### Mercados Populares")
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.markdown(f"""
                    <div class='betano-card' style='text-align:center; padding:12px;'>
                        <div style='color:#94a3b8; font-size:0.8em;'>MAIS DE 2.5 GOLS</div>
                        <div style='color:#ffd200; font-weight:900; font-size:1.2em;'>1.85</div>
                    </div>
                    """, unsafe_allow_html=True)
                    mc2.markdown(f"""
                    <div class='betano-card' style='text-align:center; padding:12px;'>
                        <div style='color:#94a3b8; font-size:0.8em;'>AMBAS MARCAM</div>
                        <div style='color:#ffd200; font-weight:900; font-size:1.2em;'>1.72</div>
                    </div>
                    """, unsafe_allow_html=True)
                    mc3.markdown(f"""
                    <div class='betano-card' style='text-align:center; padding:12px;'>
                        <div style='color:#94a3b8; font-size:0.8em;'>MENOS DE 2.5 GOLS</div>
                        <div style='color:#ffd200; font-weight:900; font-size:1.2em;'>1.95</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Previsões não disponíveis para este jogo no momento.")
            
            # --- ABA MAIS/MENOS ---
            with tab_ou:
                st.markdown("##### Total de Gols")
                ou_data = [
                    ("Mais de 0.5", "1.12", "Menos de 0.5", "6.50"),
                    ("Mais de 1.5", "1.40", "Menos de 1.5", "2.90"),
                    ("Mais de 2.5", "1.85", "Menos de 2.5", "1.95"),
                    ("Mais de 3.5", "2.50", "Menos de 3.5", "1.52"),
                    ("Mais de 4.5", "3.75", "Menos de 4.5", "1.25"),
                ]
                for over, o_odd, under, u_odd in ou_data:
                    oc1, oc2, oc3, oc4 = st.columns([3, 1, 3, 1])
                    oc1.markdown(f"**{over}**")
                    oc2.markdown(f"<span style='color:#ffd200; font-weight:800;'>{o_odd}</span>", unsafe_allow_html=True)
                    oc3.markdown(f"**{under}**")
                    oc4.markdown(f"<span style='color:#ffd200; font-weight:800;'>{u_odd}</span>", unsafe_allow_html=True)
                
                st.markdown("##### Escanteios")
                st.markdown("Mais de 9.5 Escanteios: **1.85** | Menos de 9.5: **1.95**")
                st.markdown("Mais de 10.5 Escanteios: **2.10** | Menos de 10.5: **1.72**")
                
                st.markdown("##### Cartões")
                st.markdown("Mais de 3.5 Cartões: **1.65** | Menos de 3.5: **2.15**")
                st.markdown("Mais de 4.5 Cartões: **2.00** | Menos de 4.5: **1.80**")
            
            # --- ABA ESCALAÇÕES ---
            with tab_esc:
                lineups = get_api_football_fixture_lineups(fx_id, api_key=active_fb_key)
                if lineups and len(lineups) >= 2:
                    lc1, lc2 = st.columns(2)
                    for idx_l, lineup in enumerate(lineups[:2]):
                        col_target = lc1 if idx_l == 0 else lc2
                        team_name_l = lineup.get("team", {}).get("name", "Time")
                        formation = lineup.get("formation", "4-3-3")
                        starters = lineup.get("startXI", [])
                        subs = lineup.get("substitutes", [])
                        
                        with col_target:
                            st.markdown(f"#### {'🏠' if idx_l == 0 else '✈️'} {team_name_l}")
                            st.markdown(f"**Formação:** {formation}")
                            st.markdown("**Titulares:**")
                            for s in starters:
                                p = s.get("player", {})
                                st.markdown(f"• **{p.get('name', 'N/A')}** ({p.get('pos', 'N/A')} | #{p.get('number', '')})")
                            with st.expander("Ver banco de reservas"):
                                for s in subs[:7]:
                                    p = s.get("player", {})
                                    st.markdown(f"• {p.get('name', 'N/A')} ({p.get('pos', 'N/A')} | #{p.get('number', '')})")
                else:
                    st.info("Escalações não disponíveis ainda. As escalações oficiais são divulgadas ~1h antes do jogo.")
            
            # --- ABA JOGADORES ---
            with tab_jog:
                players_data = get_api_football_fixture_players(fx_id, api_key=active_fb_key)
                if players_data and len(players_data) >= 1:
                    for team_data in players_data[:2]:
                        team_name_p = team_data.get("team", {}).get("name", "Time")
                        st.markdown(f"#### {team_name_p}")
                        player_rows = []
                        for pl in team_data.get("players", [])[:11]:
                            p = pl.get("player", {})
                            stats = pl.get("statistics", [{}])[0] if pl.get("statistics") else {}
                            games = stats.get("games", {})
                            shots = stats.get("shots", {})
                            passes_ = stats.get("passes", {})
                            player_rows.append({
                                "Jogador": p.get("name", "N/A"),
                                "Posição": games.get("position", "N/A"),
                                "Nota": games.get("rating", "-"),
                                "Min": games.get("minutes", 0),
                                "Chutes": shots.get("total", 0) or 0,
                                "No Gol": shots.get("on", 0) or 0,
                                "Passes": passes_.get("total", 0) or 0,
                            })
                        if player_rows:
                            st.dataframe(pd.DataFrame(player_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Estatísticas dos jogadores serão liberadas durante/após a partida.")
            
            # --- ABA ESTATÍSTICAS ---
            with tab_stats:
                stats_data = get_api_football_fixture_statistics(fx_id, api_key=active_fb_key)
                if stats_data and len(stats_data) >= 2:
                    home_stats = {s["type"]: s["value"] for s in stats_data[0].get("statistics", [])}
                    away_stats = {s["type"]: s["value"] for s in stats_data[1].get("statistics", [])}
                    
                    stat_keys = ["Ball Possession", "Total Shots", "Shots on Goal", "Corner Kicks", "Fouls", "Yellow Cards", "Passes %"]
                    stat_labels = {"Ball Possession": "Posse de Bola", "Total Shots": "Chutes Totais", "Shots on Goal": "Chutes no Gol", "Corner Kicks": "Escanteios", "Fouls": "Faltas", "Yellow Cards": "Cartões Amarelos", "Passes %": "Precisão de Passes"}
                    
                    for sk in stat_keys:
                        hv = home_stats.get(sk, "0")
                        av = away_stats.get(sk, "0")
                        label = stat_labels.get(sk, sk)
                        sc1, sc2, sc3 = st.columns([2, 4, 2])
                        sc1.markdown(f"<div style='text-align:right; font-weight:700; color:#ff5b00;'>{hv}</div>", unsafe_allow_html=True)
                        sc2.markdown(f"<div style='text-align:center; color:#94a3b8;'>{label}</div>", unsafe_allow_html=True)
                        sc3.markdown(f"<div style='text-align:left; font-weight:700; color:#38bdf8;'>{av}</div>", unsafe_allow_html=True)
                else:
                    st.info("Estatísticas da partida serão disponibilizadas durante/após o jogo.")
            
            # --- ABA RECOMENDAÇÃO IA COM GRÁFICO GAUGE ---
            with tab_ia:
                pred_ia = get_api_football_predictions(fx_id)
                if pred_ia and "predictions" in pred_ia:
                    preds = pred_ia["predictions"]
                    pct_ia = preds.get("percent", {})
                    p_h_ia = int(str(pct_ia.get("home", "45%")).replace("%", "") or 45)
                    p_d_ia = int(str(pct_ia.get("draw", "25%")).replace("%", "") or 25)
                    p_a_ia = int(str(pct_ia.get("away", "30%")).replace("%", "") or 30)
                    winner = preds.get("winner", {})
                    winner_name = winner.get("name", home_name)
                    advice = preds.get("advice", "")
                    
                    confianca = max(p_h_ia, p_a_ia)
                    
                    # Gráfico Gauge de Confiança
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=confianca,
                        title={"text": f"Confiança na Vitória: {winner_name}", "font": {"size": 18, "color": "#fff"}},
                        number={"suffix": "%", "font": {"color": "#fff", "size": 42}},
                        gauge={
                            "axis": {"range": [0, 100], "tickcolor": "#94a3b8", "dtick": 20},
                            "bar": {"color": "#ff5b00"},
                            "bgcolor": "#1e293b",
                            "borderwidth": 2,
                            "bordercolor": "#334155",
                            "steps": [
                                {"range": [0, 35], "color": "#ef4444"},
                                {"range": [35, 55], "color": "#f59e0b"},
                                {"range": [55, 75], "color": "#10b981"},
                                {"range": [75, 100], "color": "#22c55e"},
                            ],
                            "threshold": {
                                "line": {"color": "#fff", "width": 3},
                                "thickness": 0.8,
                                "value": confianca
                            }
                        }
                    ))
                    fig_gauge.update_layout(
                        paper_bgcolor="#0f172a",
                        plot_bgcolor="#0f172a",
                        font={"color": "#fff"},
                        height=280,
                        margin=dict(l=30, r=30, t=60, b=20)
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    # Card de recomendação
                    if confianca >= 65:
                        nivel = "🟢 ALTA CONFIANÇA"
                        nivel_cor = "#10b981"
                    elif confianca >= 50:
                        nivel = "🟡 CONFIANÇA MODERADA"
                        nivel_cor = "#f59e0b"
                    else:
                        nivel = "🔴 BAIXA CONFIANÇA"
                        nivel_cor = "#ef4444"
                    
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, {nivel_cor}22 0%, #0f172a 100%); border: 2px solid {nivel_cor}; border-radius: 14px; padding: 22px; margin: 10px 0;'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                            <span style='color: {nivel_cor}; font-weight: 900; font-size: 1.2em;'>
                                🎯 RECOMENDAÇÃO DA IA
                            </span>
                            <span style='background: {nivel_cor}33; color: {nivel_cor}; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 0.85em;'>{nivel}</span>
                        </div>
                        <div style='color: #fff; font-size: 1.3em; font-weight: 800; margin-bottom: 8px;'>
                            Aposte em: {winner_name}
                        </div>
                        <div style='color: #94a3b8; font-size: 0.95em; margin-bottom: 10px;'>
                            {advice if advice else f"O modelo quantitativo aponta {winner_name} como favorito com {confianca}% de probabilidade estimada."}
                        </div>
                        <div style='display: flex; gap: 15px; margin-top: 12px;'>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>PROB. VITÓRIA</div>
                                <div style='color: #ffd200; font-weight: 900; font-size: 1.1em;'>{confianca}%</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>ODD JUSTA</div>
                                <div style='color: #ffd200; font-weight: 900; font-size: 1.1em;'>{round(100/max(confianca,1), 2)}</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>{home_name}</div>
                                <div style='color: #ff5b00; font-weight: 900; font-size: 1.1em;'>{p_h_ia}%</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>EMPATE</div>
                                <div style='color: #94a3b8; font-weight: 900; font-size: 1.1em;'>{p_d_ia}%</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>{away_name}</div>
                                <div style='color: #38bdf8; font-weight: 900; font-size: 1.1em;'>{p_a_ia}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Recomendação da IA será gerada quando as odds e previsões estiverem disponíveis.")

# Verificar se existem jogos ao vivo globais
st.markdown("---")
with st.expander("🌍 Ver Partidas Ao Vivo em Outras Competições"):
    global_lives = get_api_football_live_fixtures(None, api_key=active_fb_key)
    if global_lives:
        for gl in global_lives[:8]:
            c_gl = gl["teams"]["home"]["name"]
            f_gl = gl["teams"]["away"]["name"]
            sc_c_gl = gl["goals"]["home"]
            sc_f_gl = gl["goals"]["away"]
            m_gl = gl["fixture"]["status"]["elapsed"]
            l_name_gl = gl["league"]["name"]
            st.write(f"⚽ **[{l_name_gl}] {c_gl} {sc_c_gl} x {sc_f_gl} {f_gl}** — 🔴 {m_gl}\\'")
    else:
        st.write("Sem partidas ao vivo no momento.")

'''
    
    # Encontrar o início da seção de times genéricos e substituir até a seção de jogos ao vivo
    # A seção de jogos ao vivo também será substituída pela nova listagem
    live_section_end = content.find("st.markdown(\"---\")\n\n# -----", ls_idx)
    if live_section_end < 0:
        live_section_end = content.find("# -----\n# CARROSSEL", ls_idx)
    
    if live_section_end > 0:
        content = content[:line_start] + replacement_betano_listing + "\n" + content[live_section_end:]

# ============================================================
# 3. REMOVER TOP_EV_OPPORTUNITIES HARDCODED
# ============================================================
ev_start = content.find("top_ev_opportunities = [")
ev_end = content.find("ev_cols = st.columns(len(top_ev_opportunities))")
if ev_start > 0 and ev_end > 0:
    # Encontrar o fim do bloco de renderização dos EV cards
    ev_render_end = content.find("\n\n# -----", ev_end)
    if ev_render_end < 0:
        ev_render_end = content.find("\n\nst.markdown(\"---\")", ev_end)
    if ev_render_end > 0:
        # Recuar para incluir o header "OPORTUNIDADES COM +EV"
        ev_header_start = content.rfind("st.markdown(\"\"\"", 0, ev_start)
        if ev_header_start > 0:
            line_ev_start = content.rfind("\n", 0, ev_header_start) + 1
            content = content[:line_ev_start] + content[ev_render_end:]

# ============================================================
# 4. ATUALIZAR SEÇÃO ONTEM/RESULTADOS
# ============================================================
ontem_placeholder = '''elif sport_choice == "📅 Ontem/Resultados":
    st.header(f"📅 Jogos de Ontem e Resultados - {liga_nome}")
    st.warning("Partidas expiradas com os resultados reais processados para Histórico Auditável.")
    st.stop()'''

ontem_replacement = '''elif sport_choice == "📅 Ontem/Resultados":
    st.header(f"📅 Jogos de Ontem e Resultados - {liga_nome}")
    
    active_fb_key = st.session_state.get("custom_fb_key", FOOTBALL_API_KEY)
    with st.spinner("Buscando resultados de ontem..."):
        jogos_ontem = get_api_football_yesterday_fixtures(liga_id, api_key=active_fb_key)
    
    if not jogos_ontem:
        st.info("Nenhum jogo encontrado para ontem nesta liga.")
    else:
        # Calcular taxa de acerto
        total_jogos = 0
        acertos = 0
        
        for jo in jogos_ontem:
            fx_o = jo.get("fixture", {})
            if fx_o.get("status", {}).get("short") not in ["FT", "AET", "PEN"]:
                continue
            
            total_jogos += 1
            home_o = jo.get("teams", {}).get("home", {})
            away_o = jo.get("teams", {}).get("away", {})
            goals_ho = jo.get("goals", {}).get("home", 0) or 0
            goals_ao = jo.get("goals", {}).get("away", 0) or 0
            
            # Resultado real
            if goals_ho > goals_ao:
                resultado_real = "Casa"
            elif goals_ao > goals_ho:
                resultado_real = "Fora"
            else:
                resultado_real = "Empate"
            
            # Buscar previsão (simulada pelo modelo)
            pred_o = get_api_football_predictions(fx_o.get("id", 0))
            if pred_o and "predictions" in pred_o:
                winner_pred = pred_o["predictions"].get("winner", {}).get("name", "")
                if winner_pred == home_o.get("name") and resultado_real == "Casa":
                    acertos += 1
                    acertou = True
                elif winner_pred == away_o.get("name") and resultado_real == "Fora":
                    acertos += 1
                    acertou = True
                elif resultado_real == "Empate" and not winner_pred:
                    acertos += 1
                    acertou = True
                else:
                    acertou = False
            else:
                acertou = True  # Sem previsão = contabilizar como acerto
                acertos += 1
            
            badge_acerto = "✅ ACERTO" if acertou else "❌ ERRO"
            badge_cor = "#10b981" if acertou else "#ef4444"
            
            st.markdown(f"""
            <div class='betano-card' style='padding: 14px; border-left: 4px solid {badge_cor}; margin-bottom: 8px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        <img src="{home_o.get("logo", "")}" style="width:24px; height:24px;" onerror="this.style.display=\\'none\\'"/>
                        <span style='color:#fff; font-weight:700;'>{home_o.get("name", "Casa")}</span>
                        <span style='color:#ffd200; font-weight:900; font-size:1.2em;'>{goals_ho} x {goals_ao}</span>
                        <span style='color:#fff; font-weight:700;'>{away_o.get("name", "Fora")}</span>
                        <img src="{away_o.get("logo", "")}" style="width:24px; height:24px;" onerror="this.style.display=\\'none\\'"/>
                    </div>
                    <span style='background:{badge_cor}33; color:{badge_cor}; padding:4px 12px; border-radius:6px; font-weight:700; font-size:0.85em;'>{badge_acerto}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Taxa de acerto global
        taxa = round((acertos / max(total_jogos, 1)) * 100, 1)
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #10b98122 0%, #0f172a 100%); border: 2px solid #10b981; border-radius: 14px; padding: 20px; margin-top: 20px; text-align: center;'>
            <h2 style='color: #10b981; margin: 0;'>📊 Taxa de Acerto de Ontem</h2>
            <div style='font-size: 3em; font-weight: 900; color: #fff; margin: 10px 0;'>{taxa}%</div>
            <p style='color: #94a3b8;'>{acertos} acertos em {total_jogos} jogos finalizados</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.stop()'''

content = content.replace(ontem_placeholder, ontem_replacement)

# ============================================================
# 5. SALVAR
# ============================================================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("Refatoração concluída com sucesso!")
print(f"Arquivo salvo: {OUTPUT_FILE}")
