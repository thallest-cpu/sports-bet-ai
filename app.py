from pathlib import Path
import hashlib
import runpy
import shutil
import sys
import tempfile
import zipfile

from hotfix_v4 import apply_hotfix

PARTS = (
    "betai_v3_payload.part1",
    "betai_v3_payload.part2",
    "betai_v3_payload.part3",
    "betai_v3_payload.part4",
    "betai_v3_payload.part5",
    "betai_v3_payload.part6",
)
EXPECTED_SHA256 = "6c7523720211360c6260a1d9444a904c967c45b0b8a59deb02ed64fe442be71d"
HOTFIX_VERSION = "v4"

root = Path(__file__).resolve().parent
missing = [name for name in PARTS if not (root / name).exists()]
if missing:
    raise RuntimeError(f"BetAI V3 incompleto: partes ausentes: {', '.join(missing)}")

payload = b"".join((root / name).read_bytes() for name in PARTS)
actual_sha256 = hashlib.sha256(payload).hexdigest()
if actual_sha256 != EXPECTED_SHA256:
    raise RuntimeError("BetAI V3 inválido: verificação de integridade falhou.")

# Diretório versionado por payload + hotfix. Isso força uma extração limpa
# quando alteramos a camada de compatibilidade sem duplicar o pacote inteiro.
extract_root = Path(tempfile.gettempdir()) / f"betai_v3_{EXPECTED_SHA256[:12]}_{HOTFIX_VERSION}"
marker = extract_root / ".ready"
if not marker.exists():
    if extract_root.exists():
        shutil.rmtree(extract_root, ignore_errors=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    payload_path = extract_root / "payload.zip"
    payload_path.write_bytes(payload)
    with zipfile.ZipFile(payload_path, "r") as archive:
        archive.extractall(extract_root)
    payload_path.unlink(missing_ok=True)

    # Aplica as correções de estado das fontes, mensagens e UX sobre a V3
    # extraída. O hotfix valida hashes antes/depois para evitar patch parcial.
    apply_hotfix(extract_root)
    marker.write_text(f"{EXPECTED_SHA256}:{HOTFIX_VERSION}", encoding="utf-8")

# Streamlit reutiliza o processo Python em reruns. Removemos módulos `src`
# antigos do cache antes de carregar a versão corrigida.
for module_name in list(sys.modules):
    if module_name == "src" or module_name.startswith("src.") or module_name == "v3_app":
        sys.modules.pop(module_name, None)

sys.path.insert(0, str(extract_root))
runpy.run_path(str(extract_root / "v3_app.py"), run_name="__main__")
