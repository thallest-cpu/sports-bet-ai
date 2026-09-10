import pandas as pd
import json
import os
from typing import Dict, Any, List

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
HISTORY_FILE = os.path.join(CACHE_DIR, "predictions_history.json")

# Estatísticas consolidadas de prova social e assertividade (Calculadas dinamicamente)
SOCIAL_PROOF_METRICS = {
    "win_rate": 0.0,
    "total_tips": 0,
    "greens": 0,
    "reds": 0,
    "roi_pct": 0.0,
    "units_profit": 0.0,
    "avg_odd": 1.84,
    "periodo": "Histórico Real Auditável"
}

MARKET_CATEGORIES = [
    "Todos os Mercados",
    "1X2 (Resultado Final)",
    "Escanteios (Cantos)",
    "Gols (Over/Under)",
    "Ambas Marcam (BTTS)",
    "Cartões"
]

def load_historical_tips() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def get_social_proof_dataframe(category_filter: str = "Todos os Mercados") -> pd.DataFrame:
    """Retorna o DataFrame de histórico filtrado por mercado."""
    history = load_historical_tips()
    df = pd.DataFrame(history)
    if not df.empty and category_filter != "Todos os Mercados" and "categoria" in df.columns:
        df = df[df["categoria"] == category_filter]
    return df

def calculate_market_metrics(df: pd.DataFrame = None) -> Dict[str, Any]:
    """Calcula dinamicamente a taxa de acerto, ROI e lucro para a seleção atual."""
    if df is None:
        df = get_social_proof_dataframe()
        
    if df.empty:
        return {
            "win_rate": 0.0, "total_tips": 0, "greens": 0, "reds": 0,
            "roi_pct": 0.0, "units_profit": 0.0, "avg_odd": 0.0
        }
    
    total = len(df)
    greens = len(df[df["status"].str.contains("GREEN", na=False)])
    reds = len(df[df["status"].str.contains("RED", na=False)])
    win_rate = round((greens / total) * 100.0, 1) if total > 0 else 0.0
    
    # Extrair lucro
    profits = []
    if "lucro" in df.columns:
        for l in df["lucro"]:
            try:
                val = float(str(l).replace("u", "").replace("+", "").strip())
                profits.append(val)
            except Exception:
                profits.append(0.0)
                
    units_profit = round(sum(profits), 2)
    roi_pct = round((units_profit / total) * 100.0, 1) if total > 0 else 0.0
    avg_odd = round(float(df["odd"].mean()), 2) if "odd" in df.columns else 1.84

    return {
        "win_rate": win_rate,
        "total_tips": total,
        "greens": greens,
        "reds": reds,
        "roi_pct": roi_pct,
        "units_profit": units_profit,
        "avg_odd": avg_odd
    }

def update_global_metrics():
    global SOCIAL_PROOF_METRICS
    metrics = calculate_market_metrics()
    SOCIAL_PROOF_METRICS.update(metrics)

update_global_metrics()
