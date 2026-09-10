import pandas as pd
import numpy as np

def calculate_ev(model_prob: float, bookmaker_odd: float) -> float:
    """
    Calcula o Valor Esperado (+EV) de uma aposta:
    EV = (Probabilidade_IA * Odd) - 1
    Retorna o valor em decimal (ex: 0.08 para +8%).
    """
    if bookmaker_odd <= 1.0 or model_prob <= 0.0:
        return -1.0
    return (model_prob * bookmaker_odd) - 1.0

def calculate_kelly_stake(model_prob: float, bookmaker_odd: float, fraction: float = 0.25) -> float:
    """
    Critério de Kelly Fracionário (padrão: 1/4 Kelly para controle rígido de risco).
    Retorna a porcentagem da banca recomendada para a aposta (entre 0% e 5%).
    """
    if bookmaker_odd <= 1.0 or model_prob <= 0.0:
        return 0.0
    
    b = bookmaker_odd - 1.0
    p = model_prob
    q = 1.0 - p
    
    kelly_full = (b * p - q) / b
    if kelly_full <= 0:
        return 0.0
    
    # Kelly fracionário com teto de segurança em 5% da banca por aposta
    recommended_pct = (kelly_full * fraction) * 100
    return round(min(5.0, recommended_pct), 2)

def evaluate_bet_market(market_name: str, model_prob: float, odd: float):
    """Gera um diagnóstico completo com EV, Odd Justa e Classificação."""
    ev = calculate_ev(model_prob, odd)
    ev_pct = round(ev * 100, 2)
    fair_odd = round(1.0 / max(0.001, model_prob), 2)
    implied_prob = round((1.0 / max(1.01, odd)) * 100, 1)
    kelly = calculate_kelly_stake(model_prob, odd)

    if ev_pct >= 8.0:
        badge = "💎 Super Valor (+EV Alto)"
        status = "positive"
    elif ev_pct >= 3.0:
        badge = "✅ Valor Detectado (+EV)"
        status = "positive"
    elif ev_pct > 0.0:
        badge = "⚖️ Valor Marginal"
        status = "neutral"
    else:
        badge = "❌ Sem Valor (Casa Favorita)"
        status = "negative"

    return {
        "Mercado": market_name,
        "Prob_IA (%)": round(model_prob * 100, 1),
        "Odd_Casa": odd,
        "Odd_Justa": fair_odd,
        "Prob_Casa (%)": implied_prob,
        "EV (%)": ev_pct,
        "Kelly_Sugestão (%)": kelly,
        "Classificação": badge,
        "Status": status
    }

def scan_value_opportunities(matches_df: pd.DataFrame, predictor, min_ev_pct: float = 3.0):
    """
    Varre as partidas do dataset e extrai todas as apostas que possuem EV positivo acima do filtro.
    """
    opportunities = []

    # Pegar partidas mais recentes (ex: últimas 20 partidas para análise e validação)
    recent_matches = matches_df.tail(25)

    for _, match in recent_matches.iterrows():
        home = match['HomeTeam']
        away = match['AwayTeam']
        date_str = str(match.get('Date', ''))[:10]

        pred = predictor.predict_match(home, away)

        # Checar mercados 1X2 e Over/Under
        markets_to_check = [
            ("Vitória Mandante (" + home + ")", pred["prob_home_win"], match.get("Odd_H", 2.0)),
            ("Empate", pred["prob_draw"], match.get("Odd_D", 3.2)),
            ("Vitória Visitante (" + away + ")", pred["prob_away_win"], match.get("Odd_A", 3.5)),
            ("Over 2.5 Gols", pred["prob_over_25"], match.get("Odd_Over25", 1.9)),
            ("Under 2.5 Gols", pred["prob_under_25"], match.get("Odd_Under25", 1.95)),
            ("Ambas Marcam (Sim)", pred["prob_btts_yes"], 1.85),
        ]

        for m_name, m_prob, m_odd in markets_to_check:
            res = evaluate_bet_market(m_name, m_prob, m_odd)
            if res["EV (%)"] >= min_ev_pct:
                opportunities.append({
                    "Data": date_str,
                    "Jogo": f"{home} vs {away}",
                    "Mercado": res["Mercado"],
                    "Odd Casa": res["Odd_Casa"],
                    "Odd Justa IA": res["Odd_Justa"],
                    "Prob IA (%)": res["Prob_IA (%)"],
                    "Prob Casa (%)": res["Prob_Casa (%)"],
                    "EV (%)": res["EV (%)"],
                    "Kelly Sugerido (%)": res["Kelly_Sugestão (%)"],
                    "Classificação": res["Classificação"]
                })

    opp_df = pd.DataFrame(opportunities)
    if not opp_df.empty:
        opp_df = opp_df.sort_values(by="EV (%)", ascending=False).reset_index(drop=True)
    return opp_df
