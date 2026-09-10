from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.current_model import calculate_current_probabilities, calculate_ev, extract_match_winner_odds
import src.sports_data_api as sports_api
from src.sports_data_api import current_season, _format_espn_event, _position_name


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.home = {
            "goals": {
                "for": {"average": {"home": "1.80"}},
                "against": {"average": {"home": "0.90"}},
            }
        }
        self.away = {
            "goals": {
                "for": {"average": {"away": "1.20"}},
                "against": {"average": {"away": "1.40"}},
            }
        }

    def test_probabilities_sum_to_100(self):
        p = calculate_current_probabilities(self.home, self.away)
        self.assertIsNotNone(p)
        self.assertAlmostEqual(p["home"] + p["draw"] + p["away"], 100.0, delta=0.2)
        self.assertTrue(0 <= p["over25"] <= 100)
        self.assertTrue(0 <= p["btts"] <= 100)

    def test_missing_stats_do_not_invent(self):
        self.assertIsNone(calculate_current_probabilities({}, self.away))

    def test_ev(self):
        self.assertEqual(calculate_ev(50, 2.10), 5.0)

    def test_odds_filter(self):
        payload = [{"bookmakers": [{"name": "X", "bets": [{"name": "Match Winner", "values": [
            {"value": "Home", "odd": "2.10"}, {"value": "Draw", "odd": "3.20"}
        ]}]}]}]
        rows = extract_match_winner_odds(payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["bookmaker"], "X")


class DataNormalizationTests(unittest.TestCase):
    def test_season_rules(self):
        tz = ZoneInfo("America/Sao_Paulo")
        self.assertEqual(current_season(71, datetime(2026, 2, 1, tzinfo=tz)), 2026)
        self.assertEqual(current_season(39, datetime(2026, 2, 1, tzinfo=tz)), 2025)
        self.assertEqual(current_season(39, datetime(2026, 9, 1, tzinfo=tz)), 2026)

    def test_positions(self):
        self.assertEqual(_position_name("Goalkeeper"), "Goalkeeper")
        self.assertEqual(_position_name("Centre Back"), "Defender")
        self.assertEqual(_position_name("Midfielder"), "Midfielder")
        self.assertEqual(_position_name("Forward"), "Attacker")


    def test_live_empty_espn_does_not_spend_api_quota(self):
        old_fetch = sports_api._fetch_espn_fixtures
        old_live = sports_api.get_api_football_live_fixtures
        old_status = dict(sports_api._PROVIDER_STATUS["espn"])
        called = {"api": 0}
        try:
            def fake_fetch(*args, **kwargs):
                sports_api._PROVIDER_STATUS["espn"] = {"ok": True, "message": "ok", "at": None}
                return []
            def fake_api(*args, **kwargs):
                called["api"] += 1
                return [{"should": "not happen"}]
            sports_api._fetch_espn_fixtures = fake_fetch
            sports_api.get_api_football_live_fixtures = fake_api
            self.assertEqual(sports_api.get_realtime_live_fixtures(), [])
            self.assertEqual(called["api"], 0)
        finally:
            sports_api._fetch_espn_fixtures = old_fetch
            sports_api.get_api_football_live_fixtures = old_live
            sports_api._PROVIDER_STATUS["espn"] = old_status

    def test_espn_event_namespace(self):
        event = {"id": "401234", "date": "2026-09-10T20:00Z"}
        comp = {
            "competitors": [
                {"homeAway": "home", "score": "1", "team": {"id": "10", "displayName": "Casa"}},
                {"homeAway": "away", "score": "0", "team": {"id": "20", "displayName": "Fora"}},
            ]
        }
        status = {"type": {"state": "in", "description": "In Progress"}, "displayClock": "67'"}
        fx = _format_espn_event(event, comp, status, "bra.1")
        self.assertEqual(fx["fixture"]["source"], "ESPN")
        self.assertEqual(fx["fixture"]["espn_event_id"], "401234")
        self.assertEqual(fx["goals"]["home"], 1)
        self.assertEqual(fx["fixture"]["status"]["short"], "LIVE")


if __name__ == "__main__":
    unittest.main()
