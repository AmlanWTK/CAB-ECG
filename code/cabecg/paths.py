"""Where the data and outputs live. Everything is relative to the repository root."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
OUTPUTS = REPO / "outputs"

PTBXL_ROOT = DATA / "ptbxl"
ECG_ARRHYTHMIA_ROOT = DATA / "ecg_arrhythmia"
CHALLENGE_ROOT = DATA / "challenge2021"
CHALLENGE_TRAINING = CHALLENGE_ROOT / "training"
CODE15_ROOT = DATA / "code15"

INDEX_DIR = OUTPUTS / "index"
INDEX_CSV = INDEX_DIR / "index.csv"
AUDIT_DIR = OUTPUTS / "audit"


def find_one(root: Path, pattern: str) -> Path:
    """Return the single file matching a recursive glob, so long unzip folder names do not matter."""
    hits = sorted(root.rglob(pattern))
    if not hits:
        raise FileNotFoundError(f"No file matching {pattern!r} under {root}")
    return hits[0]


def rel(path: Path) -> str:
    """Path relative to data/, with forward slashes, for storing in the index."""
    return Path(path).resolve().relative_to(DATA.resolve()).as_posix()
