import pandas as pd
import numpy as np

def calculate_league_ratings(df: pd.DataFrame):
    """
    Calcula os parâmetros de força de ataque e defesa de cada equipe na liga,
    separando mando de campo (casa e fora).
    """
    total_home_games = len(df)
    total_away_games = len(df)
    
    if total_home_games == 0:
        return {}, {}, 1.5, 1.2

    avg_home_goals = df['FTHG'].mean()
    avg_away_goals = df['FTAG'].mean()

    # Cálculo agregado veloz usando groupby
    home_stats = df.groupby('HomeTeam').agg(
        home_games=('FTHG', 'count'),
        home_scored=('FTHG', 'sum'),
        home_conceded=('FTAG', 'sum')
    ).to_dict(orient='index')

    away_stats = df.groupby('AwayTeam').agg(
        away_games=('FTAG', 'count'),
        away_scored=('FTAG', 'sum'),
        away_conceded=('FTHG', 'sum')
    ).to_dict(orient='index')

    # Lista de todos os times
    teams = sorted(list(set(df['HomeTeam'].dropna().unique()) | set(df['AwayTeam'].dropna().unique())))

    # Histórico recente para cada time (últimos 5 jogos)
    team_stats = {}
    for team in teams:
        h = home_stats.get(team, {'home_games': 0, 'home_scored': 0, 'home_conceded': 0})
        a = away_stats.get(team, {'away_games': 0, 'away_scored': 0, 'away_conceded': 0})

        h_games = h['home_games']
        a_games = a['away_games']

        home_att = ((h['home_scored'] / h_games) / avg_home_goals) if h_games > 0 and avg_home_goals > 0 else 1.0
        home_def = ((h['home_conceded'] / h_games) / avg_away_goals) if h_games > 0 and avg_away_goals > 0 else 1.0

        away_att = ((a['away_scored'] / a_games) / avg_away_goals) if a_games > 0 and avg_away_goals > 0 else 1.0
        away_def = ((a['away_conceded'] / a_games) / avg_home_goals) if a_games > 0 and avg_home_goals > 0 else 1.0

        team_stats[team] = {
            "home_attack": max(0.2, home_att),
            "home_defense": max(0.2, home_def),
            "away_attack": max(0.2, away_att),
            "away_defense": max(0.2, away_def),
            "recent_points_avg": 1.2,
            "recent_goals_scored_avg": ((h['home_scored'] + a['away_scored']) / max(1, h_games + a_games)),
            "recent_goals_conceded_avg": ((h['home_conceded'] + a['away_conceded']) / max(1, h_games + a_games)),
            "total_games": h_games + a_games
        }

    return team_stats, avg_home_goals, avg_away_goals
