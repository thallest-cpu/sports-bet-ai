import numpy as np
from scipy.stats import poisson

class PoissonMatchPredictor:
    """
    Modelo de previsão de partidas de futebol baseado em Distribuição de Poisson
    com ajuste para correlação de placares baixos (Dixon-Coles).
    """

    def __init__(self, team_stats: dict, avg_home_goals: float, avg_away_goals: float):
        self.team_stats = team_stats
        self.avg_home_goals = avg_home_goals
        self.avg_away_goals = avg_away_goals
        self.max_goals = 8  # Matriz de 0 a 7 gols

    def predict_match(self, home_team: str, away_team: str, rho: float = -0.06) -> dict:
        """
        Calcula as taxas esperadas de gols (lambda e mu) e a matriz de probabilidades
        de placar, probabilidades de 1X2, Over/Under e Ambas Marcam.
        """
        home_info = self.team_stats.get(home_team, {
            "home_attack": 1.0, "home_defense": 1.0
        })
        away_info = self.team_stats.get(away_team, {
            "away_attack": 1.0, "away_defense": 1.0
        })

        # Expectativa de gols (xG matemático)
        lambda_home = max(0.15, home_info["home_attack"] * away_info["away_defense"] * self.avg_home_goals)
        mu_away = max(0.15, away_info["away_attack"] * home_info["home_defense"] * self.avg_away_goals)

        # Matriz de probabilidade de placar
        prob_matrix = np.zeros((self.max_goals, self.max_goals))
        for h in range(self.max_goals):
            for a in range(self.max_goals):
                p_h = poisson.pmf(h, lambda_home)
                p_a = poisson.pmf(a, mu_away)
                prob = p_h * p_a

                # Ajuste Dixon-Coles para placares 0x0, 1x0, 0x1, 1x1
                if rho != 0:
                    if h == 0 and a == 0:
                        prob *= (1 - lambda_home * mu_away * rho)
                    elif h == 0 and a == 1:
                        prob *= (1 + lambda_home * rho)
                    elif h == 1 and a == 0:
                        prob *= (1 + mu_away * rho)
                    elif h == 1 and a == 1:
                        prob *= (1 - rho)

                prob_matrix[h, a] = max(0.0, prob)

        # Normalizar a matriz para que a soma seja 100%
        total_p = prob_matrix.sum()
        if total_p > 0:
            prob_matrix /= total_p

        # Probabilidades 1X2
        home_win_prob = np.sum(np.tril(prob_matrix, -1))
        draw_prob = np.sum(np.diag(prob_matrix))
        away_win_prob = np.sum(np.triu(prob_matrix, 1))

        # Mercados de Gols
        goals_grid = np.fromfunction(lambda i, j: i + j, (self.max_goals, self.max_goals))
        over_15_prob = np.sum(prob_matrix[goals_grid > 1.5])
        under_15_prob = 1.0 - over_15_prob

        over_25_prob = np.sum(prob_matrix[goals_grid > 2.5])
        under_25_prob = 1.0 - over_25_prob

        over_35_prob = np.sum(prob_matrix[goals_grid > 3.5])
        under_35_prob = 1.0 - over_35_prob

        # Ambas Marcam (BTTS)
        btts_yes_prob = np.sum(prob_matrix[1:, 1:])
        btts_no_prob = 1.0 - btts_yes_prob

        # Ranking dos 5 placares mais prováveis
        exact_scores = []
        for h in range(self.max_goals):
            for a in range(self.max_goals):
                exact_scores.append((f"{h} x {a}", prob_matrix[h, a]))
        exact_scores.sort(key=lambda x: x[1], reverse=True)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "lambda_home": float(lambda_home),
            "mu_away": float(mu_away),
            "total_expected_goals": float(lambda_home + mu_away),
            "prob_home_win": float(home_win_prob),
            "prob_draw": float(draw_prob),
            "prob_away_win": float(away_win_prob),
            "fair_odd_home": round(1.0 / max(0.001, home_win_prob), 2),
            "fair_odd_draw": round(1.0 / max(0.001, draw_prob), 2),
            "fair_odd_away": round(1.0 / max(0.001, away_win_prob), 2),
            "prob_over_15": float(over_15_prob),
            "prob_under_15": float(under_15_prob),
            "prob_over_25": float(over_25_prob),
            "prob_under_25": float(under_25_prob),
            "fair_odd_over_25": round(1.0 / max(0.001, over_25_prob), 2),
            "fair_odd_under_25": round(1.0 / max(0.001, under_25_prob), 2),
            "prob_over_35": float(over_35_prob),
            "prob_under_35": float(under_35_prob),
            "prob_btts_yes": float(btts_yes_prob),
            "prob_btts_no": float(btts_no_prob),
            "fair_odd_btts": round(1.0 / max(0.001, btts_yes_prob), 2),
            "top_scores": exact_scores[:6],
            "score_matrix": prob_matrix
        }
