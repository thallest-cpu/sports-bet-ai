import json
from typing import Optional

def generate_realtime_html_component(server_port: int = 8002) -> str:
    """
    Componente reativo profissional de tempo real com os Três Pilares integrados:
    1. Renderizador do Campo de Futebol 2D (SVG/Canvas) estilo Betano Match Tracker
    2. Painel de Estatísticas e Probabilidades (Odds) Sincronizadas
    3. Conexão contínua via WebSockets com sistema de salas por partida (join_match / leave_match)
    """
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    body {{
        background-color: #0b0e14;
        color: #e2e8f0;
        padding: 10px;
    }}
    
    /* Barra Superior de Conexão */
    .top-status-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        background: #17212b;
        border: 1px solid #233242;
        border-radius: 10px;
        padding: 10px 16px;
        margin-bottom: 14px;
    }}
    .connection-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 0.82em;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid #10b981;
    }}
    .connection-badge.connecting {{
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border-color: #f59e0b;
    }}
    .connection-badge.error {{
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border-color: #ef4444;
    }}
    .status-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #10b981;
        animation: pulse-dot 1.5s infinite;
    }}
    @keyframes pulse-dot {{
        0% {{ transform: scale(0.9); opacity: 0.8; }}
        50% {{ transform: scale(1.3); opacity: 1; }}
        100% {{ transform: scale(0.9); opacity: 0.8; }}
    }}

    /* Banner de Alerta de Desconexão */
    #disconnect-banner {{
        display: none;
        background: rgba(245, 158, 11, 0.2);
        border: 1px solid #f59e0b;
        color: #fcd34d;
        padding: 8px 14px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-size: 0.85em;
        font-weight: 600;
        align-items: center;
        gap: 10px;
    }}

    /* -------------------------------------------------------------
       PILAR 1 & 2: MATCH TRACKER 2D ESTILO BETANO (CAMPO SVG + ESTATÍSTICAS)
       ------------------------------------------------------------- */
    .match-center-card {{
        background: #121922;
        border: 1px solid #ff5b00;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}
    .tracker-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid #233242;
        margin-bottom: 14px;
    }}
    .tracker-match-info {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .tracker-match-title {{
        font-size: 1.15em;
        font-weight: 900;
        color: #fff;
    }}
    .tracker-score-pill {{
        background: #ff5b00;
        color: #fff;
        font-weight: 900;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 1.05em;
        letter-spacing: 1px;
    }}
    .tracker-clock-badge {{
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8em;
        font-weight: 800;
    }}
    .match-select-dropdown {{
        background: #17212b;
        color: #fff;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 7px 12px;
        font-size: 0.85em;
        outline: none;
        cursor: pointer;
        max-width: 280px;
    }}

    /* Layout Lado a Lado (Campo à Esquerda + Estatísticas à Direita) */
    .tracker-body-split {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
    }}
    @media (max-width: 920px) {{
        .tracker-body-split {{
            grid-template-columns: 1fr;
        }}
    }}

    /* Renderizador do Campo SVG */
    .pitch-wrapper {{
        position: relative;
        width: 100%;
        min-height: 250px;
        background: linear-gradient(180deg, #11381e 0%, #174b29 50%, #11381e 100%);
        border: 2px solid #1f5d34;
        border-radius: 10px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.6);
    }}
    .pitch-svg {{
        width: 100%;
        height: 100%;
        min-height: 250px;
    }}
    .team-pitch-label {{
        position: absolute;
        top: 8px;
        font-size: 0.78em;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 3px 8px;
        border-radius: 4px;
        background: rgba(11, 14, 20, 0.75);
        color: #fff;
        z-index: 5;
    }}
    .team-pitch-label.home {{ left: 10px; border-left: 3px solid #ff5b00; }}
    .team-pitch-label.away {{ right: 10px; border-right: 3px solid #38bdf8; }}

    /* Banner Dinâmico de Evento Sobreposto no Campo */
    .event-banner {{
        position: absolute;
        bottom: 12px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(17, 24, 39, 0.92);
        border: 1px solid #ff5b00;
        color: #fff;
        font-size: 0.88em;
        font-weight: 800;
        padding: 6px 18px;
        border-radius: 20px;
        text-align: center;
        white-space: nowrap;
        box-shadow: 0 4px 15px rgba(255, 91, 0, 0.3);
        z-index: 10;
        transition: all 0.3s ease;
    }}
    .event-banner.danger {{
        background: rgba(239, 68, 68, 0.95);
        border-color: #f87171;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.6);
        animation: pulse-danger 1s infinite alternate;
    }}
    @keyframes pulse-danger {{
        0% {{ transform: translateX(-50%) scale(0.97); }}
        100% {{ transform: translateX(-50%) scale(1.03); }}
    }}

    /* Overlay de Celebração de Gol no Campo */
    .pitch-goal-celebration {{
        display: none;
        position: absolute;
        inset: 0;
        background: radial-gradient(circle, rgba(255, 91, 0, 0.4) 0%, rgba(11, 14, 20, 0.85) 100%);
        z-index: 20;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        animation: fadeIn 0.3s forwards;
    }}
    .pitch-goal-celebration h2 {{
        font-size: 2em;
        font-weight: 900;
        color: #fbbf24;
        text-shadow: 0 0 20px #ff5b00;
        letter-spacing: 2px;
        animation: bounce 0.6s infinite alternate;
    }}
    @keyframes bounce {{
        0% {{ transform: translateY(0); }}
        100% {{ transform: translateY(-8px); }}
    }}

    /* Bola de Futebol e Animação de Movimento */
    #pitch-ball {{
        transition: cx 0.7s cubic-bezier(0.25, 1, 0.5, 1), cy 0.7s cubic-bezier(0.25, 1, 0.5, 1);
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));
    }}
    #attack-cone-home, #attack-cone-away {{
        transition: opacity 0.5s ease;
    }}

    /* Barra de Simulação Tática Rápida */
    .tactical-sim-bar {{
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-top: 10px;
        justify-content: center;
    }}
    .btn-tactical {{
        background: #17212b;
        color: #cbd5e1;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 5px 9px;
        font-size: 0.76em;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .btn-tactical:hover {{
        background: #ff5b00;
        color: #fff;
        border-color: #ff5b00;
    }}
    .btn-tactical.goal-btn {{
        background: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border-color: #f59e0b;
    }}
    .btn-tactical.goal-btn:hover {{
        background: #f59e0b;
        color: #000;
    }}

    /* -------------------------------------------------------------
       PILAR 3: PAINEL DE ESTATÍSTICAS E ODDS SINCRONIZADAS
       ------------------------------------------------------------- */
    .stats-panel-container {{
        display: flex;
        flex-direction: column;
        gap: 12px;
    }}
    .odds-card-section {{
        background: #17212b;
        border: 1px solid #233242;
        border-radius: 8px;
        padding: 10px 14px;
    }}
    .section-title {{
        font-size: 0.82em;
        font-weight: 800;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
    }}
    .odds-row-tracker {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px;
    }}
    .odd-btn-track {{
        background: #111722;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 10px;
        color: #fff;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .odd-btn-track:hover {{
        border-color: #ff5b00;
    }}
    .odd-label-t {{
        font-size: 0.72em;
        color: #94a3b8;
        font-weight: 700;
        display: block;
        margin-bottom: 2px;
    }}
    .odd-val-t {{
        font-size: 1.05em;
        font-weight: 900;
        color: #f8fafc;
    }}

    /* Barras de Estatísticas do Confronto */
    .stats-rows-container {{
        background: #17212b;
        border: 1px solid #233242;
        border-radius: 8px;
        padding: 12px 14px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }}
    .stat-line {{
        display: flex;
        flex-direction: column;
        gap: 4px;
    }}
    .stat-header {{
        display: flex;
        justify-content: space-between;
        font-size: 0.8em;
        font-weight: 700;
        color: #cbd5e1;
    }}
    .stat-bar-dual {{
        display: flex;
        height: 6px;
        width: 100%;
        background: #233242;
        border-radius: 3px;
        overflow: hidden;
    }}
    .bar-home {{
        background: #ff5b00;
        height: 100%;
        transition: width 0.5s ease;
    }}
    .bar-away {{
        background: #38bdf8;
        height: 100%;
        transition: width 0.5s ease;
    }}

    /* Card Veredito IA ao Vivo */
    .ai-verdict-live {{
        background: rgba(255, 91, 0, 0.1);
        border: 1px dashed #ff5b00;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 0.82em;
        color: #fdba74;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* -------------------------------------------------------------
       FEED DE PARTIDAS, BUSCA E FILTROS
       ------------------------------------------------------------- */
    .search-row {{
        margin-bottom: 12px;
        position: relative;
    }}
    .search-input {{
        width: 100%;
        background: #17212b;
        border: 1px solid #233242;
        border-radius: 8px;
        padding: 10px 14px 10px 38px;
        color: #fff;
        font-size: 0.88em;
        outline: none;
        transition: border-color 0.2s;
    }}
    .search-input:focus {{
        border-color: #ff5b00;
        box-shadow: 0 0 0 2px rgba(255, 91, 0, 0.2);
    }}
    .search-icon {{
        position: absolute;
        left: 12px;
        top: 50%;
        transform: translateY(-50%);
        color: #64748b;
        font-size: 1.1em;
    }}

    .status-tabs {{
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
        flex-wrap: wrap;
    }}
    .tab-status-btn {{
        background: #17212b;
        border: 1px solid #233242;
        color: #94a3b8;
        padding: 7px 14px;
        border-radius: 8px;
        font-size: 0.82em;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .tab-status-btn.active {{
        background: #ff5b00;
        color: #fff;
        border-color: #ff5b00;
    }}

    .league-filters {{
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 14px;
    }}
    .filter-btn {{
        background: #111722;
        color: #94a3b8;
        border: 1px solid #233242;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 0.76em;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .filter-btn:hover, .filter-btn.active {{
        background: #233242;
        color: #ff5b00;
        border-color: #ff5b00;
    }}

    /* Card de Jogo na Lista */
    .matches-grid {{
        display: flex;
        flex-direction: column;
        gap: 10px;
    }}
    .match-card {{
        background: #17212b;
        border: 1px solid #233242;
        border-radius: 10px;
        padding: 12px 16px;
        transition: border-color 0.2s, transform 0.2s;
        cursor: pointer;
    }}
    .match-card:hover {{
        border-color: #3b82f6;
        transform: translateY(-1px);
    }}
    .match-card.active-selected {{
        border-color: #ff5b00;
        background: #1a2533;
        box-shadow: 0 0 10px rgba(255, 91, 0, 0.2);
    }}
    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }}
    .league-title {{
        color: #94a3b8;
        font-size: 0.78em;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .badges-group {{
        display: flex;
        gap: 6px;
        align-items: center;
    }}
    .status-badge {{
        font-size: 0.75em;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 4px;
    }}
    .status-badge.live {{
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #ef4444;
    }}
    .status-badge.post {{
        background: rgba(148, 163, 184, 0.15);
        color: #94a3b8;
    }}
    .status-badge.pre {{
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
    }}

    .card-body {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }}
    .match-title {{
        font-size: 1.05em;
        font-weight: 800;
        color: #fff;
    }}
    .score-badge {{
        background: #ff5b00;
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        margin: 0 6px;
        font-size: 0.95em;
    }}
    .btn-open-tracker {{
        background: rgba(255, 91, 0, 0.15);
        color: #ff5b00;
        border: 1px solid #ff5b00;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.78em;
        font-weight: 800;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .btn-open-tracker:hover {{
        background: #ff5b00;
        color: #fff;
    }}
</style>
</head>
<body>

<!-- BARRA DE STATUS E CONEXÃO -->
<div class="top-status-bar">
    <div id="connection-status" class="connection-badge connecting">
        <div class="status-dot"></div>
        <span id="conn-text">Conectando ao WebSockets (Porta {server_port})...</span>
    </div>
    <div style="font-size: 0.82em; color: #94a3b8; font-weight: 600;">
        <span id="match-counter">Carregando partidas...</span> • Match Tracker 2D Ativo
    </div>
</div>

<!-- BANNER DE RECONEXÃO -->
<div id="disconnect-banner">
    ⚠️ Conexão WebSocket interrompida. Tentando reconexão automática em segundo plano...
</div>

<!-- ============================================================= -->
<!-- PILARES 1, 2 & 3: MATCH CENTER 2D ESTILO BETANO               -->
<!-- ============================================================= -->
<div class="match-center-card" id="match-tracker-panel">
    <div class="tracker-header">
        <div class="tracker-match-info">
            <span class="tracker-clock-badge" id="track-clock">AO VIVO (38')</span>
            <span class="tracker-match-title" id="track-teams">Flamengo vs Palmeiras</span>
            <span class="tracker-score-pill" id="track-score">1 x 0</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-size: 0.8em; color: #94a3b8; font-weight: 700;">Selecionar Partida:</label>
            <select class="match-select-dropdown" id="match-selector" onchange="changeTrackedMatch(this.value)">
                <option value="123">Flamengo x Palmeiras (Ao Vivo)</option>
            </select>
        </div>
    </div>

    <div class="tracker-body-split">
        <!-- LADO ESQUERDO: CAMPO DE FUTEBOL 2D (SVG/CANVAS) -->
        <div>
            <div class="pitch-wrapper" id="pitch-container">
                <!-- Rótulos dos Clubes -->
                <span class="team-pitch-label home" id="pitch-home-name">FLAMENGO</span>
                <span class="team-pitch-label away" id="pitch-away-name">PALMEIRAS</span>

                <!-- Campo SVG com Proporção Fiel 100x60 -->
                <svg class="pitch-svg" viewBox="0 0 100 60" preserveAspectRatio="none">
                    <defs>
                        <!-- Faixas do Gramado Texturizado -->
                        <pattern id="grass-stripes" width="10" height="60" patternUnits="userSpaceOnUse">
                            <rect width="5" height="60" fill="#144224" />
                            <rect x="5" width="5" height="60" fill="#174b29" />
                        </pattern>
                        <!-- Gradiente de Ataque Perigoso Casa (Direita) -->
                        <linearGradient id="attackGradRight" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#ff5b00" stop-opacity="0" />
                            <stop offset="70%" stop-color="#ff5b00" stop-opacity="0.35" />
                            <stop offset="100%" stop-color="#ef4444" stop-opacity="0.7" />
                        </linearGradient>
                        <!-- Gradiente de Ataque Perigoso Fora (Esquerda) -->
                        <linearGradient id="attackGradLeft" x1="100%" y1="0%" x2="0%" y2="0%">
                            <stop offset="0%" stop-color="#38bdf8" stop-opacity="0" />
                            <stop offset="70%" stop-color="#38bdf8" stop-opacity="0.35" />
                            <stop offset="100%" stop-color="#ef4444" stop-opacity="0.7" />
                        </linearGradient>
                    </defs>

                    <!-- Fundo do Gramado -->
                    <rect width="100" height="60" fill="url(#grass-stripes)" />

                    <!-- Marcações Oficiais do Campo -->
                    <rect x="2" y="2" width="96" height="56" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <line x1="50" y1="2" x2="50" y2="58" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <circle cx="50" cy="30" r="8" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <circle cx="50" cy="30" r="0.7" fill="#ffffff" />

                    <!-- Grande Área & Pequena Área Esquerda -->
                    <rect x="2" y="15" width="14" height="30" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <rect x="2" y="22" width="5" height="16" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <circle cx="10" cy="30" r="0.6" fill="#ffffff" />
                    <path d="M 16 25 A 6 6 0 0 1 16 35" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />

                    <!-- Grande Área & Pequena Área Direita -->
                    <rect x="84" y="15" width="14" height="30" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <rect x="93" y="22" width="5" height="16" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <circle cx="90" cy="30" r="0.6" fill="#ffffff" />
                    <path d="M 84 25 A 6 6 0 0 0 84 35" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />

                    <!-- Arcos de Escanteio -->
                    <path d="M 2 4 A 2 2 0 0 0 4 2" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <path d="M 2 56 A 2 2 0 0 1 4 58" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <path d="M 98 4 A 2 2 0 0 1 96 2" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />
                    <path d="M 98 56 A 2 2 0 0 0 96 58" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="0.8" />

                    <!-- Cones de Ataque Perigoso Animados -->
                    <polygon id="attack-cone-home" points="50,15 95,20 95,40 50,45" fill="url(#attackGradRight)" opacity="0" />
                    <polygon id="attack-cone-away" points="50,15 5,20 5,40 50,45" fill="url(#attackGradLeft)" opacity="0" />

                    <!-- A Bola de Futebol em Movimento 60 FPS -->
                    <circle id="pitch-ball" cx="50" cy="30" r="1.6" fill="#ffffff" stroke="#ff5b00" stroke-width="0.5" />
                </svg>

                <!-- Banner Central de Evento -->
                <div class="event-banner" id="pitch-event-banner">⚡ Ataque Perigoso - Flamengo</div>

                <!-- Overlay de Celebração de Gol -->
                <div class="pitch-goal-celebration" id="goal-celebration-overlay">
                    <h2>⚽ GOOOOOOOL!</h2>
                    <p id="celebration-subtitle" style="color: #fff; font-size: 1.1em; font-weight: 800; margin-top: 6px;">Gol do Flamengo!</p>
                </div>
            </div>

            <!-- Controles de Simulação Tática Instantânea -->
            <div class="tactical-sim-bar">
                <button class="btn-tactical" onclick="simulatePitch('DANGEROUS_ATTACK', 'casa')">⚡ Ataque Casa</button>
                <button class="btn-tactical" onclick="simulatePitch('DANGEROUS_ATTACK', 'fora')">⚡ Ataque Fora</button>
                <button class="btn-tactical" onclick="simulatePitch('SHOT', 'casa')">🎯 Chute no Gol</button>
                <button class="btn-tactical" onclick="simulatePitch('CORNER', 'casa')">🚩 Escanteio</button>
                <button class="btn-tactical" onclick="simulatePitch('FREE_KICK', 'casa')">⚠️ Falta</button>
                <button class="btn-tactical goal-btn" onclick="simulatePitch('GOAL', 'casa')">⚽ Simular GOL!</button>
            </div>
        </div>

        <!-- LADO DIREITO: ESTATÍSTICAS E ODDS SINCRONIZADAS -->
        <div class="stats-panel-container">
            <!-- Probabilidades (Odds Ao Vivo) -->
            <div class="odds-card-section">
                <div class="section-title">
                    <span>Probabilidades (Odds Ao Vivo)</span>
                    <span style="color: #10b981;">● Flutuação < 5ms</span>
                </div>
                <div class="odds-row-tracker">
                    <button class="odd-btn-track" id="btn-odd-casa">
                        <span class="odd-label-t">Casa (1)</span>
                        <span class="odd-val-t" id="track-odd-c">1.85</span>
                    </button>
                    <button class="odd-btn-track" id="btn-odd-empate">
                        <span class="odd-label-t">Empate (X)</span>
                        <span class="odd-val-t" id="track-odd-d">3.20</span>
                    </button>
                    <button class="odd-btn-track" id="btn-odd-fora">
                        <span class="odd-label-t">Fora (2)</span>
                        <span class="odd-val-t" id="track-odd-a">4.10</span>
                    </button>
                </div>
            </div>

            <!-- Estatísticas do Confronto -->
            <div class="stats-rows-container">
                <div class="section-title">Estatísticas do Confronto</div>

                <!-- Posse de Bola -->
                <div class="stat-line">
                    <div class="stat-header">
                        <span id="stat-posse-casa">58%</span>
                        <span style="color: #94a3b8;">Posse de Bola</span>
                        <span id="stat-posse-fora">42%</span>
                    </div>
                    <div class="stat-bar-dual">
                        <div class="bar-home" id="bar-posse-casa" style="width: 58%;"></div>
                        <div class="bar-away" id="bar-posse-fora" style="width: 42%;"></div>
                    </div>
                </div>

                <!-- Chutes no Gol -->
                <div class="stat-line">
                    <div class="stat-header">
                        <span id="stat-chutes-casa">4</span>
                        <span style="color: #94a3b8;">Finalizações no Alvo</span>
                        <span id="stat-chutes-fora">1</span>
                    </div>
                    <div class="stat-bar-dual">
                        <div class="bar-home" id="bar-chutes-casa" style="width: 80%;"></div>
                        <div class="bar-away" id="bar-chutes-fora" style="width: 20%;"></div>
                    </div>
                </div>

                <!-- Ataques Perigosos -->
                <div class="stat-line">
                    <div class="stat-header">
                        <span id="stat-ataques-casa">34</span>
                        <span style="color: #94a3b8;">Ataques Perigosos</span>
                        <span id="stat-ataques-fora">19</span>
                    </div>
                    <div class="stat-bar-dual">
                        <div class="bar-home" id="bar-ataques-casa" style="width: 64%;"></div>
                        <div class="bar-away" id="bar-ataques-fora" style="width: 36%;"></div>
                    </div>
                </div>

                <!-- Escanteios -->
                <div class="stat-line">
                    <div class="stat-header">
                        <span id="stat-cantos-casa">5</span>
                        <span style="color: #94a3b8;">Escanteios</span>
                        <span id="stat-cantos-fora">2</span>
                    </div>
                    <div class="stat-bar-dual">
                        <div class="bar-home" id="bar-cantos-casa" style="width: 71%;"></div>
                        <div class="bar-away" id="bar-cantos-fora" style="width: 29%;"></div>
                    </div>
                </div>

                <!-- Expected Goals (xG) -->
                <div class="stat-line">
                    <div class="stat-header">
                        <span id="stat-xg-casa">1.45</span>
                        <span style="color: #94a3b8;">Gols Esperados (xG)</span>
                        <span id="stat-xg-fora">0.38</span>
                    </div>
                    <div class="stat-bar-dual">
                        <div class="bar-home" id="bar-xg-casa" style="width: 79%;"></div>
                        <div class="bar-away" id="bar-xg-fora" style="width: 21%;"></div>
                    </div>
                </div>
            </div>

            <!-- Veredito Quantitativo IA -->
            <div class="ai-verdict-live">
                <span>🤖</span>
                <div>
                    <b>BetAI Quant Pro:</b> Domínio ofensivo do mandante detectado (+EV Live favorável à vitória da casa ou Over 1.5).
                </div>
            </div>
        </div>
    </div>
</div>

<!-- ============================================================= -->
<!-- FEED DE PARTIDAS, BUSCA E FILTROS                             -->
<!-- ============================================================= -->
<div class="search-row">
    <span class="search-icon">🔍</span>
    <input 
        type="text" 
        class="search-input" 
        id="team-search" 
        placeholder="Pesquisar por clube, país ou competição ao vivo..."
        oninput="handleSearch(this.value)"
    >
</div>

<div class="status-tabs">
    <button class="tab-status-btn active" onclick="setStatusGroup('ALL')">Todas as Partidas <span id="count-all">(0)</span></button>
    <button class="tab-status-btn" onclick="setStatusGroup('LIVE')">🔴 Ao Vivo <span id="count-live">(0)</span></button>
    <button class="tab-status-btn" onclick="setStatusGroup('PRE')">⏳ Próximos Jogos <span id="count-pre">(0)</span></button>
    <button class="tab-status-btn" onclick="setStatusGroup('POST')">🏁 Encerrados <span id="count-post">(0)</span></button>
</div>

<div class="league-filters">
    <button class="filter-btn active" onclick="setLeagueFilter('ALL')">Todas as Ligas</button>
    <button class="filter-btn" onclick="setLeagueFilter('Brasileir')">🇧🇷 Brasileirão Série A</button>
    <button class="filter-btn" onclick="setLeagueFilter('Premier')">🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League</button>
    <button class="filter-btn" onclick="setLeagueFilter('Champions')">⭐ Champions League</button>
    <button class="filter-btn" onclick="setLeagueFilter('La Liga')">🇪🇸 La Liga</button>
    <button class="filter-btn" onclick="setLeagueFilter('Libertadores')">🏆 Copa Libertadores</button>
</div>

<div class="matches-grid" id="matches-container">
    <p style="text-align: center; color: #94a3b8; padding: 20px;">Carregando partidas em tempo real...</p>
</div>

<script>
    const WS_URL = "ws://localhost:{server_port}/ws/live";
    let socket = null;
    let reconnectTimeout = null;
    let pingInterval = null;
    let currentMatches = [];
    let activeStatusGroup = 'ALL';
    let activeLeagueFilter = 'ALL';
    let searchQuery = '';
    let selectedMatchId = '123';

    // ---------------------------------------------------------
    // CONEXÃO WEBSOCKET & SISTEMA DE SALAS
    // ---------------------------------------------------------
    function connectWebSocket() {{
        updateBadge('connecting', 'Conectando ao WebSockets...');
        try {{
            socket = new WebSocket(WS_URL);
        }} catch(e) {{
            fallbackSSE();
            return;
        }}

        socket.onopen = () => {{
            updateBadge('connected', '🟢 WebSocket Conectado (<5ms)');
            hideDisconnectBanner();
            startPingLoop();
            // Entrar na sala do jogo atualmente selecionado
            socket.send(JSON.stringify({{ action: "join_match", matchId: selectedMatchId }}));
        }};

        socket.onmessage = (event) => {{
            try {{
                const msg = JSON.parse(event.data);
                handleIncomingMessage(msg);
            }} catch(e) {{
                console.error("Erro parsing WS message:", e);
            }}
        }};

        socket.onclose = () => {{
            updateBadge('error', 'Desconectado');
            showDisconnectBanner();
            stopPingLoop();
            scheduleReconnect();
        }};

        socket.onerror = () => {{
            socket.close();
        }};
    }}

    function scheduleReconnect() {{
        if (reconnectTimeout) clearTimeout(reconnectTimeout);
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
    }}

    function showDisconnectBanner() {{
        const b = document.getElementById('disconnect-banner');
        if (b) b.style.display = 'flex';
    }}

    function hideDisconnectBanner() {{
        const b = document.getElementById('disconnect-banner');
        if (b) b.style.display = 'none';
    }}

    function startPingLoop() {{
        if (pingInterval) clearInterval(pingInterval);
        pingInterval = setInterval(() => {{
            if (socket && socket.readyState === WebSocket.OPEN) {{
                socket.send(JSON.stringify({{ action: "ping" }}));
            }}
        }}, 8000);
    }}

    function stopPingLoop() {{
        if (pingInterval) clearInterval(pingInterval);
    }}

    function updateBadge(state, text) {{
        const el = document.getElementById('connection-status');
        const txt = document.getElementById('conn-text');
        if (el) el.className = 'connection-badge ' + state;
        if (txt) txt.textContent = text;
    }}

    // ---------------------------------------------------------
    // GERENCIAMENTO DE MENSAGENS E ATUALIZAÇÕES EM TEMPO REAL
    // ---------------------------------------------------------
    function handleIncomingMessage(msg) {{
        // 1. Snapshot Inicial
        if (msg.type === "SNAPSHOT") {{
            if (msg.matches && msg.matches.length > 0) {{
                currentMatches = msg.matches;
                populateMatchSelector();
                updateCounters();
                renderMatches();
            }}
            return;
        }}

        // 2. Atualização de Telemetria do Jogo Específico (Match Tracker 2D)
        if (msg.type === "match_update" && msg.data) {{
            if (String(msg.matchId) === String(selectedMatchId)) {{
                updateMatchTracker(msg.data);
            }}
            return;
        }}

        // 3. Atualização Global de Partidas
        if (msg.channel === "matches:live" && msg.data && msg.data.matches) {{
            currentMatches = msg.data.matches;
            updateCounters();
            updateOrRenderMatches();
            return;
        }}

        // 4. Eventos Globais de Gols e Odds
        if (msg.channel === "events:realtime" || msg.channel === "goals:alerts") {{
            const ev = msg.data || msg;
            if (ev.type === "GOAL") {{
                const scoreEl = document.getElementById(`score-${{ev.match_id}}`);
                if (scoreEl) scoreEl.textContent = ev.new_score;
                if (String(ev.match_id) === String(selectedMatchId)) {{
                    triggerGoalCelebration(ev.team_scored || ev.home_team, ev.scorer);
                }}
            }}
        }}
    }}

    // ---------------------------------------------------------
    // RENDERIZAÇÃO DO MATCH TRACKER 2D (CAMPO SVG + ESTATÍSTICAS)
    // ---------------------------------------------------------
    function updateMatchTracker(data) {{
        if (!data) return;

        // Cabeçalho
        const teamsEl = document.getElementById('track-teams');
        const scoreEl = document.getElementById('track-score');
        const clockEl = document.getElementById('track-clock');
        const homeLabel = document.getElementById('pitch-home-name');
        const awayLabel = document.getElementById('pitch-away-name');

        if (teamsEl) teamsEl.textContent = `${{data.timeCasa}} vs ${{data.timeVisitante}}`;
        if (scoreEl) scoreEl.textContent = data.placar;
        if (clockEl) clockEl.textContent = `AO VIVO (${{data.tempo || "38'"}})`;
        if (homeLabel) homeLabel.textContent = data.timeCasa.toUpperCase();
        if (awayLabel) awayLabel.textContent = data.timeVisitante.toUpperCase();

        // Posição da Bola no Campo SVG
        const ball = document.getElementById('pitch-ball');
        const banner = document.getElementById('pitch-event-banner');
        const coneHome = document.getElementById('attack-cone-home');
        const coneAway = document.getElementById('attack-cone-away');

        const ev = data.ultimoEvento;
        if (ev && ball) {{
            ball.setAttribute('cx', ev.bolaX || 50);
            ball.setAttribute('cy', ev.bolaY || 30);

            if (banner) {{
                banner.textContent = ev.texto || "Bola em jogo";
                banner.className = 'event-banner' + (ev.intensidade === 'perigo_maximo' ? ' danger' : '');
            }}

            // Animação dos Cones de Pressão de Ataque
            if (coneHome && coneAway) {{
                if (ev.tipo === 'DANGEROUS_ATTACK' || ev.tipo === 'SHOT_ON_TARGET') {{
                    if (ev.time === 'casa') {{
                        coneHome.setAttribute('opacity', '0.75');
                        coneAway.setAttribute('opacity', '0');
                    }} else {{
                        coneHome.setAttribute('opacity', '0');
                        coneAway.setAttribute('opacity', '0.75');
                    }}
                }} else {{
                    coneHome.setAttribute('opacity', '0');
                    coneAway.setAttribute('opacity', '0');
                }}
            }}

            if (ev.tipo === 'GOAL') {{
                triggerGoalCelebration(ev.time === 'casa' ? data.timeCasa : data.timeVisitante);
            }}
        }}

        // Odds Sincronizadas
        if (data.odds) {{
            const cEl = document.getElementById('track-odd-c');
            const dEl = document.getElementById('track-odd-d');
            const aEl = document.getElementById('track-odd-a');
            if (cEl) cEl.textContent = Number(data.odds.casa).toFixed(2);
            if (dEl) dEl.textContent = Number(data.odds.empate).toFixed(2);
            if (aEl) aEl.textContent = Number(data.odds.fora).toFixed(2);
        }}

        // Estatísticas do Confronto
        const s = data.stats;
        if (s) {{
            setStatDual('posse', s.posseCasa, s.posseFora, '%');
            setStatDual('chutes', s.chutesGolCasa, s.chutesGolFora, '');
            setStatDual('ataques', s.ataquesPerigososCasa, s.ataquesPerigososFora, '');
            setStatDual('cantos', s.escanteiosCasa, s.escanteiosFora, '');
            setStatDual('xg', s.xgCasa, s.xgFora, '');
        }}
    }}

    function setStatDual(id, valH, valA, suffix) {{
        const txtH = document.getElementById(`stat-${{id}}-casa`);
        const txtA = document.getElementById(`stat-${{id}}-fora`);
        const barH = document.getElementById(`bar-${{id}}-casa`);
        const barA = document.getElementById(`bar-${{id}}-fora`);

        if (txtH) txtH.textContent = `${{valH}}${{suffix}}`;
        if (txtA) txtA.textContent = `${{valA}}${{suffix}}`;

        const total = (Number(valH) + Number(valA)) || 1;
        const pctH = Math.min(95, Math.max(5, Math.round((Number(valH) / total) * 100)));
        const pctA = 100 - pctH;

        if (barH) barH.style.width = `${{pctH}}%`;
        if (barA) barA.style.width = `${{pctA}}%`;
    }}

    function triggerGoalCelebration(team, scorer) {{
        const overlay = document.getElementById('goal-celebration-overlay');
        const sub = document.getElementById('celebration-subtitle');
        if (overlay && sub) {{
            sub.textContent = `Gol do ${{team}}! ${{scorer ? '(' + scorer + ')' : ''}}`;
            overlay.style.display = 'flex';
            setTimeout(() => {{ overlay.style.display = 'none'; }}, 3500);
        }}
    }}

    // ---------------------------------------------------------
    // TROCA DE PARTIDA E SELEÇÃO (JOIN / LEAVE ROOM)
    // ---------------------------------------------------------
    function changeTrackedMatch(newMatchId) {{
        if (String(newMatchId) === String(selectedMatchId)) return;
        
        // Sair da sala antiga
        if (socket && socket.readyState === WebSocket.OPEN) {{
            socket.send(JSON.stringify({{ action: "leave_match", matchId: selectedMatchId }}));
        }}

        selectedMatchId = String(newMatchId);

        // Entrar na nova sala
        if (socket && socket.readyState === WebSocket.OPEN) {{
            socket.send(JSON.stringify({{ action: "join_match", matchId: selectedMatchId }}));
        }}

        // Atualizar visual da seleção
        const sel = document.getElementById('match-selector');
        if (sel) sel.value = selectedMatchId;

        document.querySelectorAll('.match-card').forEach(card => card.classList.remove('active-selected'));
        const activeCard = document.getElementById(`card-${{selectedMatchId}}`);
        if (activeCard) activeCard.classList.add('active-selected');

        // Buscar dados imediatos via HTTP REST fallback
        fetch(`http://localhost:{server_port}/api/telemetry/${{selectedMatchId}}`)
            .then(r => r.json())
            .then(data => updateMatchTracker(data))
            .catch(() => {{}});
    }}

    function populateMatchSelector() {{
        const sel = document.getElementById('match-selector');
        if (!sel) return;
        sel.innerHTML = currentMatches.slice(0, 35).map(m => {{
            const mId = String(m.id || `${{m.home_team}}_vs_${{m.away_team}}`);
            return `<option value="${{mId}}">${{m.home_team}} x ${{m.away_team}} (${{m.status_label || 'Ao Vivo'}})</option>`;
        }}).join('');
        if (selectedMatchId) sel.value = selectedMatchId;
    }}

    // ---------------------------------------------------------
    // DISPARO DE SIMULAÇÃO TÁTICA (INSTANTÂNEO)
    // ---------------------------------------------------------
    function simulatePitch(eventType, team) {{
        if (socket && socket.readyState === WebSocket.OPEN) {{
            socket.send(JSON.stringify({{
                action: "simulate_pitch_event",
                matchId: selectedMatchId,
                event: {{ type: eventType, team: team }}
            }}));
        }} else {{
            fetch(`http://localhost:{server_port}/api/simulate/pitch-event`, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ matchId: selectedMatchId, eventType: eventType, team: team }})
            }})
            .then(r => r.json())
            .then(res => {{ if (res.telemetry) updateMatchTracker(res.telemetry); }});
        }}
    }}

    // ---------------------------------------------------------
    // BUSCA, FILTROS E LISTA DE JOGOS
    // ---------------------------------------------------------
    function handleSearch(val) {{
        searchQuery = val.toLowerCase().trim();
        renderMatches();
    }}

    function setStatusGroup(group) {{
        activeStatusGroup = group;
        document.querySelectorAll('.tab-status-btn').forEach(btn => btn.classList.remove('active'));
        event.target.closest('.tab-status-btn').classList.add('active');
        renderMatches();
    }}

    function setLeagueFilter(league) {{
        activeLeagueFilter = league;
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');
        renderMatches();
    }}

    function updateCounters() {{
        let total = currentMatches.length;
        let live = currentMatches.filter(m => isMatchLive(m)).length;
        let pre = currentMatches.filter(m => !isMatchLive(m) && !isMatchPost(m)).length;
        let post = currentMatches.filter(m => isMatchPost(m)).length;

        document.getElementById('count-all').textContent = `(${{total}})`;
        document.getElementById('count-live').textContent = `(${{live}})`;
        document.getElementById('count-pre').textContent = `(${{pre}})`;
        document.getElementById('count-post').textContent = `(${{post}})`;
        document.getElementById('match-counter').textContent = `${{total}} partidas monitoradas`;
    }}

    function isMatchLive(m) {{
        return m.badge_type === 'live' || (m.status_label && m.status_label.includes('AO VIVO'));
    }}

    function isMatchPost(m) {{
        return m.badge_type === 'post' || (m.status_label && m.status_label.includes('Encerrado'));
    }}

    function updateOrRenderMatches() {{
        const container = document.getElementById('matches-container');
        if (container.children.length === 0 || container.querySelector('p')) {{
            renderMatches();
            return;
        }}
        currentMatches.forEach(m => {{
            const mId = m.id || `${{m.home_team}}_vs_${{m.away_team}}`;
            const scoreEl = document.getElementById(`score-${{mId}}`);
            const statusEl = document.getElementById(`status-${{mId}}`);
            if (scoreEl) scoreEl.textContent = `${{m.home_score}} x ${{m.away_score}}`;
            if (statusEl) statusEl.textContent = m.status_label;
        }});
    }}

    function renderMatches() {{
        const container = document.getElementById('matches-container');
        let list = currentMatches;

        if (activeStatusGroup === 'LIVE') {{
            list = list.filter(m => isMatchLive(m));
        }} else if (activeStatusGroup === 'PRE') {{
            list = list.filter(m => !isMatchLive(m) && !isMatchPost(m));
        }} else if (activeStatusGroup === 'POST') {{
            list = list.filter(m => isMatchPost(m));
        }}

        if (activeLeagueFilter !== 'ALL') {{
            list = list.filter(m => m.league && m.league.toLowerCase().includes(activeLeagueFilter.toLowerCase()));
        }}

        if (searchQuery) {{
            list = list.filter(m => 
                (m.home_team && m.home_team.toLowerCase().includes(searchQuery)) ||
                (m.away_team && m.away_team.toLowerCase().includes(searchQuery)) ||
                (m.league && m.league.toLowerCase().includes(searchQuery))
            );
        }}

        if (list.length === 0) {{
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #94a3b8;">
                    Nenhuma partida encontrada para os critérios selecionados.
                </div>
            `;
            return;
        }}

        container.innerHTML = list.map(m => {{
            const mId = String(m.id || `${{m.home_team}}_vs_${{m.away_team}}`);
            const live = isMatchLive(m);
            const post = isMatchPost(m);
            const statusClass = live ? 'live' : (post ? 'post' : 'pre');
            const isSelected = (mId === selectedMatchId) ? 'active-selected' : '';

            return `
            <div class="match-card ${{isSelected}}" id="card-${{mId}}" onclick="changeTrackedMatch('${{mId}}')">
                <div class="card-header">
                    <span class="league-title">🏆 ${{m.league || 'Competição'}} • ${{m.venue || 'Estádio'}}</span>
                    <div class="badges-group">
                        <span class="status-badge ${{statusClass}}" id="status-${{mId}}">${{m.status_label || 'Agendado'}}</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="teams-section">
                        <div class="match-title">
                            ${{m.home_team}} 
                            <span class="score-badge" id="score-${{mId}}">${{m.home_score}} x ${{m.away_score}}</span> 
                            ${{m.away_team}}
                        </div>
                    </div>
                    <button class="btn-open-tracker" onclick="event.stopPropagation(); changeTrackedMatch('${{mId}}')">
                        🏟️ Abrir Match Tracker 2D
                    </button>
                </div>
            </div>
            `;
        }}).join('');
    }}

    // Iniciar conexão ao carregar
    connectWebSocket();
</script>
</body>
</html>
"""
