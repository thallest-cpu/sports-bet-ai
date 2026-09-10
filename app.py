from pathlib import Path
import hashlib
import runpy
import sys
import tempfile

PARTS = (
    "betai_v3_payload.part1",
    "betai_v3_payload.part2",
    "betai_v3_payload.part3",
    "betai_v3_payload.part4",
    "betai_v3_payload.part5",
    "betai_v3_payload.part6",
)
EXPECTED_SHA256 = "6c7523720211360c6260a1d9444a904c967c45b0b8a59deb02ed64fe442be71d"

root = Path(__file__).resolve().parent
missing = [name for name in PARTS if not (root / name).exists()]
if missing:
    raise RuntimeError(f"BetAI V3 incompleto: partes ausentes: {', '.join(missing)}")

payload = b"".join((root / name).read_bytes() for name in PARTS)
actual_sha256 = hashlib.sha256(payload).hexdigest()
if actual_sha256 != EXPECTED_SHA256:
    raise RuntimeError("BetAI V3 inválido: verificação de integridade falhou.")

payload_path = Path(tempfile.gettempdir()) / f"betai_v3_{EXPECTED_SHA256[:12]}.pyz"
if not payload_path.exists() or hashlib.sha256(payload_path.read_bytes()).hexdigest() != EXPECTED_SHA256:
    payload_path.write_bytes(payload)

sys.path.insert(0, str(payload_path))
runpy.run_module("v3_app", run_name="__main__")
