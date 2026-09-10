import pandas as pd
import numpy as np
from .feature_engineering import calculate_league_ratings
from .models.poisson_model import PoissonMatchPredictor
from .value_finder import calculate_ev, calculate_kelly_stake

def run_backtest(df: pd.DataFrame, initial_bankroll: float = 1000.0, min_ev_pct: float = 3.0, stake_mode: str = "fixed"):
    """
    Executa um backtest cronológico sem viés de futuro (walk-forward).
    Para cada partida a partir de um período inicial de aquecimento, calcula probabilidades
    com base apenas no histórico anterior, identifica apostas com +EV e simula o saldo da banca.
    """
    if len(df) < 50:
        return None

    df_sorted = df.sort_values(by='Date' if 'Date' in df.columns else df.index).reset_index(drop=True)
    
    # 40 partidas iniciais para aquecimento dos índices estatísticos
    warmup_matches = 40
    bankroll = initial_bankroll
    bankroll_history = [initial_bankroll]
    bets_placed = []

    for i in range(warmup_matches, len(df_sorted)):
        past_data = df_sorted.iloc[:i]
        match = df_sorted.iloc[i]

        h_team = match['HomeTeam']
        a_team = match['AwayTeam']
        fthg = match['FTHG']
        ftag = match['FTAG']
        ftr = match['FTR']

        if pd.isna(fthg) or pd.isna(ftag):
            continue

        team_stats, avg_h, avg_a = calculate_league_ratings(past_data)
        if h_team not in team_stats or a_team not in team_stats:
            continue

        predictor = PoissonMatchPredictor(team_stats, avg_h, avg_a)
        pred = predictor.predict_match(h_team, a_team)

        # Checar se mandante tem +EV
        odd_h = match.get('Odd_H', 2.0)
        ev_h = calculate_ev(pred['prob_home_win'], odd_h) * 100

        # Checar se visitante tem +EV
        odd_a = match.get('Odd_A', 3.0)
        ev_a = calculate_ev(pred['prob_away_win'], odd_a) * 100

        # Checar Over 2.5 tem +EV
        odd_over = match.get('Odd_Over25', 1.9)
        ev_over = calculate_ev(pred['prob_over_25'], odd_over) * 100

        # Selecionar a melhor oportunidade da partida se passar da régua de corte
        candidate_bets = []
        if ev_h >= min_ev_pct and odd_h > 1.2:
            won = (ftr == 'H')
            candidate_bets.append(('Mandante (' + h_team + ')', pred['prob_home_win'], odd_h, ev_h, won))
        if ev_a >= min_ev_pct and odd_a > 1.2:
            won = (ftr == 'A')
            candidate_bets.append(('Visitante (' + a_team + ')', pred['prob_away_win'], odd_a, ev_a, won))
        if ev_over >= min_ev_pct and odd_over > 1.2:
            won = (fthg + ftag > 2.5)
            candidate_bets.append(('Over 2.5 Gols', pred['prob_over_25'], odd_over, ev_over, won))

        if not candidate_bets:
            bankroll_history.append(bankroll)
            continue

        # Seleciona o mercado com maior EV da partida
        best_bet = max(candidate_bets, key=lambda x: x[3])
        m_name, m_prob, m_odd, m_ev, m_won = best_bet

        if stake_mode == "kelly":
            kelly_pct = calculate_kelly_stake(m_prob, m_odd, fraction=0.20)
            stake = bankroll * (kelly_pct / 100.0)
            stake = max(5.0, min(stake, bankroll * 0.05)) # Mínimo R$5, máximo 5%
        else:
            stake = 20.0 # Aposta fixa de R$ 20

        if stake > bankroll:
            break

        if m_won:
            profit = stake * (m_odd - 1.0)
            bankroll += profit
        else:
            bankroll -= stake
            profit = -stake

        bankroll_history.append(round(bankroll, 2))
        bets_placed.append({
            "Partida": f"{h_team} vs {a_team}",
            "Mercado": m_name,
            "Odd": m_odd,
            "EV (%)": round(m_ev, 1),
            "Aposta": round(stake, 2),
            "Resultado": "Ganhou" if m_won else "Perdeu",
            "Lucro/Prejuízo": round(profit, 2),
            "Saldo Banca": round(bankroll, 2)
        })

    total_bets = len(bets_placed)
    if total_bets == 0:
        return None

    wins = sum(1 for b in bets_placed if b["Resultado"] == "Ganhou")
    win_rate = (wins / total_bets) * 100
    total_invested = sum(b["Aposta"] for b in bets_placed)
    net_profit = bankroll - initial_bankroll
    roi = (net_profit / total_invested * 100) if total_invested > 0 else 0

    return {
        "initial_bankroll": initial_bankroll,
        "final_bankroll": round(bankroll, 2),
        "net_profit": round(net_profit, 2),
        "roi_pct": round(roi, 2),
        "total_bets": total_bets,
        "wins": wins,
        "losses": total_bets - wins,
        "win_rate": round(win_rate, 1),
        "bankroll_curve": bankroll_history,
        "bets_df": pd.DataFrame(bets_placed)
    }
