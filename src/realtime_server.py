import time
import json
import asyncio
import threading
from typing import Dict, Any

import os
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse, FileResponse
from starlette.routing import Route, WebSocketRoute
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect
import uvicorn

from src.realtime_cache import GLOBAL_CACHE
from src.livescore_engine import GLOBAL_ENGINE, start_engine_if_needed

REALTIME_PORT = 8002
_SERVER_THREAD = None
_SERVER_STARTED = False

# -------------------------------------------------------------
# HANDLERS HTTP E SSE
# -------------------------------------------------------------
async def health_check(request):
    """Endpoint de verificação de integridade do servidor de tempo real."""
    return JSONResponse({
        "status": "healthy",
        "service": "BetAI Quant Pro Realtime Engine",
        "port": REALTIME_PORT,
        "timestamp": time.time()
    })

async def get_live_state_endpoint(request):
    """Retorna o estado consolidado das partidas em tempo real."""
    state = GLOBAL_CACHE.get("matches:live") or {}
    return JSONResponse(state)

async def webhook_sports_event(request):
    """
    Receptor oficial de Webhooks disparados por provedores de dados esportivos.
    Ex: Sportradar, Opta, API-Football ou ferramentas internas de mensageria.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    result = GLOBAL_ENGINE.process_external_webhook(payload)
    return JSONResponse({"status": "received", "result": result})

async def simulate_event_endpoint(request):
    """
    Endpoint utilitário para simulação imediata de eventos (Gols e Variação de Odds)
    para comprovação visual instantânea sem recarregar a tela.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    sim_type = body.get("type", "GOAL").upper()
    if sim_type == "GOAL":
        payload = {
            "event_type": "GOAL",
            "home_team": body.get("home_team", "Flamengo"),
            "away_team": body.get("away_team", "Palmeiras"),
            "team_scored": body.get("team_scored", "Flamengo"),
            "scorer": body.get("scorer", "Pedro"),
            "old_score": body.get("old_score", "0 x 0"),
            "new_score": body.get("new_score", "1 x 0"),
            "minute": body.get("minute", "38'")
        }
    else:
        payload = {
            "event_type": "ODD_CHANGE",
            "home_team": body.get("home_team", "Flamengo"),
            "away_team": body.get("away_team", "Palmeiras"),
            "old_odd": body.get("old_odd", 2.10),
            "new_odd": body.get("new_odd", 1.80)
        }

    res = GLOBAL_ENGINE.process_external_webhook(payload)
    return JSONResponse({"status": "simulated", "data": res})

async def sse_live_stream(request):
    """
    Server-Sent Events (SSE) Endpoint (`text/event-stream`).
    Fornece fluxo unidirecional contínuo de eventos para navegadores via HTTP padrão.
    """
    async def event_generator():
        client_queue = asyncio.Queue()
        GLOBAL_CACHE.subscribe("*", client_queue)

        try:
            # 1. Enviar Snapshot inicial
            snapshot = GLOBAL_CACHE.get("matches:live") or {}
            init_payload = {
                "type": "SNAPSHOT",
                "matches": snapshot.get("matches", []),
                "recent_events": GLOBAL_CACHE.get_recent_events(10),
                "server_time": time.time()
            }
            yield f"data: {json.dumps(init_payload)}\n\n"

            # 2. Transmitir eventos conforme chegam
            while True:
                try:
                    # Timeout para envio de ping/keep-alive a cada 10s
                    item = await asyncio.wait_for(client_queue.get(), timeout=10.0)
                    yield f"data: {json.dumps(item)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            GLOBAL_CACHE.unsubscribe("*", client_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

from src.match_telemetry import get_or_create_telemetry, advance_match_telemetry

async def get_telemetry_endpoint(request):
    """Retorna o estado de telemetria espacial e estatísticas de um jogo específico."""
    match_id = request.path_params.get("match_id", "123")
    snapshot = GLOBAL_CACHE.get("matches:live") or {}
    matches = snapshot.get("matches", [])
    found = next((m for m in matches if str(m.get("id")) == str(match_id)), None)
    if found:
        t = get_or_create_telemetry(
            match_id, found.get("home_team", "Flamengo"), found.get("away_team", "Palmeiras"),
            int(found.get("home_score", 0) or 0), int(found.get("away_score", 0) or 0),
            found.get("status_label", "Ao Vivo")
        )
    else:
        t = get_or_create_telemetry(match_id)
    return JSONResponse(t)

async def simulate_pitch_event_endpoint(request):
    """Injeta um evento tático instantâneo (Ataque Perigoso, Chute, Escanteio, Gol) na telemetria do jogo."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    match_id = str(body.get("matchId", "123"))
    event_type = body.get("eventType", "DANGEROUS_ATTACK")
    team = body.get("team", "casa")
    scorer = body.get("scorer", "Artilheiro")

    telemetry = advance_match_telemetry(match_id, force_event={"type": event_type, "team": team, "scorer": scorer})
    GLOBAL_CACHE.publish(f"match_telemetry:{match_id}", telemetry)
    return JSONResponse({"status": "event_triggered", "telemetry": telemetry})

# -------------------------------------------------------------
# WEBSOCKET ENDPOINT (/ws/live) COM SUPORTE A SALAS DE JOGOS
# -------------------------------------------------------------
async def websocket_live_endpoint(websocket: WebSocket):
    """
    Canal de comunicação bidirecional de latência ultrabaixa (<5ms).
    Suporta eventos globais e salas de partidas específicas (join_match / leave_match)
    com telemetria a cada 2.5 segundos para o renderizador de campo (Canvas/SVG).
    """
    await websocket.accept()
    client_queue = asyncio.Queue()
    GLOBAL_CACHE.subscribe("*", client_queue)
    joined_matches = set()

    try:
        # Enviar Snapshot inicial completo
        snapshot = GLOBAL_CACHE.get("matches:live") or {}
        init_payload = {
            "type": "SNAPSHOT",
            "matches": snapshot.get("matches", []),
            "recent_events": GLOBAL_CACHE.get_recent_events(10),
            "timestamp": time.time(),
            "pulse": snapshot.get("pulse", 0)
        }
        await websocket.send_text(json.dumps(init_payload))

        # 1. Recepção de comandos do cliente
        async def client_receiver():
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        msg = json.loads(data)
                        action = msg.get("action")
                        if action == "ping":
                            await websocket.send_text(json.dumps({"type": "PONG", "timestamp": time.time()}))
                        elif action == "join_match":
                            m_id = str(msg.get("matchId") or "123")
                            joined_matches.add(m_id)
                            cached = GLOBAL_CACHE.get("matches:live") or {}
                            m_found = next((m for m in cached.get("matches", []) if str(m.get("id")) == m_id), None)
                            if m_found:
                                t = get_or_create_telemetry(
                                    m_id, m_found.get("home_team", "Flamengo"), m_found.get("away_team", "Palmeiras"),
                                    int(m_found.get("home_score", 0) or 0), int(m_found.get("away_score", 0) or 0),
                                    m_found.get("status_label", "Ao Vivo")
                                )
                            else:
                                t = get_or_create_telemetry(m_id)
                            await websocket.send_text(json.dumps({
                                "type": "match_update",
                                "matchId": m_id,
                                "data": t
                            }))
                        elif action == "leave_match":
                            m_id = str(msg.get("matchId") or "")
                            if m_id in joined_matches:
                                joined_matches.remove(m_id)
                        elif action == "simulate_pitch_event":
                            m_id = str(msg.get("matchId") or "123")
                            force_evt = msg.get("event")
                            t = advance_match_telemetry(m_id, force_event=force_evt)
                            await websocket.send_text(json.dumps({
                                "type": "match_update",
                                "matchId": m_id,
                                "data": t
                            }))
                    except Exception:
                        pass
            except WebSocketDisconnect:
                pass
            except Exception:
                pass

        # 2. Transmissor de eventos globais
        async def server_sender():
            while True:
                item = await client_queue.get()
                await websocket.send_text(json.dumps(item))

        # 3. Ticker contínuo de telemetria tática dos jogos ativos
        async def telemetry_ticker():
            while True:
                await asyncio.sleep(2.5)
                for m_id in list(joined_matches):
                    try:
                        t = advance_match_telemetry(m_id)
                        await websocket.send_text(json.dumps({
                            "type": "match_update",
                            "matchId": m_id,
                            "data": t
                        }))
                    except Exception:
                        pass

        receiver_task = asyncio.create_task(client_receiver())
        sender_task = asyncio.create_task(server_sender())
        ticker_task = asyncio.create_task(telemetry_ticker())

        done, pending = await asyncio.wait(
            [receiver_task, sender_task, ticker_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        GLOBAL_CACHE.unsubscribe("*", client_queue)

# -------------------------------------------------------------
async def download_zip_endpoint(request):
    """Serve o arquivo ZIP completo do projeto para download direto no navegador."""
    zip_path = os.path.join(os.path.dirname(__file__), "..", "sports-bet-ai-completo.zip")
    zip_path = os.path.abspath(zip_path)
    if os.path.exists(zip_path):
        return FileResponse(zip_path, media_type="application/zip", filename="sports-bet-ai-completo.zip")
    return JSONResponse({"error": "Arquivo não encontrado"}, status_code=404)

# -------------------------------------------------------------
# ROTAS E MIDDLEWARE
# -------------------------------------------------------------
routes = [
    Route("/api/health", health_check, methods=["GET"]),
    Route("/api/live/state", get_live_state_endpoint, methods=["GET"]),
    Route("/api/telemetry/{match_id}", get_telemetry_endpoint, methods=["GET"]),
    Route("/api/webhook/sports-event", webhook_sports_event, methods=["POST"]),
    Route("/api/simulate/event", simulate_event_endpoint, methods=["POST"]),
    Route("/api/simulate/pitch-event", simulate_pitch_event_endpoint, methods=["POST"]),
    Route("/api/download/zip", download_zip_endpoint, methods=["GET"]),
    Route("/download/zip", download_zip_endpoint, methods=["GET"]),
    Route("/sse/live", sse_live_stream, methods=["GET"]),
    WebSocketRoute("/ws/live", websocket_live_endpoint),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    )
]

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    start_engine_if_needed()
    yield

app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)

# -------------------------------------------------------------
# INICIALIZAÇÃO DO SERVIDOR EM BACKGROUND DAEMON
# -------------------------------------------------------------
def _run_uvicorn():
    start_engine_if_needed()
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=REALTIME_PORT,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

import socket

def is_port_in_use(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False

def start_realtime_server_if_needed():
    """Garante que o servidor WebSockets/SSE esteja ativo na porta 8002."""
    global _SERVER_THREAD, _SERVER_STARTED
    if _SERVER_STARTED and _SERVER_THREAD is not None and _SERVER_THREAD.is_alive():
        return
    if is_port_in_use(REALTIME_PORT):
        _SERVER_STARTED = True
        return
    _SERVER_STARTED = True
    _SERVER_THREAD = threading.Thread(target=_run_uvicorn, daemon=True)
    _SERVER_THREAD.start()
    print(f"[REALTIME SERVER] Servidor WebSockets/SSE iniciado na porta {REALTIME_PORT}")
