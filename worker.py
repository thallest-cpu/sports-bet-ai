"""Run with python worker.py from an external scheduler, with environment secrets."""
from src.prediction_service import open_ledger, collect, reconcile
from src.sports_data_api import API_FOOTBALL_LEAGUES
from src.settings import secret


def main():
    ledger = open_ledger()
    if ledger is None:
        raise SystemExit('BETAI_DATABASE_URL ausente; nenhum histórico foi criado.')
    configured = secret('BETAI_MONITORED_LEAGUES', '71').split(',')
    leagues = [int(value) for value in configured]
    if any(league not in API_FOOTBALL_LEAGUES.values() for league in leagues):
        raise SystemExit('Competição não suportada')
    for league in leagues:
        settled = reconcile(ledger, league)
        recorded = collect(ledger, league)
        print(f'Competição {league}: {recorded} registros; {settled} apurações.')


if __name__ == '__main__':
    main()
