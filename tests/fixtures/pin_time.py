"""Fija las respuestas de `now` de un fixture grabado a un instante conocido.

Uso: python tests/fixtures/pin_time.py <fixture.json> 2026-09-28T12:04:05-03:00
"""

import json
import sys
from datetime import datetime, timedelta

path, start = sys.argv[1], datetime.fromisoformat(sys.argv[2])
data = json.load(open(path, encoding="utf-8"))
recorded = [datetime.fromisoformat(v) for v in data["calls"]["now[]"]]
data["calls"]["now[]"] = [
    (start + (t - recorded[0])).isoformat(timespec="seconds") for t in recorded
]
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
