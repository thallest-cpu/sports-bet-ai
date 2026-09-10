import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.audit import Ledger, match_state, regulation_result
from src.quota import QuotaGuard
from src.current_model import calculate_current_probabilities
from src.settings import licensed_photo
from src import sports_data_api as api


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.url = 'sqlite:///' + str(Path(self.tmp.name) / 'audit.db')
        self.ledger = Ledger(self.url)
        self.now = datetime(2026, 9, 10, 15, tzinfo=timezone.utc)
        self.match = {'fixture': {'id': 123, 'date': (self.now + timedelta(hours=1)).isoformat(), 'status': {'short': 'NS'}},
                      'league': {'id': 71}, 'teams': {'home': {'name':'A'}, 'away': {'name':'B'}}}
        self.probs = {'home': 60, 'draw': 25, 'away': 15}
        self.evidence = {'observed_at': self.now.isoformat()}

    def tearDown(self):
        self.tmp.cleanup()

    def record(self):
        return self.ledger.record(self.match, self.probs, self.evidence, self.now)

    def test_persists_and_cannot_overwrite(self):
        self.assertTrue(self.record())
        self.probs = {'home': 20, 'draw': 30, 'away': 50}
        self.assertFalse(self.record())
        self.assertEqual(Ledger(self.url).predictions()[0]['probabilities']['home'], 60)

    def test_kickoff_and_live_rejected(self):
        self.assertFalse(self.ledger.record(self.match, self.probs, self.evidence, self.now + timedelta(hours=1)))
        self.match['fixture']['status']['short'] = 'LIVE'
        self.assertFalse(self.record())

    def test_future_and_stale_evidence_rejected(self):
        for delta in (timedelta(minutes=1), -timedelta(hours=7)):
            self.evidence['observed_at'] = (self.now + delta).isoformat()
            with self.assertRaises(ValueError): self.record()

    def test_namespace_separation(self):
        self.record()
        result = copy.deepcopy(self.match)
        result['fixture'].update(source='ESPN', status={'short': 'FT'})
        result['goals'] = {'home': 2, 'away': 0}
        self.assertEqual(self.ledger.settle(result, self.now + timedelta(hours=3)), 0)

    def test_settlement_idempotent_and_corrections_append_including_revert(self):
        self.record()
        result = copy.deepcopy(self.match)
        result['fixture']['status']['short'] = 'FT'
        result['goals'] = {'home': 2, 'away': 0}
        at = self.now + timedelta(hours=3)
        self.assertEqual(self.ledger.settle(result, at), 1)
        self.assertEqual(self.ledger.settle(result, at), 0)
        result['goals'] = {'home': 0, 'away': 2}
        self.assertEqual(self.ledger.settle(result, at + timedelta(minutes=1)), 1)
        result['goals'] = {'home': 2, 'away': 0}
        self.assertEqual(self.ledger.settle(result, at + timedelta(minutes=2)), 1)
        self.assertEqual([x['verdict'] for x in self.ledger.settlements()], ['Acerto', 'Erro', 'Acerto'])

    def test_extra_time_requires_regulation_score(self):
        self.match['fixture']['status']['short'] = 'PEN'
        self.match['goals'] = {'home': 5, 'away': 4}
        self.assertIsNone(regulation_result(self.match))
        self.match['score'] = {'fulltime': {'home': 1, 'away': 1}}
        self.assertEqual(regulation_result(self.match), 'draw')

    def test_unknown_score_not_zero(self):
        self.match['fixture']['status']['short'] = 'FT'
        self.match['goals'] = {'home': None, 'away': None}
        self.assertIsNone(regulation_result(self.match))

    def test_yesterday_does_not_imply_finished(self):
        self.assertIn('Expirado', match_state(self.match, self.now + timedelta(days=1)))
        self.match['fixture']['status']['short'] = 'PST'
        self.assertEqual(match_state(self.match, self.now + timedelta(days=1)), 'Adiado')

    def test_quota_shared_and_block_survives_new_instance(self):
        path = Path(self.tmp.name) / 'quota.db'
        one = QuotaGuard(path); two = QuotaGuard(path)
        self.assertTrue(one.reserve('key', 2)[0])
        self.assertTrue(two.reserve('key', 2)[0])
        self.assertFalse(one.reserve('key', 2)[0])
        one.block('key', 120, 'cota')
        self.assertEqual(QuotaGuard(path).reserve('key', 100), (False, 'cota'))


class DataSafetyTests(unittest.TestCase):
    def test_nonfinite_model_inputs_rejected(self):
        for value in ['nan', 'inf', '-1']:
            stats = {'goals': {'for': {'average': {'home': value, 'away':'1'}}, 'against': {'average': {'home':'1','away':'1'}}}}
            self.assertIsNone(calculate_current_probabilities(stats, stats))

    def test_photos_default_off_and_host_restricted(self):
        with patch('src.settings.secret', return_value=''):
            self.assertEqual(licensed_photo('https://media.api-sports.io/a.png','API-Football'), '')
        with patch('src.settings.secret', return_value='API-Football'):
            self.assertEqual(licensed_photo('https://evil.test/a.png','API-Football'), '')
            self.assertTrue(licensed_photo('https://media.api-sports.io/a.png','API-Football'))

    def test_espn_failed_roster_never_calls_api_with_espn_id(self):
        with patch.object(api, '_espn_squad', return_value=[]), patch.object(api, '_api_get') as request:
            self.assertEqual(api.get_api_football_squad(10, league_id=71, source_hint='ESPN'), [])
            request.assert_not_called()

    def test_local_day_filter(self):
        day = datetime(2026, 9, 9).date()
        matches = [{'fixture': {'date': d}} for d in ['2026-09-09T02:59:00Z','2026-09-09T03:00:00Z','2026-09-10T02:59:00Z','2026-09-10T03:00:00Z']]
        with patch.object(api, '_fetch_espn_fixtures', return_value=matches), patch.dict(api._PROVIDER_STATUS, {'espn': {'ok':True}}):
            selected, ok = api.fixtures_on_date(71, day)
        self.assertTrue(ok)
        self.assertEqual(selected, matches[1:3])

    def test_espn_pre_match_score_not_invented(self):
        match = api._format_espn_event({'id':'1'}, {}, {'type':{'state':'pre'}}, 'bra.1')
        self.assertEqual(match['goals'], {'home':None, 'away':None})

    def test_old_standings_rejected(self):
        with patch.object(api, '_espn_get', return_value={'season':{'year':2020}}):
            self.assertEqual(api._espn_standings(71), [])
