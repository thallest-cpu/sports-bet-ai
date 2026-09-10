import time
import json
import asyncio
import threading
from typing import Dict, Any, List, Optional, Set

class InMemoryCachePubSub:
    """
    Sistema de Cache em Memória e Mensageria Pub/Sub no padrão Redis.
    Isola a API externa, fornecendo caching com TTL e distribuição fan-out
    para conexões WebSockets e Server-Sent Events (SSE).
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, Set[Any]] = {} # channel -> set of async queues
        self._lock = threading.RLock()
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 50

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Armazena um valor com tempo de expiração opcional (TTL)."""
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at
            }

    def get(self, key: str, default: Any = None) -> Any:
        """Recupera um valor se não estiver expirado."""
        with self._lock:
            item = self._cache.get(key)
            if not item:
                return default
            if item["expires_at"] and time.time() > item["expires_at"]:
                del self._cache[key]
                return default
            return item["value"]

    def delete(self, key: str):
        """Remove uma chave do cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def subscribe(self, channel: str, queue: asyncio.Queue):
        """Registra uma fila assíncrona (Queue) para receber mensagens de um canal."""
        with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = set()
            self._subscribers[channel].add(queue)

    def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """Remove a assinatura da fila."""
        with self._lock:
            if channel in self._subscribers and queue in self._subscribers[channel]:
                self._subscribers[channel].remove(queue)

    def publish(self, channel: str, message: Dict[str, Any]):
        """
        Publica uma mensagem no canal para todos os ouvintes conectados (Fan-out).
        Registra no histórico para novos clientes receberem o replay de eventos recentes.
        """
        with self._lock:
            if channel in ["events:realtime", "goals:alerts", "odds:updates"]:
                event_record = {
                    "channel": channel,
                    "timestamp": time.time(),
                    "data": message
                }
                self._event_history.append(event_record)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)

            queues = list(self._subscribers.get(channel, []))
            wildcard_queues = list(self._subscribers.get("*", []))

        all_queues = set(queues + wildcard_queues)
        payload = {"channel": channel, "data": message, "timestamp": time.time()}
        
        for q in all_queues:
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retorna os eventos mais recentes publicados."""
        with self._lock:
            return list(self._event_history[-limit:])

# Instância global compartilhada (Singleton)
GLOBAL_CACHE = InMemoryCachePubSub()
