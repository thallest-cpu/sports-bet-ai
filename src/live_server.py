import time
import threading
import json
import os
import datetime
from typing import Dict, Any, List
from src.live_tracker import fetch_all_major_leagues
from src.whatsapp_notifier import format_goal_whatsapp_message

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STATE_FILE = os.path.join(STATE_DIR, "live_state.json")

# Estrutura em memória
_GLOBAL_LIVE_STATE = {
    "last_update": "",
    "pulse_counter": 0,
    "matches": [],
    "recent_goals": []
}

_SERVER_THREAD = None
_SERVER_RUNNING = False

def update_live_cycle():
    """Executa um ciclo completo de sincronização a cada 3 segundos."""
    global _GLOBAL_LIVE_STATE
    os.makedirs(STATE_DIR, exist_ok=True)
    
    # 1. Carregar partidas mais recentes
    try:
        matches = fetch_all_major_leagues()
    except Exception as e:
        matches = _GLOBAL_LIVE_STATE.get("matches", [])

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    _GLOBAL_LIVE_STATE["last_update"] = now_str
    _GLOBAL_LIVE_STATE["pulse_counter"] = (_GLOBAL_LIVE_STATE.get("pulse_counter", 0) + 1) % 100000
    
    # Se houver jogos, manter a lista
    if matches:
        _GLOBAL_LIVE_STATE["matches"] = matches

    # Salvar em arquivo para persistência entre instâncias
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(_GLOBAL_LIVE_STATE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def live_daemon_worker():
    """Loop contínuo de 3 segundos do servidor ao vivo."""
    global _SERVER_RUNNING
    _SERVER_RUNNING = True
    print("[SERVIDOR AO VIVO] Iniciado com pulso de 3 segundos...")
    
    while _SERVER_RUNNING:
        try:
            update_live_cycle()
        except Exception as err:
            print(f"[SERVIDOR AO VIVO] Erro no ciclo: {err}")
        time.sleep(3)

def start_live_server_if_needed():
    """Garante que o servidor ao vivo em segundo plano esteja ativo."""
    global _SERVER_THREAD, _SERVER_RUNNING
    if _SERVER_THREAD is None or not _SERVER_THREAD.is_alive():
        _SERVER_THREAD = threading.Thread(target=live_daemon_worker, daemon=True)
        _SERVER_THREAD.start()

def get_current_live_state() -> Dict[str, Any]:
    """Retorna o estado do servidor ao vivo em tempo real."""
    start_live_server_if_needed()
    
    # Tentar ler do arquivo se a memória local estiver vazia
    if not _GLOBAL_LIVE_STATE.get("matches"):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # Se ainda vazio, executa um ciclo imediato
        update_live_cycle()
        
    return _GLOBAL_LIVE_STATE
