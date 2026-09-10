"""Render every public page under a total provider outage."""
import unittest
from unittest.mock import patch
import requests
from streamlit.testing.v1 import AppTest
from pathlib import Path
from datetime import timedelta
from src import sports_data_api as api


class AppSmokeTests(unittest.TestCase):
    def test_all_seven_pages_under_outage(self):
        with patch('requests.Session.get', side_effect=requests.ConnectionError), patch('requests.get', side_effect=requests.ConnectionError):
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
            self.assertFalse(at.exception)
            pages = list(at.radio[0].options)
            self.assertEqual(len(pages), 7)
            for page in pages:
                at.radio[0].set_value(page).run()
                self.assertFalse(at.exception, f'Page failed: {page}')

    def test_analysis_with_evidence_and_no_database(self):
        now = api.now_local()
        match = {'fixture': {'id': 99, 'date': (now + timedelta(days=1)).isoformat(), 'status': {'short':'NS'}},
                 'league': {'id':71, 'name':'Test competition'}, 'teams': {'home':{'id':1,'name':'Test A'}, 'away':{'id':2,'name':'Test B'}}}
        stats = {'league': {'id':71,'season':api.current_season(71)}, 'fixtures':{'played':{'home':5,'away':5}},
                 'goals':{'for':{'average':{'home':'1.5','away':'1.2'}},'against':{'average':{'home':'1.0','away':'1.1'}}}}
        with patch('requests.Session.get', side_effect=requests.ConnectionError), patch.object(api, 'get_analysis_fixtures', return_value=[match]), patch.object(api, 'get_api_football_team_statistics', return_value=stats), patch.object(api, 'data_observed_at', return_value=now.isoformat()):
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
            at.radio[0].set_value('📈 Análise').run()
            self.assertFalse(at.exception)
            self.assertTrue(any('Estimativa não registrada' in info.value for info in at.info))
