from __future__ import annotations

from pathlib import Path
from typing import Final

DIT_PATH: Final = Path(__file__).parent.parent.parent
CORPORA_PATH: Final = DIT_PATH / "corpora"
LOGS_PATH: Final = DIT_PATH / "logs"
SUBMODULES_PATH: Final = DIT_PATH / "git-submodules"
