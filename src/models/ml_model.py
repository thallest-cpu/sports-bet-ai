import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

class MLMatchClassifier:
    """
    Modelo de Machine Learning supervisionado treinado com histórico de partidas
    para prever probabilidades de vitória mandante, empate ou vitória visitante.
    """

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
        self.scaler = StandardScaler()
        self.is_fitted = False

    def prepare_dataset(self, df: pd.DataFrame, team_stats: dict):
        """Extrai features de cada partida para treinamento."""
        X, y = [], []
        
        for _, row in df.iterrows():
            h_team = row['HomeTeam']
            a_team = row['AwayTeam']
            ftr = row.get('FTR')
            
            if pd.isna(ftr) or h_team not in team_stats or a_team not in team_stats:
                continue

            h_stat = team_stats[h_team]
            a_stat = team_stats[a_team]

            features = [
                h_stat["home_attack"],
                h_stat["home_defense"],
                a_stat["away_attack"],
                a_stat["away_defense"],
                h_stat["recent_points_avg"],
                a_stat["recent_points_avg"],
                h_stat["recent_goals_scored_avg"],
                a_stat["recent_goals_scored_avg"],
                row.get("Odd_H", 2.0),
                row.get("Odd_D", 3.2),
                row.get("Odd_A", 3.5),
            ]

            # Label: 0=Mandante (H), 1=Empate (D), 2=Visitante (A)
            target = 0 if ftr == 'H' else (1 if ftr == 'D' else 2)
            X.append(features)
            y.append(target)

        return np.array(X), np.array(y)

    def train(self, df: pd.DataFrame, team_stats: dict):
        """Treina o modelo nos dados fornecidos."""
        X, y = self.prepare_dataset(df, team_stats)
        if len(X) < 30:
            return False

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        return True

    def predict_probabilities(self, home_team: str, away_team: str, team_stats: dict, odds: dict = None):
        """Gera probabilidades [Home, Draw, Away] usando Machine Learning."""
        if not self.is_fitted:
            return {"ml_home": 0.45, "ml_draw": 0.28, "ml_away": 0.27}

        h_stat = team_stats.get(home_team, {"home_attack": 1.0, "home_defense": 1.0, "recent_points_avg": 1.0, "recent_goals_scored_avg": 1.2})
        a_stat = team_stats.get(away_team, {"away_attack": 1.0, "away_defense": 1.0, "recent_points_avg": 1.0, "recent_goals_scored_avg": 1.0})

        if odds is None:
            odds = {"Odd_H": 2.10, "Odd_D": 3.30, "Odd_A": 3.40}

        features = np.array([[
            h_stat.get("home_attack", 1.0),
            h_stat.get("home_defense", 1.0),
            a_stat.get("away_attack", 1.0),
            a_stat.get("away_defense", 1.0),
            h_stat.get("recent_points_avg", 1.0),
            a_stat.get("recent_points_avg", 1.0),
            h_stat.get("recent_goals_scored_avg", 1.2),
            a_stat.get("recent_goals_scored_avg", 1.0),
            odds.get("Odd_H", 2.10),
            odds.get("Odd_D", 3.30),
            odds.get("Odd_A", 3.40),
        ]])

        X_scaled = self.scaler.transform(features)
        probs = self.model.predict_proba(X_scaled)[0]

        # Garantir ordenação das 3 classes
        prob_dict = {0: 0.33, 1: 0.33, 2: 0.33}
        for idx, cls in enumerate(self.model.classes_):
            prob_dict[cls] = probs[idx]

        return {
            "ml_prob_home": float(prob_dict[0]),
            "ml_prob_draw": float(prob_dict[1]),
            "ml_prob_away": float(prob_dict[2]),
        }
