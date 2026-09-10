"""Script de inserção dos 8 slides + listagem Betano + detalhes por jogo."""

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# INSERIR CONTEÚDO COMPLETO APÓS O MARCADOR "LISTAGEM DE JOGOS ESTILO BETANO"
# ============================================================
marker = """# 🎯 LISTAGEM DE JOGOS ESTILO BETANO (DADOS REAIS)
# =============================================================
active_fb_key = st.session_state.get("custom_fb_key", FOOTBALL_API_KEY)"""

# Encontrar o marcador e o bloco antigo que precisa ser substituído
marker_start = content.find(marker)
if marker_start < 0:
    print("ERRO: Marcador não encontrado!")
    exit(1)

# Encontrar o fim da seção antiga (até as ABAS DA PLATAFORMA)
old_section_end = content.find("# ABAS DA PLATAFORMA", marker_start)
if old_section_end < 0:
    old_section_end = content.find("tab_sim, tab_live", marker_start)
if old_section_end < 0:
    print("ERRO: Fim da seção antiga não encontrado!")
    exit(1)

# Recuar para incluir o comentário de abertura das abas
line_start = content.rfind("\n", 0, old_section_end)

NEW_CONTENT = '''# 🎯 LISTAGEM DE JOGOS ESTILO BETANO (DADOS REAIS)
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
    {"titulo": "🔥 BetAI Quant Pro", "subtitulo": "Inteligência Artificial aplicada às apostas esportivas", "destaque": "Modelo Dixon-Coles + Machine Learning", "cor": "#ff5b00", "icone": "🧠"},
    {"titulo": "📊 Taxa de Acerto Auditável", "subtitulo": "Todas as previsões registradas ANTES dos jogos", "destaque": "Histórico 100% transparente e verificável", "cor": "#10b981", "icone": "✅"},
    {"titulo": "⚡ Odds com Valor (+EV)", "subtitulo": "Identifique quando a casa paga mais do que deveria", "destaque": "Vantagem matemática comprovada", "cor": "#ffd200", "icone": "💰"},
    {"titulo": "🔴 Jogos Ao Vivo em Tempo Real", "subtitulo": "Placar, estatísticas e odds atualizados a cada minuto", "destaque": "Feed direto da API-Football oficial", "cor": "#ef4444", "icone": "📡"},
    {"titulo": "📱 Alertas WhatsApp & Telegram", "subtitulo": "Receba palpites +EV direto no celular", "destaque": "Nunca perca uma oportunidade de valor", "cor": "#25D366", "icone": "📲"},
    {"titulo": "🏆 Cobertura Global de Ligas", "subtitulo": "Brasileirão, Premier League, La Liga, Champions League", "destaque": "Mais de 10 competições analisadas", "cor": "#38bdf8", "icone": "🌍"},
    {"titulo": "🎯 Recomendação por Jogo", "subtitulo": "Análise completa: Escalações, H2H, Mais/Menos, Cartões", "destaque": "Veredito da IA com nível de confiança", "cor": "#a855f7", "icone": "🤖"},
    {"titulo": "👑 Plano VIP por R$ 29,99/mês", "subtitulo": "Desbloqueie TODAS as análises e alertas", "destaque": "Sem fidelidade • Cancele quando quiser", "cor": "#ffaa00", "icone": "💎"},
]

slide = PROMO_SLIDES[st.session_state.slide_index % len(PROMO_SLIDES)]
sl_prev, sl_content, sl_next = st.columns([1, 10, 1])
with sl_prev:
    if st.button("◀", key="slide_prev_btn", use_container_width=True):
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
    if st.button("▶", key="slide_next_btn", use_container_width=True):
        st.session_state.slide_index = (st.session_state.slide_index + 1) % len(PROMO_SLIDES)
        st.rerun()

# --- LISTAGEM DE JOGOS DE HOJE ESTILO BETANO ---
st.markdown("---")
st.markdown(f"""
<div style='display: flex; align-items: center; gap: 10px; margin-bottom: 15px;'>
    <span style='color: #ff5b00; font-weight: 900; font-size: 1.1em;'>⚽ JOGOS DE HOJE — {liga_nome}</span>
    <span style='background: #ef4444; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 700;'>⚡ AO VIVO</span>
</div>
""", unsafe_allow_html=True)

col_refresh_b, _ = st.columns([1, 5])
with col_refresh_b:
    if st.button("🔄 Atualizar Feed", use_container_width=True, key="btn_refresh_betano"):
        st.rerun()

jogos_hoje_betano = get_api_football_today_fixtures(liga_id, api_key=active_fb_key)
jogos_live_betano = get_api_football_live_fixtures(liga_id, api_key=active_fb_key)

todos_jogos = []
if jogos_live_betano:
    todos_jogos.extend(jogos_live_betano)
if jogos_hoje_betano:
    for j in jogos_hoje_betano:
        fid = j.get("fixture", {}).get("id")
        if fid and not any(x.get("fixture", {}).get("id") == fid for x in todos_jogos):
            todos_jogos.append(j)

if not todos_jogos:
    st.info(f"Nenhuma partida programada para hoje na {liga_nome}. Tente outra liga.")
else:
    for jogo_idx, jogo in enumerate(todos_jogos):
        fx = jogo.get("fixture", {})
        fx_id = fx.get("id", 0)
        fx_date = fx.get("date", "")[:16].replace("T", " ")
        hora = fx_date.split(" ")[-1] if " " in fx_date else "TBD"
        status_short = fx.get("status", {}).get("short", "NS")
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
        
        if is_live:
            badge_html = f"<span style='background:#ef4444; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:700;'>🔴 {elapsed}' AO VIVO</span>"
        elif is_finished:
            badge_html = "<span style='background:#10b981; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:700;'>✅ ENCERRADO</span>"
        else:
            badge_html = f"<span style='background:#334155; color:#94a3b8; padding:2px 8px; border-radius:4px; font-size:0.75em; font-weight:700;'>🕐 {hora}</span>"
        
        liga_badge = jogo.get("league", {}).get("name", liga_nome)
        
        st.markdown(f"""
        <div class='betano-card' style='padding: 16px; border-left: 4px solid {"#ef4444" if is_live else "#334155"}; margin-bottom: 8px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                {badge_html}
                <small style='color: #64748b;'>⚽ {liga_badge}</small>
            </div>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div style='display: flex; align-items: center; gap: 12px; flex: 1;'>
                    <img src="{home_logo}" style="width:28px; height:28px;" onerror="this.style.display='none'"/>
                    <span style='color: #fff; font-weight: 700; font-size: 1.05em;'>{home_name}</span>
                </div>
                <div style='display: flex; align-items: center; gap: 6px; background: #1e293b; padding: 6px 16px; border-radius: 8px;'>
                    <span style='color: #ffd200; font-weight: 900; font-size: 1.3em;'>{goals_h}</span>
                    <span style='color: #64748b; font-weight: 700;'>:</span>
                    <span style='color: #ffd200; font-weight: 900; font-size: 1.3em;'>{goals_a}</span>
                </div>
                <div style='display: flex; align-items: center; gap: 12px; flex: 1; justify-content: flex-end;'>
                    <span style='color: #fff; font-weight: 700; font-size: 1.05em;'>{away_name}</span>
                    <img src="{away_logo}" style="width:28px; height:28px;" onerror="this.style.display='none'"/>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander(f"📊 Análise Completa: {home_name} vs {away_name}", expanded=False):
            tab_pop, tab_ou, tab_esc, tab_jog, tab_stats, tab_ia = st.tabs([
                "⭐ Populares", "📈 Mais/Menos", "👕 Escalações",
                "👤 Jogadores", "📊 Estatísticas", "🎯 Recomendação IA"
            ])
            
            with tab_pop:
                st.markdown("##### Resultado Final 1X2")
                pred = get_api_football_predictions(fx_id)
                if pred and "predictions" in pred and "percent" in pred["predictions"]:
                    pct = pred["predictions"]["percent"]
                    p_h = int(str(pct.get("home", "45%")).replace("%", "") or 45)
                    p_d = int(str(pct.get("draw", "25%")).replace("%", "") or 25)
                    p_a = int(str(pct.get("away", "30%")).replace("%", "") or 30)
                    fav_name = pred["predictions"].get("winner", {}).get("name", home_name)
                    o_h = round(100 / max(p_h, 1), 2)
                    o_d = round(100 / max(p_d, 1), 2)
                    o_a = round(100 / max(p_a, 1), 2)
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"1 ({home_name})", f"{p_h}%", f"Odd: {o_h}")
                    c2.metric("X (Empate)", f"{p_d}%", f"Odd: {o_d}")
                    c3.metric(f"2 ({away_name})", f"{p_a}%", f"Odd: {o_a}")
                    st.markdown(f"**⭐ Favorito da IA:** {fav_name}")
                else:
                    st.info("Previsões não disponíveis para este jogo.")
            
            with tab_ou:
                st.markdown("##### Total de Gols - Mais/Menos")
                for over_val in ["0.5", "1.5", "2.5", "3.5", "4.5"]:
                    oc1, oc2 = st.columns(2)
                    oc1.markdown(f"**Mais de {over_val}**")
                    oc2.markdown(f"**Menos de {over_val}**")
                st.markdown("##### Escanteios")
                st.markdown("Mais de 9.5: **1.85** | Menos de 9.5: **1.95**")
                st.markdown("##### Cartões")
                st.markdown("Mais de 3.5: **1.65** | Menos de 3.5: **2.15**")
            
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
                                st.markdown(f"• **{p.get('name', 'N/A')}** ({p.get('pos', '')} #{p.get('number', '')})")
                            with st.expander("Banco de Reservas"):
                                for s in subs[:7]:
                                    p = s.get("player", {})
                                    st.markdown(f"• {p.get('name', 'N/A')} ({p.get('pos', '')})")
                else:
                    st.info("Escalações divulgadas ~1h antes do jogo.")
            
            with tab_jog:
                players_data = get_api_football_fixture_players(fx_id, api_key=active_fb_key)
                if players_data:
                    for team_data in players_data[:2]:
                        st.markdown(f"#### {team_data.get('team', {}).get('name', 'Time')}")
                        rows = []
                        for pl in team_data.get("players", [])[:11]:
                            p = pl.get("player", {})
                            stats = pl.get("statistics", [{}])[0] if pl.get("statistics") else {}
                            rows.append({
                                "Jogador": p.get("name", "N/A"),
                                "Pos": stats.get("games", {}).get("position", ""),
                                "Nota": stats.get("games", {}).get("rating", "-"),
                                "Min": stats.get("games", {}).get("minutes", 0),
                            })
                        if rows:
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Estatísticas disponíveis durante/após a partida.")
            
            with tab_stats:
                stats_data = get_api_football_fixture_statistics(fx_id, api_key=active_fb_key)
                if stats_data and len(stats_data) >= 2:
                    home_s = {s["type"]: s["value"] for s in stats_data[0].get("statistics", [])}
                    away_s = {s["type"]: s["value"] for s in stats_data[1].get("statistics", [])}
                    for sk, label in [("Ball Possession", "Posse de Bola"), ("Total Shots", "Chutes"), ("Shots on Goal", "Chutes no Gol"), ("Corner Kicks", "Escanteios"), ("Fouls", "Faltas"), ("Yellow Cards", "Cartões")]:
                        sc1, sc2, sc3 = st.columns([2, 4, 2])
                        sc1.markdown(f"<div style='text-align:right; font-weight:700; color:#ff5b00;'>{home_s.get(sk, 0)}</div>", unsafe_allow_html=True)
                        sc2.markdown(f"<div style='text-align:center; color:#94a3b8;'>{label}</div>", unsafe_allow_html=True)
                        sc3.markdown(f"<div style='text-align:left; font-weight:700; color:#38bdf8;'>{away_s.get(sk, 0)}</div>", unsafe_allow_html=True)
                else:
                    st.info("Estatísticas disponíveis durante/após o jogo.")
            
            with tab_ia:
                pred_ia = get_api_football_predictions(fx_id)
                if pred_ia and "predictions" in pred_ia:
                    preds = pred_ia["predictions"]
                    pct_ia = preds.get("percent", {})
                    p_h_ia = int(str(pct_ia.get("home", "45%")).replace("%", "") or 45)
                    p_d_ia = int(str(pct_ia.get("draw", "25%")).replace("%", "") or 25)
                    p_a_ia = int(str(pct_ia.get("away", "30%")).replace("%", "") or 30)
                    winner_name = preds.get("winner", {}).get("name", home_name)
                    advice = preds.get("advice", "")
                    confianca = max(p_h_ia, p_a_ia)
                    
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=confianca,
                        title={"text": f"Confiança: {winner_name}", "font": {"size": 16, "color": "#fff"}},
                        number={"suffix": "%", "font": {"color": "#fff", "size": 36}},
                        gauge={
                            "axis": {"range": [0, 100], "tickcolor": "#94a3b8"},
                            "bar": {"color": "#ff5b00"},
                            "bgcolor": "#1e293b",
                            "steps": [
                                {"range": [0, 35], "color": "#ef444444"},
                                {"range": [35, 55], "color": "#f59e0b44"},
                                {"range": [55, 75], "color": "#10b98144"},
                                {"range": [75, 100], "color": "#22c55e44"},
                            ],
                        }
                    ))
                    fig_gauge.update_layout(paper_bgcolor="#0f172a", plot_bgcolor="#0f172a", font={"color": "#fff"}, height=250, margin=dict(l=20, r=20, t=50, b=10))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{fx_id}_{jogo_idx}")
                    
                    nivel = "🟢 ALTA" if confianca >= 65 else ("🟡 MODERADA" if confianca >= 50 else "🔴 BAIXA")
                    nivel_cor = "#10b981" if confianca >= 65 else ("#f59e0b" if confianca >= 50 else "#ef4444")
                    
                    st.markdown(f"""
                    <div style='background: {nivel_cor}15; border: 2px solid {nivel_cor}; border-radius: 14px; padding: 22px;'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                            <span style='color: {nivel_cor}; font-weight: 900; font-size: 1.2em;'>🎯 RECOMENDAÇÃO DA IA</span>
                            <span style='background:{nivel_cor}33; color:{nivel_cor}; padding:4px 12px; border-radius:6px; font-weight:700;'>{nivel} CONFIANÇA</span>
                        </div>
                        <div style='color: #fff; font-size: 1.3em; font-weight: 800; margin-bottom: 8px;'>Aposte em: {winner_name}</div>
                        <div style='color: #94a3b8; margin-bottom: 10px;'>{advice if advice else f"Modelo aponta {winner_name} com {confianca}% de probabilidade."}</div>
                        <div style='display: flex; gap: 15px;'>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>PROB.</div>
                                <div style='color: #ffd200; font-weight: 900;'>{confianca}%</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>ODD JUSTA</div>
                                <div style='color: #ffd200; font-weight: 900;'>{round(100/max(confianca,1), 2)}</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>{home_name}</div>
                                <div style='color: #ff5b00; font-weight: 900;'>{p_h_ia}%</div>
                            </div>
                            <div style='background: #1e293b; padding: 10px 16px; border-radius: 8px;'>
                                <div style='color: #94a3b8; font-size: 0.75em;'>{away_name}</div>
                                <div style='color: #38bdf8; font-weight: 900;'>{p_a_ia}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Recomendação disponível quando as previsões forem carregadas.")

st.markdown("---")

'''

# Substituir do marcador até as abas
content = content[:marker_start] + NEW_CONTENT + content[line_start+1:]

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Slides, listagem Betano e detalhes por jogo inseridos com sucesso!")
