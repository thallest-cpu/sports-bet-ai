"""Modelo Poisson transparente baseado em estatísticas da temporada atual.

O módulo deliberadamente não cria dados ausentes. Se a fonte não fornecer
médias de gols válidas, a função principal retorna ``None``.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import math


def _num(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _nested(data: Dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def calculate_current_probabilities(home_stats: Dict[str, Any], away_stats: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Calcula probabilidades 1X2/Over/BTTS usando médias casa/fora atuais.

    A grade vai até 14 gols por equipe; depois normalizamos todas as métricas
    pela massa de probabilidade coberta. Isso evita a pequena distorção que
    ocorria quando a grade era truncada em 8 gols.
    """
    h_for = _num(_nested(home_stats, "goals", "for", "average", "home"))
    h_against = _num(_nested(home_stats, "goals", "against", "average", "home"))
    a_for = _num(_nested(away_stats, "goals", "for", "average", "away"))
    a_against = _num(_nested(away_stats, "goals", "against", "average", "away"))

    if None in (h_for, h_against, a_for, a_against):
        return None

    values = [h_for, h_against, a_for, a_against]
    if any(v < 0 for v in values):
        return None

    xg_home = max(0.15, min(4.5, (h_for + a_against) / 2.0))
    xg_away = max(0.15, min(4.5, (a_for + h_against) / 2.0))

    home_win = draw = away_win = over25 = btts = covered_mass = 0.0
    for i in range(15):
        pi = _poisson(i, xg_home)
        for j in range(15):
            p = pi * _poisson(j, xg_away)
            covered_mass += p
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            if i + j >= 3:
                over25 += p
            if i > 0 and j > 0:
                btts += p

    if covered_mass <= 0:
        return None

    home_win /= covered_mass
    draw /= covered_mass
    away_win /= covered_mass
    over25 /= covered_mass
    btts /= covered_mass

    return {
        "home": round(home_win * 100, 1),
        "draw": round(draw * 100, 1),
        "away": round(away_win * 100, 1),
        "over25": round(over25 * 100, 1),
        "btts": round(btts * 100, 1),
        "xg_home": round(xg_home, 2),
        "xg_away": round(xg_away, 2),
        "fair_home": round(1 / home_win, 2) if home_win else 0,
        "fair_draw": round(1 / draw, 2) if draw else 0,
        "fair_away": round(1 / away_win, 2) if away_win else 0,
    }


def extract_match_winner_odds(payload: list) -> list:
    """Extrai odds 1X2 reais do payload da API-Football."""
    rows = []
    for page in payload or []:
        for bookmaker in page.get("bookmakers", []) or []:
            bookmaker_name = bookmaker.get("name") or "Bookmaker"
            for bet in bookmaker.get("bets", []) or []:
                name = str(bet.get("name") or "").lower()
                if "match winner" not in name and "winner" not in name and "1x2" not in name:
                    continue
                for item in bet.get("values", []) or []:
                    try:
                        odd = float(item.get("odd"))
                    except (TypeError, ValueError):
                        continue
                    if odd <= 1.0:
                        continue
                    rows.append({
                        "bookmaker": bookmaker_name,
                        "selection": item.get("value") or "",
                        "odd": odd,
                    })
    return rows


def calculate_ev(prob_pct: float, odd: float) -> float:
    """Valor esperado percentual para uma odd decimal e probabilidade em %."""
    return round(((prob_pct / 100.0) * odd - 1.0) * 100.0, 1)
