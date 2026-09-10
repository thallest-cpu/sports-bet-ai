import random
import time
from typing import Dict, Any, Optional

# Banco de dados em memória contendo a telemetria e o estado tático dos jogos
_TELEMETRY_STATE: Dict[str, Dict[str, Any]] = {}

def get_or_create_telemetry(match_id: str, home_team: str = "Flamengo", away_team: str = "Palmeiras",
                            home_score: int = 0, away_score: int = 0, clock: str = "38'") -> Dict[str, Any]:
    """Recupera ou inicializa a telemetria tática de um confronto específico."""
    global _TELEMETRY_STATE
    match_id = str(match_id)
    if match_id in _TELEMETRY_STATE:
        return _TELEMETRY_STATE[match_id]

    posse_casa = random.randint(48, 62)
    posse_fora = 100 - posse_casa
    chutes_gol_c = max(1, home_score + random.randint(1, 4))
    chutes_gol_f = max(0, away_score + random.randint(0, 3))
    
    state = {
        "matchId": match_id,
        "timeCasa": home_team,
        "timeVisitante": away_team,
        "placar": f"{home_score} x {away_score}",
        "tempo": clock,
        "stats": {
            "chutesGolCasa": chutes_gol_c,
            "chutesGolFora": chutes_gol_f,
            "chutesTotalCasa": chutes_gol_c + random.randint(2, 6),
            "chutesTotalFora": chutes_gol_f + random.randint(1, 5),
            "posseCasa": posse_casa,
            "posseFora": posse_fora,
            "escanteiosCasa": random.randint(2, 7),
            "escanteiosFora": random.randint(1, 5),
            "ataquesPerigososCasa": random.randint(20, 45),
            "ataquesPerigososFora": random.randint(15, 38),
            "cartoesAmarelosCasa": random.randint(0, 2),
            "cartoesAmarelosFora": random.randint(0, 3),
            "cartoesVermelhosCasa": 0,
            "cartoesVermelhosFora": 0,
            "xgCasa": round(0.4 + (home_score * 0.7) + (chutes_gol_c * 0.15), 2),
            "xgFora": round(0.2 + (away_score * 0.7) + (chutes_gol_f * 0.12), 2)
        },
        "odds": {
            "casa": 1.85,
            "empate": 3.30,
            "fora": 4.10,
            "variacaoCasa": "neutral",
            "variacaoEmpate": "neutral",
            "variacaoFora": "neutral"
        },
        "ultimoEvento": {
            "tipo": "SAFE_POSSESSION",
            "texto": f"Bola em jogo no meio-campo ({home_team})",
            "time": "casa",
            "posse": "casa",
            "bolaX": 48.0,
            "bolaY": 30.0,
            "direcaoAtaque": "direita",
            "intensidade": "media"
        },
        "timestamp": time.time()
    }
    _TELEMETRY_STATE[match_id] = state
    return state

def advance_match_telemetry(match_id: str, force_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Avança a simulação tática ou injeta um evento forçado, recalculando a posição
    da bola no campo (Canvas/SVG), o vetor de perigo e pequenas variações de odds.
    """
    global _TELEMETRY_STATE
    match_id = str(match_id)
    state = _TELEMETRY_STATE.get(match_id)
    if not state:
        state = get_or_create_telemetry(match_id)

    stats = state["stats"]
    odds = state["odds"]
    h_team = state["timeCasa"]
    a_team = state["timeVisitante"]

    if force_event:
        event_type = force_event.get("type", "SAFE_POSSESSION").upper()
        team_target = force_event.get("team", "casa").lower()
        is_home = (team_target == "casa")

        if event_type == "DANGEROUS_ATTACK":
            bola_x = random.uniform(74, 88) if is_home else random.uniform(12, 26)
            bola_y = random.uniform(18, 42)
            direcao = "direita" if is_home else "esquerda"
            team_name = h_team if is_home else a_team
            if is_home:
                stats["ataquesPerigososCasa"] += 1
            else:
                stats["ataquesPerigososFora"] += 1
            event = {
                "tipo": "DANGEROUS_ATTACK",
                "texto": f"⚡ ATAQUE PERIGOSO - {team_name}!",
                "time": team_target,
                "posse": team_target,
                "bolaX": round(bola_x, 1),
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": direcao,
                "intensidade": "perigo_maximo"
            }

        elif event_type in ["SHOT", "SHOT_ON_TARGET"]:
            bola_x = 94.0 if is_home else 6.0
            bola_y = random.uniform(24, 36)
            team_name = h_team if is_home else a_team
            if is_home:
                stats["chutesGolCasa"] += 1
                stats["chutesTotalCasa"] += 1
                stats["xgCasa"] = round(stats["xgCasa"] + 0.18, 2)
            else:
                stats["chutesGolFora"] += 1
                stats["chutesTotalFora"] += 1
                stats["xgFora"] = round(stats["xgFora"] + 0.18, 2)
            event = {
                "tipo": "SHOT_ON_TARGET",
                "texto": f"🎯 CHUTE A GOL DEFENDIDO! ({team_name})",
                "time": team_target,
                "posse": team_target,
                "bolaX": bola_x,
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": "direita" if is_home else "esquerda",
                "intensidade": "alta"
            }

        elif event_type == "CORNER":
            bola_x = 96.0 if is_home else 4.0
            bola_y = 4.0 if random.random() > 0.5 else 56.0
            team_name = h_team if is_home else a_team
            if is_home:
                stats["escanteiosCasa"] += 1
            else:
                stats["escanteiosFora"] += 1
            event = {
                "tipo": "CORNER",
                "texto": f"🚩 ESCANTEIO A FAVOR DO {team_name.upper()}",
                "time": team_target,
                "posse": team_target,
                "bolaX": bola_x,
                "bolaY": bola_y,
                "direcaoAtaque": "direita" if is_home else "esquerda",
                "intensidade": "media"
            }

        elif event_type == "FREE_KICK":
            bola_x = random.uniform(68, 80) if is_home else random.uniform(20, 32)
            bola_y = random.uniform(16, 44)
            team_name = h_team if is_home else a_team
            event = {
                "tipo": "FREE_KICK",
                "texto": f"⚠️ FALTA PERIGOSA PRÓXIMA À ÁREA ({team_name})",
                "time": team_target,
                "posse": team_target,
                "bolaX": round(bola_x, 1),
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": "direita" if is_home else "esquerda",
                "intensidade": "alta"
            }

        elif event_type == "GOAL":
            bola_x = 98.0 if is_home else 2.0
            bola_y = 30.0
            team_name = h_team if is_home else a_team
            scorer = force_event.get("scorer", "Artilheiro")
            parts = state["placar"].split("x")
            h_s = int(parts[0].strip()) if len(parts) == 2 else 0
            a_s = int(parts[1].strip()) if len(parts) == 2 else 0
            if is_home:
                h_s += 1
                stats["chutesGolCasa"] += 1
                stats["xgCasa"] = round(stats["xgCasa"] + 0.75, 2)
                odds["casa"] = round(max(1.10, odds["casa"] * 0.7), 2)
                odds["fora"] = round(odds["fora"] * 1.5, 2)
            else:
                a_s += 1
                stats["chutesGolFora"] += 1
                stats["xgFora"] = round(stats["xgFora"] + 0.75, 2)
                odds["fora"] = round(max(1.10, odds["fora"] * 0.7), 2)
                odds["casa"] = round(odds["casa"] * 1.5, 2)
            state["placar"] = f"{h_s} x {a_s}"

            event = {
                "tipo": "GOAL",
                "texto": f"⚽ GOOOOOOOL DO {team_name.upper()}! ({scorer})",
                "time": team_target,
                "posse": team_target,
                "bolaX": bola_x,
                "bolaY": bola_y,
                "direcaoAtaque": "direita" if is_home else "esquerda",
                "intensidade": "gol"
            }
        else:
            event = {
                "tipo": "SAFE_POSSESSION",
                "texto": f"Bola em jogo no meio-campo ({h_team})",
                "time": "casa",
                "posse": "casa",
                "bolaX": 50.0,
                "bolaY": 30.0,
                "direcaoAtaque": "direita",
                "intensidade": "baixa"
            }
    else:
        # Avanço autônomo natural
        r = random.random()
        is_home = (r < 0.56) # Leve viés de ataque para o mandante
        direcao = "direita" if is_home else "esquerda"
        team_name = h_team if is_home else a_team
        team_target = "casa" if is_home else "fora"

        if r < 0.28:
            # Ataque perigoso
            bola_x = random.uniform(72, 86) if is_home else random.uniform(14, 28)
            bola_y = random.uniform(18, 42)
            if is_home:
                stats["ataquesPerigososCasa"] += 1
            else:
                stats["ataquesPerigososFora"] += 1
            event = {
                "tipo": "DANGEROUS_ATTACK",
                "texto": f"⚡ Ataque Perigoso - {team_name}",
                "time": team_target,
                "posse": team_target,
                "bolaX": round(bola_x, 1),
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": direcao,
                "intensidade": "perigo_maximo"
            }
        elif r < 0.38:
            # Escanteio
            bola_x = 96.0 if is_home else 4.0
            bola_y = 5.0 if random.random() > 0.5 else 55.0
            if is_home:
                stats["escanteiosCasa"] += 1
            else:
                stats["escanteiosFora"] += 1
            event = {
                "tipo": "CORNER",
                "texto": f"🚩 Escanteio - {team_name}",
                "time": team_target,
                "posse": team_target,
                "bolaX": bola_x,
                "bolaY": bola_y,
                "direcaoAtaque": direcao,
                "intensidade": "media"
            }
        elif r < 0.44:
            # Chute a gol
            bola_x = 92.0 if is_home else 8.0
            bola_y = random.uniform(22, 38)
            if is_home:
                stats["chutesGolCasa"] += 1
            else:
                stats["chutesGolFora"] += 1
            event = {
                "tipo": "SHOT_ON_TARGET",
                "texto": f"🎯 Finalização no Alvo ({team_name})",
                "time": team_target,
                "posse": team_target,
                "bolaX": round(bola_x, 1),
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": direcao,
                "intensidade": "alta"
            }
        elif r < 0.52:
            # Falta
            bola_x = random.uniform(62, 78) if is_home else random.uniform(22, 38)
            bola_y = random.uniform(14, 46)
            event = {
                "tipo": "FREE_KICK",
                "texto": f"⚠️ Falta marcada para o {team_name}",
                "time": team_target,
                "posse": team_target,
                "bolaX": round(bola_x, 1),
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": direcao,
                "intensidade": "media"
            }
        else:
            # Posse no meio
            bola_x = random.uniform(38, 62)
            bola_y = random.uniform(12, 48)
            event = {
                "tipo": "SAFE_POSSESSION",
                "texto": f"Posse de bola no meio-campo ({team_name})",
                "time": team_target,
                "posse": team_target,
                "bolaX": round(bola_x, 1),
                "bolaY": round(bola_y, 1),
                "direcaoAtaque": direcao,
                "intensidade": "baixa"
            }

    # Pequena variação nas odds em tempo real
    old_odd_c = odds["casa"]
    delta_c = round((random.random() * 0.04 - 0.02), 2)
    new_odd_c = max(1.05, round(old_odd_c + delta_c, 2))
    odds["variacaoCasa"] = "up" if new_odd_c > old_odd_c else ("down" if new_odd_c < old_odd_c else "neutral")
    odds["casa"] = new_odd_c

    state["ultimoEvento"] = event
    state["timestamp"] = time.time()
    return state
