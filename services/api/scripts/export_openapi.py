"""Write the API contract to openapi.json (source for generated TS types, A-08).

Usage:  python scripts/export_openapi.py          # write
        python scripts/export_openapi.py --check  # fail if the committed file is stale (CI)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

TARGET = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> int:
    rendered = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text() != rendered:
            print("openapi.json is stale: run `python scripts/export_openapi.py` and `npm run gen:types`")
            return 1
        print("openapi.json is up to date")
        return 0
    TARGET.write_text(rendered)
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
