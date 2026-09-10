import time
import threading
import datetime
from typing import Dict, Any, List, Optional
from src.realtime_cache import GLOBAL_CACHE
from src.live_tracker import fetch_all_major_leagues
from src.whatsapp_notifier import format_goal_whatsapp_message
from src.telegram_notifier import format_telegram_goal_message

class LiveScoreEngine:
    """
    Motor de Monitoramento de Alta Frequência (3s a 5s) e Ingestão de Webhooks.
    Processa deltas (gols, variações de odds, cartões) e alimenta o Cache Pub/Sub
    para distribuição instantânea aos clientes WebSockets/SSE.
    """
    def __init__(self, poll_interval: float = 3.5):
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._previous_matches: Dict[str, Dict[str, Any]] = {}
        self._pulse_count = 0

    def start(self):
        """Inicia o daemon de monitoramento contínuo em segundo plano."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[LIVESCORE ENGINE] Motor ativo - Frequencia: {self.poll_interval}s")

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            try:
                self.sync_cycle()
            except Exception as e:
                print(f"[LIVESCORE ENGINE] Erro no ciclo de sincronização: {e}")
            time.sleep(self.poll_interval)

    def sync_cycle(self):
        """Executa um ciclo completo de checagem contra a API esportiva."""
        self._pulse_count += 1
        matches = fetch_all_major_leagues()
        
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        timestamp_now = time.time()

        # Atualizar cache de partidas
        current_map: Dict[str, Dict[str, Any]] = {}
        
        for m in matches:
            m_id = str(m.get("id", f"{m['home_team']}_vs_{m['away_team']}"))
            current_map[m_id] = m

            prev = self._previous_matches.get(m_id)
            if prev:
                # 1. Checagem de Gols
                prev_h_score = int(prev.get("home_score", 0) or 0)
                curr_h_score = int(m.get("home_score", 0) or 0)
                prev_a_score = int(prev.get("away_score", 0) or 0)
                curr_a_score = int(m.get("away_score", 0) or 0)

                if curr_h_score > prev_h_score:
                    scorer = m.get("home_scorer", {}).get("nome", m["home_team"])
                    self._dispatch_goal_event(
                        m, team_scored=m["home_team"], scorer=scorer,
                        old_score=f"{prev_h_score} x {prev_a_score}",
                        new_score=f"{curr_h_score} x {curr_a_score}"
                    )

                if curr_a_score > prev_a_score:
                    scorer = m.get("away_scorer", {}).get("nome", m["away_team"])
                    self._dispatch_goal_event(
                        m, team_scored=m["away_team"], scorer=scorer,
                        old_score=f"{prev_h_score} x {prev_a_score}",
                        new_score=f"{curr_h_score} x {curr_a_score}"
                    )

                # 2. Checagem de Oscilação de Odds
                prev_odd_h = float(prev.get("odd_h", 2.0))
                curr_odd_h = float(m.get("odd_h", 2.0))
                if abs(curr_odd_h - prev_odd_h) >= 0.04:
                    self._dispatch_odd_event(m, "home", prev_odd_h, curr_odd_h)

        self._previous_matches = current_map

        # Publicar estado consolidado no cache Pub/Sub
        state_payload = {
            "pulse": self._pulse_count,
            "last_update": now_str,
            "timestamp": timestamp_now,
            "total_matches": len(matches),
            "matches": matches
        }
        GLOBAL_CACHE.set("matches:live", state_payload, ttl_seconds=15)
        GLOBAL_CACHE.publish("matches:live", state_payload)

    def _dispatch_goal_event(self, match: Dict[str, Any], team_scored: str, scorer: str, old_score: str, new_score: str):
        """Dispara evento de gol via Pub/Sub para WebSockets e SSE."""
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        event = {
            "type": "GOAL",
            "match_id": match.get("id"),
            "league": match.get("league"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "team_scored": team_scored,
            "scorer": scorer,
            "old_score": old_score,
            "new_score": new_score,
            "minute": match.get("status_label", "Ao Vivo"),
            "time_str": now_str,
            "whatsapp_text": format_goal_whatsapp_message(
                match.get("home_team", ""), match.get("away_team", ""),
                team_scored, scorer, "Gol", new_score
            ),
            "telegram_text": format_telegram_goal_message(
                match.get("home_team", ""), match.get("away_team", ""),
                team_scored, scorer, new_score, match.get("league", "")
            )
        }
        print(f"[GOL DETECTADO] {team_scored}! ({scorer}) Novo Placar: {new_score}")
        GLOBAL_CACHE.publish("events:realtime", event)
        GLOBAL_CACHE.publish("goals:alerts", event)

    def _dispatch_odd_event(self, match: Dict[str, Any], target: str, old_val: float, new_val: float):
        """Dispara evento de oscilação de cotação via Pub/Sub."""
        direction = "up" if new_val > old_val else "down"
        event = {
            "type": "ODD_CHANGE",
            "match_id": match.get("id"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
            "market": f"Vitória {match['home_team']}" if target == "home" else "Mercado",
            "target": target,
            "old_odd": old_val,
            "new_odd": new_val,
            "direction": direction,
            "time_str": datetime.datetime.now().strftime("%H:%M:%S")
        }
        GLOBAL_CACHE.publish("events:realtime", event)
        GLOBAL_CACHE.publish("odds:updates", event)

    def process_external_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa notificação de Webhook recebida de provedores externos de dados esportivos.
        Ex: Notificações HTTP da Sportradar, Opta, API-Football ou simuladores de evento.
        """
        event_type = payload.get("event_type", "GENERIC_EVENT").upper()
        now_str = datetime.datetime.now().strftime("%H:%M:%S")

        if event_type == "GOAL":
            event = {
                "type": "GOAL",
                "match_id": payload.get("match_id", "live-webhook-1"),
                "league": payload.get("league", "Brasileirão Série A"),
                "home_team": payload.get("home_team", "Flamengo"),
                "away_team": payload.get("away_team", "Palmeiras"),
                "team_scored": payload.get("team_scored", payload.get("home_team", "Flamengo")),
                "scorer": payload.get("scorer", "Pedro"),
                "old_score": payload.get("old_score", "0 x 0"),
                "new_score": payload.get("new_score", "1 x 0"),
                "minute": payload.get("minute", "34'"),
                "time_str": now_str,
                "source": "WEBHOOK_EXTERNAL_API"
            }
            # Atualizar também o placar da partida no cache de partidas
            cached_matches = GLOBAL_CACHE.get("matches:live")
            if cached_matches and "matches" in cached_matches:
                for m in cached_matches["matches"]:
                    if m.get("home_team") == event["home_team"] and m.get("away_team") == event["away_team"]:
                        parts = event["new_score"].split("x")
                        if len(parts) == 2:
                            m["home_score"] = parts[0].strip()
                            m["away_score"] = parts[1].strip()
                GLOBAL_CACHE.set("matches:live", cached_matches, ttl_seconds=15)
                GLOBAL_CACHE.publish("matches:live", cached_matches)

            GLOBAL_CACHE.publish("events:realtime", event)
            GLOBAL_CACHE.publish("goals:alerts", event)
            return {"status": "success", "event_dispatched": event}

        elif event_type == "ODD_CHANGE":
            event = {
                "type": "ODD_CHANGE",
                "match_id": payload.get("match_id", "live-webhook-1"),
                "home_team": payload.get("home_team", "Flamengo"),
                "away_team": payload.get("away_team", "Palmeiras"),
                "target": payload.get("target", "home"),
                "old_odd": float(payload.get("old_odd", 2.10)),
                "new_odd": float(payload.get("new_odd", 1.85)),
                "direction": "down" if float(payload.get("new_odd", 1.85)) < float(payload.get("old_odd", 2.10)) else "up",
                "time_str": now_str,
                "source": "WEBHOOK_EXTERNAL_API"
            }
            GLOBAL_CACHE.publish("events:realtime", event)
            GLOBAL_CACHE.publish("odds:updates", event)
            return {"status": "success", "event_dispatched": event}

        else:
            event = {
                "type": event_type,
                "payload": payload,
                "time_str": now_str,
                "source": "WEBHOOK_EXTERNAL_API"
            }
            GLOBAL_CACHE.publish("events:realtime", event)
            return {"status": "success", "event_dispatched": event}

# Instância global do motor
GLOBAL_ENGINE = LiveScoreEngine(poll_interval=3.5)

def start_engine_if_needed():
    """Garante que o motor de monitoramento esteja ativo."""
    GLOBAL_ENGINE.start()
