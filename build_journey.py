"""Embed latest session JSON into journey.html template."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SESSION = json.loads((ROOT / "sessions" / "bc700e8d94b1.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "journey.template.html").read_text(encoding="utf-8")
(ROOT / "journey.html").write_text(
    TEMPLATE.replace("__SESSION_JSON__", json.dumps(SESSION, ensure_ascii=False)),
    encoding="utf-8",
)
print("Wrote journey.html")
