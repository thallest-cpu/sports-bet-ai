from pathlib import Path
import sys

PAYLOAD = Path(__file__).with_name("betai_v3_payload.pyz")
if not PAYLOAD.exists():
    raise RuntimeError("BetAI V3 payload ausente.")

# Carrega a V3 empacotada antes dos módulos antigos do repositório.
sys.path.insert(0, str(PAYLOAD))
import v3_app  # noqa: F401,E402
