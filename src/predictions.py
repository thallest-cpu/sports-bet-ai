"""
Modelo estatístico de previsão de partidas — BetAI Quant Pro.

Abordagem: modelo de Poisson bivariado simplificado, usando as médias de
gols marcados/sofridos (mandante e visitante) vindas das estatísticas REAIS
da API (SportsDataAPI.get_team_statistics). Não usa nenhum dado hardcoded:
se as estatísticas não estiverem disponíveis, a função retorna None e a UI
deve exibir "não disponível" em vez de inventar uma previsão.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class MatchPrediction:
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    expected_goals_home: float
    expected_goals_away: float
    over_2_5_pct: float
    btts_pct: float  # ambas equipes marcam
    confidence: str  # "baixa" | "média" | "alta" — baseada na quantidade de jogos usados


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _extract_goal_averages(team_stats: dict, is_home: bool) -> tuple[float, float] | None:
    """
    Extrai (média de gols marcados, média de gols sofridos) das estatísticas
    retornadas pela API-Football (endpoint /teams/statistics), separando
    mandante/visitante quando disponível.
    """
    try:
        goals = team_stats["goals"]
        side = "home" if is_home else "away"
        scored_avg = goals["for"]["average"][side]
        conceded_avg = goals["against"]["average"][side]
        if scored_avg is None or conceded_avg is None:
            return None
        return float(scored_avg), float(conceded_avg)
    except (KeyError, TypeError, ValueError):
        return None


def _games_played(team_stats: dict) -> int:
    try:
        fixtures = team_stats.get("fixtures", {}).get("played", {})
        return int(fixtures.get("total") or 0)
    except (TypeError, ValueError):
        return 0


def predict_match(home_team_stats: dict | None, away_team_stats: dict | None) -> MatchPrediction | None:
    """
    Gera uma previsão a partir das estatísticas reais dos dois times na
    temporada atual. Retorna None se não houver dados suficientes — nunca
    inventa números.
    """
    if not home_team_stats or not away_team_stats:
        return None

    home_avgs = _extract_goal_averages(home_team_stats, is_home=True)
    away_avgs = _extract_goal_averages(away_team_stats, is_home=False)
    if home_avgs is None or away_avgs is None:
        return None

    home_scored_avg, home_conceded_avg = home_avgs
    away_scored_avg, away_conceded_avg = away_avgs

    # Força de ataque/defesa relativa (média simples entre ataque de um time
    # e defesa do adversário) — abordagem clássica de modelo Poisson simples.
    expected_goals_home = max((home_scored_avg + away_conceded_avg) / 2, 0.05)
    expected_goals_away = max((away_scored_avg + home_conceded_avg) / 2, 0.05)

    max_goals = 10
    home_win = draw = away_win = 0.0
    over_2_5 = 0.0
    btts = 0.0

    for hg in range(max_goals + 1):
        p_hg = _poisson_pmf(hg, expected_goals_home)
        for ag in range(max_goals + 1):
            p_ag = _poisson_pmf(ag, expected_goals_away)
            p = p_hg * p_ag

            if hg > ag:
                home_win += p
            elif hg == ag:
                draw += p
            else:
                away_win += p

            if hg + ag >= 3:
                over_2_5 += p
            if hg >= 1 and ag >= 1:
                btts += p

    games_used = min(_games_played(home_team_stats), _games_played(away_team_stats))
    if games_used >= 10:
        confidence = "alta"
    elif games_used >= 4:
        confidence = "média"
    else:
        confidence = "baixa"

    return MatchPrediction(
        home_win_pct=round(home_win * 100, 1),
        draw_pct=round(draw * 100, 1),
        away_win_pct=round(away_win * 100, 1),
        expected_goals_home=round(expected_goals_home, 2),
        expected_goals_away=round(expected_goals_away, 2),
        over_2_5_pct=round(over_2_5 * 100, 1),
        btts_pct=round(btts * 100, 1),
        confidence=confidence,
    )
