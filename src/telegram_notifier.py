import urllib.parse
from typing import Dict, Any

DEFAULT_TELEGRAM_BOT = "betai_quant_bot"

def format_telegram_prematch_message(
    match_info: Dict[str, Any],
    pred: Dict[str, Any],
    corners: Dict[str, Any],
    cards: Dict[str, Any],
    home_star: Dict[str, Any],
    away_star: Dict[str, Any],
    verdict: Dict[str, Any]
) -> str:
    """Formata o alerta pré-jogo de 10 minutos para o canal/bot do Telegram."""
    home = match_info.get("home_team", "Mandante")
    away = match_info.get("away_team", "Visitante")
    league = match_info.get("league", "Campeonato")
    time_str = match_info.get("time_str", "Em breve")

    msg = (
        f"🔥 *[BETAI QUANT • ALERTA PRÉ-JOGO 10 MIN]* 🔥\n\n"
        f"🏆 *{league}*\n"
        f"⚽ *{home} vs {away}*\n"
        f"⏰ Início: {time_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *PROBABILIDADES CALCULADAS PELA IA:*\n"
        f"• 🏠 Vitória {home}: *{pred['prob_home_win']*100:.1f}%* (Odd Justa: {pred['fair_odd_home']})\n"
        f"• 🤝 Empate: *{pred['prob_draw']*100:.1f}%* (Odd Justa: {pred['fair_odd_draw']})\n"
        f"• ✈️ Vitória {away}: *{pred['prob_away_win']*100:.1f}%* (Odd Justa: {pred['fair_odd_away']})\n\n"
        f"🚩 *MERCADO DE ESCANTEIOS:*\n"
        f"• Total Esperado: *{corners['total_expected_corners']} cantos*\n"
        f"• Over 9.5 Cantos: *{corners['prob_over_95']}%* de chance\n"
        f"• Tendência: *{corners['quem_tem_mais']}*\n\n"
        f"🟨 *PROJEÇÃO DE CARTÕES:*\n"
        f"• Total Esperado: *{cards['total_expected_cards']} cartões*\n"
        f"• {cards['intensidade']}\n\n"
        f"👑 *DUELO DE CRAQUES:*\n"
        f"• {home}: *{home_star.get('nome', 'Destaque')}* ({home_star.get('posicao', 'Atacante')})\n"
        f"• {away}: *{away_star.get('nome', 'Destaque')}* ({away_star.get('posicao', 'Atacante')})\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *APOSTA RECOMENDADA COM VALOR (+EV):*\n"
        f"👉 *{verdict['no_que_apostar']}*\n"
        f"📈 Odd Mínima de Valor: *{verdict['odd_alvo']}*\n"
        f"💼 Gestão Sugerida: *{verdict['stake_sugerida']}*\n"
        f"💡 {verdict['motivo']}\n\n"
        f"⚠️ _{verdict['armadilha']}_\n\n"
        f"🤖 _BetAI Quant Pro • Modelo Dixon-Coles & Machine Learning_"
    )
    return msg

def format_telegram_goal_message(
    match_title: str,
    scoring_team: str,
    minute: str,
    current_score: str,
    scorer_name: str,
    live_impact: str
) -> str:
    """Formata o alerta instantâneo de gol ao vivo para o Telegram."""
    msg = (
        f"⚽🚨 *GOOOOOL NO JOGO!* 🚨⚽\n\n"
        f"🏟️ *{match_title}*\n"
        f"⏱️ Minuto: *{minute}*\n"
        f"👟 Autor do Gol: *{scorer_name}* ({scoring_team})\n"
        f"🔥 Placar Atual: *{current_score}*\n\n"
        f"📊 *IMPACTO AO VIVO DA IA:*\n"
        f"{live_impact}\n\n"
        f"⚡ _Acompanhamento em tempo real via BetAI Quant Server_"
    )
    return msg

def generate_telegram_bot_link(message: str, bot_username: str = DEFAULT_TELEGRAM_BOT) -> str:
    """Gera um link direto para compartilhar no Telegram."""
    encoded_text = urllib.parse.quote(message)
    return f"https://t.me/share/url?url=https://betaiquant.pro&text={encoded_text}"
