import urllib.parse
from typing import Dict, Any, List

def format_phone_number(raw_phone: str) -> str:
    """Formata número de telefone brasileiro no padrão visual +55 (DD) 9XXXX-XXXX."""
    digits = "".join(c for c in str(raw_phone) if c.isdigit())
    if digits.startswith("55") and len(digits) >= 12:
        digits = digits[2:]
    if len(digits) == 11:
        return f"+55 ({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"+55 ({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return raw_phone

def sanitize_phone_digits(raw_phone: str) -> str:
    """Extrai dígitos com código do país 55 garantido."""
    digits = "".join(c for c in str(raw_phone) if c.isdigit())
    if not digits.startswith("55") and len(digits) in [10, 11]:
        digits = "55" + digits
    return digits if digits else ""

def format_prematch_whatsapp_message(
    match_info: Dict[str, Any],
    pred: Dict[str, Any],
    corners: Dict[str, Any],
    cards: Dict[str, Any],
    home_star: Dict[str, Any],
    away_star: Dict[str, Any],
    verdict: Dict[str, Any]
) -> str:
    """
    Formata a mensagem de alta conversão do WhatsApp enviada 10 minutos antes do jogo começar.
    Contém: Probabilidade de vitória, escanteios, cartões, artilheiros e recomendação de aposta.
    """
    home = match_info.get("home_team", "Mandante")
    away = match_info.get("away_team", "Visitante")
    league = match_info.get("league", "Grandes Ligas")
    time_str = match_info.get("time_str", "Em 10 minutos")

    p_h = round(pred.get("prob_home_win", 0.45) * 100, 1)
    p_d = round(pred.get("prob_draw", 0.28) * 100, 1)
    p_a = round(pred.get("prob_away_win", 0.27) * 100, 1)

    fav = home if p_h >= p_a else away
    fav_prob = max(p_h, p_a)

    msg = f"""🔥 *[BETAI VIP • ALERTA PRÉ-JOGO 10 MIN]* 🔥
🏆 *{league}*
⚽ *{home} vs {away}*
⏰ *Início em 10 minutos* ({time_str})

━━━━━━━━━━━━━━━━━━━━
📊 *PROBABILIDADE DE VITÓRIA (1X2)*
• {home}: *{p_h}%* (Odd Justa: {pred.get('fair_odd_home', 2.10)})
• Empate: *{p_d}%* (Odd Justa: {pred.get('fair_odd_draw', 3.30)})
• {away}: *{p_a}%* (Odd Justa: {pred.get('fair_odd_away', 3.20)})
👉 *Favorito Calculado:* *{fav}* ({fav_prob}% de chance)

🚩 *PROJEÇÃO DE ESCANTEIOS (CORNERS)*
• Expectativa no jogo: *{corners.get('total_expected_corners', 10.2)} cantos*
• Mais de 8.5 Cantos: *{corners.get('prob_over_85', 75)}%*
• Mais de 9.5 Cantos: *{corners.get('prob_over_95', 65)}%*
• Maior volume de cantos: *{corners.get('quem_tem_mais', home)}*

🟨 *PROJEÇÃO DE CARTÕES (DISCIPLINA)*
• Expectativa: *{cards.get('total_expected_cards', 4.8)} cartões*
• Mais de 4.5 Cartões: *{cards.get('prob_over_45', 62)}%*
• Tendência do Clássico: *{cards.get('intensidade', 'Alta Disputa')}*

👑 *CRAQUES & ARTILHEIROS EM CAMPO*
• *{home}:* {home_star.get('nome', 'Camisa 9')} ({home_star.get('posicao', 'Atacante')} • {home_star.get('gols', 0)} gols)
• *{away}:* {away_star.get('nome', 'Camisa 9')} ({away_star.get('posicao', 'Atacante')} • {away_star.get('gols', 0)} gols)

━━━━━━━━━━━━━━━━━━━━
🎯 *PALPITE EXCLUSIVO DA IA:*
💡 *No que apostar:* *{verdict.get('no_que_apostar', 'Vitória do Favorito')}*
💰 *Odd Recomendada:* *{verdict.get('odd_alvo', 1.80)}*
🛡️ *Gestão de Banca:* *{verdict.get('stake_sugerida', '3.0% da Banca')}*
⭐ *Confiança:* {verdict.get('confianca', '⭐⭐⭐⭐ Alta')}
━━━━━━━━━━━━━━━━━━━━
_BetAI Quant Pro • Sistema VIP para Assinantes_"""

    return msg

def format_goal_whatsapp_message(
    match_name: str,
    scoring_team: str,
    minute: str,
    new_score: str,
    scorer_name: str,
    updated_prob_text: str
) -> str:
    """
    Formata o alerta instantâneo de gol enviado no WhatsApp para os jogos que o assinante escolheu acompanhar.
    """
    return f"""⚽🚨 *GOOOOOOL EM TEMPO REAL!* 🚨⚽
🏟️ *{match_name}*
⏱️ Minuto: *{minute}*

🔥 Gol de: *{scorer_name}* ({scoring_team})
📊 *NOVO PLACAR:* *{new_score}*

📈 *ATUALIZAÇÃO DE PROBABILIDADES AO VIVO:*
{updated_prob_text}

⚡ _Notificação automática BetAI para jogos selecionados._"""

def generate_whatsapp_web_link(phone: str, message: str) -> str:
    """Gera um link direto do WhatsApp Web com a mensagem pré-formatada e pronta para envio."""
    clean_phone = "".join(c for c in phone if c.isdigit())
    encoded_text = urllib.parse.quote(message)
    if clean_phone:
        return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
    return f"https://api.whatsapp.com/send?text={encoded_text}"
