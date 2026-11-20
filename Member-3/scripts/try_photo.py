"""Run damage vision on your own photos.

From Member-3/ (with the venv active):
    python scripts/try_photo.py path/to/photo.jpg [more photos...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.vision import assess_damage  # noqa: E402

if len(sys.argv) < 2:
    sys.exit(__doc__)

print(f"Provider: {config.VISION_PROVIDER}")
for path in sys.argv[1:]:
    result = assess_damage(Path(path).read_bytes())
    print(f"\n{path}")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
