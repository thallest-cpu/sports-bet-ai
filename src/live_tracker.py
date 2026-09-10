import requests
import datetime
import traceback
from typing import List, Dict, Any
from src.team_intelligence import get_club_squad
from src.sports_data_api import get_api_football_live_fixtures

MAJOR_LEAGUES = {
    "Brasileirão Série A": "bra.1",
    "Premier League (Inglaterra)": "eng.1",
    "Champions League": "uefa.champions",
    "La Liga (Espanha)": "esp.1",
    "Serie A (Itália)": "ita.1",
    "Bundesliga (Alemanha)": "ger.1",
    "Ligue 1 (França)": "fra.1",
    "Copa Libertadores": "conmebol.libertadores",
    "Copa Sul-Americana": "conmebol.sudamericana",
}

def american_to_decimal(odd_val) -> float:
    """Converte odd americana (ex: +150, -170) para odd decimal (ex: 2.50, 1.59)."""
    try:
        if isinstance(odd_val, str):
            odd_val = odd_val.replace('+', '').strip()
        val = float(odd_val)
        if val == 0:
            return 2.0
        if val > 0:
            return round((val / 100.0) + 1.0, 2)
        else:
            return round((100.0 / abs(val)) + 1.0, 2)
    except Exception:
        return 2.0

def fetch_api_football_live_matches() -> List[Dict[str, Any]]:
    """Busca partidas em andamento via API-Football com latência em tempo real."""
    live_fixtures = get_api_football_live_fixtures()
    results = []
    for fx in live_fixtures:
        try:
            teams = fx.get("teams", {})
            goals = fx.get("goals", {})
            status = fx.get("fixture", {}).get("status", {})
            h_name = teams.get("home", {}).get("name", "Mandante")
            a_name = teams.get("away", {}).get("name", "Visitante")
            elapsed = status.get("elapsed", 0) or 0
            
            h_sq = get_club_squad(h_name)
            a_sq = get_club_squad(a_name)
            
            results.append({
                "id": f"apifb_{fx.get('fixture', {}).get('id')}",
                "league": fx.get("league", {}).get("name", "Ao Vivo Global"),
                "home_team": h_name,
                "away_team": a_name,
                "home_id": str(teams.get("home", {}).get("id", "")),
                "away_id": str(teams.get("away", {}).get("id", "")),
                "home_logo": teams.get("home", {}).get("logo", ""),
                "away_logo": teams.get("away", {}).get("logo", ""),
                "home_score": str(goals.get("home") if goals.get("home") is not None else 0),
                "away_score": str(goals.get("away") if goals.get("away") is not None else 0),
                "home_form": "",
                "away_form": "",
                "home_squad": h_sq,
                "away_squad": a_sq,
                "home_star": h_sq.get("craque", {}),
                "away_star": a_sq.get("craque", {}),
                "home_scorer": h_sq.get("artilheiro", {}),
                "away_scorer": a_sq.get("artilheiro", {}),
                "raw_date": fx.get("fixture", {}).get("date", ""),
                "status_state": "in",
                "status_desc": f"Ao Vivo ({elapsed}')",
                "status_label": f"🔴 AO VIVO ({elapsed}')",
                "badge_type": "live",
                "clock": f"{elapsed}'",
                "time_str": "Ao Vivo",
                "odd_h": 2.10,
                "odd_d": 3.25,
                "odd_a": 3.40,
                "odd_over25": 1.90,
                "odd_under25": 1.90,
                "provider": "API-Football LiveFeed",
                "venue": fx.get("fixture", {}).get("venue", {}).get("name", "Estádio Oficial")
            })
        except Exception as e:
            continue
    return results

def fetch_league_scoreboard(league_slug: str, league_name: str) -> List[Dict[str, Any]]:
    """
    Busca o placar e partidas em tempo real de uma liga específica via ESPN.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
    matches = []
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        events = data.get("events", [])
        
        for ev in events:
            try:
                ev_id = ev.get("id")
                raw_date = ev.get("date", "")

                # Formatar data/hora local (Brasília UTC-3)
                match_time_str = ""
                is_today = False
                if raw_date:
                    try:
                        dt = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                        dt_br = dt - datetime.timedelta(hours=3)
                        if dt_br.strftime("%Y-%m-%d") == "2026-09-09":
                            match_time_str = f"Hoje às {dt_br.strftime('%H:%M')}"
                            is_today = True
                        else:
                            match_time_str = dt_br.strftime("%d/%m %H:%M")
                    except Exception:
                        match_time_str = raw_date[:16].replace("T", " ")

                competitions = ev.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                
                status_obj = comp.get("status") or {}
                type_obj = status_obj.get("type") or {}
                state = type_obj.get("state", "pre") # 'pre', 'in', 'post'
                display_clock = status_obj.get("displayClock", "")
                status_desc = type_obj.get("description", "Agendado")
                
                if state == "in":
                    status_label = f"🔴 AO VIVO ({display_clock})"
                    badge_type = "live"
                elif state == "post":
                    status_label = f"🏁 Encerrado"
                    badge_type = "post"
                else:
                    status_label = f"⏳ Agendado ({match_time_str})"
                    badge_type = "pre"

                competitors = comp.get("competitors", [])
                home_comp = next((c for c in competitors if isinstance(c, dict) and c.get("homeAway") == "home"), {})
                away_comp = next((c for c in competitors if isinstance(c, dict) and c.get("homeAway") == "away"), {})

                home_team_dict = home_comp.get("team") if isinstance(home_comp, dict) and isinstance(home_comp.get("team"), dict) else {}
                away_team_dict = away_comp.get("team") if isinstance(away_comp, dict) and isinstance(away_comp.get("team"), dict) else {}

                home_id = str(home_team_dict.get("id", ""))
                away_id = str(away_team_dict.get("id", ""))
                home_team = home_team_dict.get("displayName", "Mandante")
                away_team = away_team_dict.get("displayName", "Visitante")
                home_logo = home_team_dict.get("logo", "")
                away_logo = away_team_dict.get("logo", "")
                
                home_score = str(home_comp.get("score", "0")) if isinstance(home_comp, dict) else "0"
                away_score = str(away_comp.get("score", "0")) if isinstance(away_comp, dict) else "0"
                home_form = home_comp.get("form", "") if isinstance(home_comp, dict) else ""
                away_form = away_comp.get("form", "") if isinstance(away_comp, dict) else ""

                # Elenco e Jogadores Reais
                home_squad = get_club_squad(home_team, league_slug, home_id)
                away_squad = get_club_squad(away_team, league_slug, away_id)
                home_star = home_squad.get("craque", {})
                away_star = away_squad.get("craque", {})
                home_scorer = home_squad.get("artilheiro", {})
                away_scorer = away_squad.get("artilheiro", {})

                # Extração de Odds com fallbacks seguros
                odd_h = 2.10
                odd_d = 3.30
                odd_a = 3.20
                odd_over25 = 1.90
                odd_under25 = 1.90
                provider_name = "Estimado / Mercado"

                odds_list = comp.get("odds") or []
                if odds_list and isinstance(odds_list[0], dict):
                    first_odd = odds_list[0]
                    provider_dict = first_odd.get("provider") or {}
                    provider_name = provider_dict.get("displayName", "DraftKings")
                    ml_odds = first_odd.get("moneyline") or {}
                    
                    if isinstance(ml_odds, dict):
                        if "home" in ml_odds:
                            h_close = (ml_odds["home"] or {}).get("close") or {}
                            if isinstance(h_close, dict) and "odds" in h_close:
                                odd_h = american_to_decimal(h_close["odds"])
                        if "away" in ml_odds:
                            a_close = (ml_odds["away"] or {}).get("close") or {}
                            if isinstance(a_close, dict) and "odds" in a_close:
                                odd_a = american_to_decimal(a_close["odds"])
                        if "draw" in ml_odds:
                            d_close = (ml_odds["draw"] or {}).get("close") or {}
                            if isinstance(d_close, dict) and "odds" in d_close:
                                odd_d = american_to_decimal(d_close["odds"])
                    
                    if "drawOdds" in first_odd and odd_d == 3.30:
                        d_ml = (first_odd.get("drawOdds") or {}).get("moneyLine")
                        if d_ml is not None:
                            odd_d = american_to_decimal(d_ml)

                    totals = first_odd.get("total") or {}
                    if isinstance(totals, dict):
                        over_obj = (totals.get("over") or {}).get("close") or {}
                        under_obj = (totals.get("under") or {}).get("close") or {}
                        if isinstance(over_obj, dict) and "odds" in over_obj:
                            odd_over25 = american_to_decimal(over_obj["odds"])
                        if isinstance(under_obj, dict) and "odds" in under_obj:
                            odd_under25 = american_to_decimal(under_obj["odds"])

                venue_dict = comp.get("venue") or {}
                venue = venue_dict.get("fullName", "")

                matches.append({
                    "id": ev_id,
                    "league": league_name,
                    "league_slug": league_slug,
                    "raw_date": raw_date,
                    "is_today": is_today,
                    "home_id": home_id,
                    "away_id": away_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_logo": home_logo,
                    "away_logo": away_logo,
                    "home_form": home_form,
                    "away_form": away_form,
                    "home_squad": home_squad,
                    "away_squad": away_squad,
                    "home_star": home_star,
                    "away_star": away_star,
                    "home_scorer": home_scorer,
                    "away_scorer": away_scorer,
                    "status_state": state,
                    "status_label": status_label,
                    "badge_type": badge_type,
                    "clock": display_clock,
                    "time_str": match_time_str,
                    "odd_h": odd_h,
                    "odd_d": odd_d,
                    "odd_a": odd_a,
                    "odd_over25": odd_over25,
                    "odd_under25": odd_under25,
                    "provider": provider_name,
                    "venue": venue
                })
            except Exception as item_err:
                print(f"Erro ao processar partida em {league_name}: {item_err}")
                continue

    except Exception as e:
        print(f"Erro geral ao buscar partidas da {league_name}: {e}")
    
    return matches

def fetch_all_major_leagues(selected_leagues=None) -> List[Dict[str, Any]]:
    """Busca todas as partidas ao vivo e agendadas nas grandes ligas via API-Football e ESPN."""
    all_matches = []
    
    # 1. Partidas ao vivo globais via API-Football (latência instantânea)
    api_live = fetch_api_football_live_matches()
    if api_live:
        all_matches.extend(api_live)

    # 2. Partidas das ligas selecionadas via ESPN Scoreboard
    target_leagues = MAJOR_LEAGUES
    if selected_leagues:
        target_leagues = {k: v for k, v in MAJOR_LEAGUES.items() if k in selected_leagues}

    for name, slug in target_leagues.items():
        league_matches = fetch_league_scoreboard(slug, name)
        all_matches.extend(league_matches)

    # Ordenar: 1º Jogos AO VIVO, 2º Jogos Agendados de Hoje, 3º Jogos Agendados Futuros, 4º Encerrados
    def sort_key(m):
        st_state = m["status_state"]
        priority = 0 if st_state == "in" else (1 if m.get("is_today") else (2 if st_state == "pre" else 3))
        return (priority, m.get("raw_date", ""))

    all_matches.sort(key=sort_key)
    return all_matches
