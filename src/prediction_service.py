"""The same lifecycle is used by Streamlit and the optional scheduled worker."""
from datetime import timedelta
from src.audit import Ledger, parse_time, utcnow
from src.settings import secret
from src.current_model import calculate_current_probabilities
from src import sports_data_api as api


def open_ledger():
    url = secret('BETAI_DATABASE_URL')
    if not url:
        return None
    # SQLite is deliberately unavailable through production configuration.
    if not url.startswith(('postgresql://', 'postgres://')):
        raise ValueError('Configure PostgreSQL para o histórico permanente')
    return Ledger(url)


def evidence_for(home, away, league, season):
    stamps = [api.data_observed_at(s) for s in (home, away)]
    if not all(stamps):
        return None
    for stats in (home, away):
        metadata = stats.get('league') or {}
        if metadata.get('id') != league or metadata.get('season') != season:
            return None
    try:
        if int(home['fixtures']['played']['home']) < 3 or int(away['fixtures']['played']['away']) < 3:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return {'source': 'API-Football', 'observed_at': min(stamps), 'league': league,
            'season': season, 'home_stats': home, 'away_stats': away}


def reconcile(ledger, league):
    """Recheck pending results and the last seven days for provider corrections."""
    latest = {s['prediction_id']: s for s in ledger.settlements()}
    now = utcnow()
    count = 0
    for prediction in ledger.predictions(league):
        match = prediction['fixture']
        start = parse_time(match['fixture']['date'])
        if not start or start > now:
            continue
        if prediction['id'] in latest and start < now - timedelta(days=7):
            continue
        result = api.get_api_football_fixture_details(int(match['fixture']['id']))
        if result:
            count += ledger.settle(result)
    return count


def collect(ledger, league):
    season = api.current_season(league)
    existing = {p['fixture']['fixture']['id'] for p in ledger.predictions(league)}
    count = 0
    for match in api.get_analysis_fixtures(league, season=season, next_games=10):
        fx = match.get('fixture') or {}
        start = parse_time(fx.get('date'))
        now = utcnow()
        if fx.get('source', 'API-Football') != 'API-Football' or fx.get('id') in existing or not start or not now < start < now + timedelta(hours=48) or fx.get('status', {}).get('short') != 'NS':
            continue
        teams = match['teams']
        home = api.get_api_football_team_statistics(league, int(teams['home']['id']), season=season)
        away = api.get_api_football_team_statistics(league, int(teams['away']['id']), season=season)
        if not home or not away:
            continue
        evidence = evidence_for(home, away, league, season)
        probs = calculate_current_probabilities(home, away) if evidence else None
        if probs:
            count += ledger.record(match, probs, evidence)
    return count
