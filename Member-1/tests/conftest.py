import os
import sys
from pathlib import Path

os.environ["CLAIM_AI_MODE"] = "mock"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
