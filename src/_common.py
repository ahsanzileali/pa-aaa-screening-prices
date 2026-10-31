import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


def url_hash(url):
    """File stem used for each price-file extraction result."""
    return hashlib.md5(url.encode()).hexdigest()[:12]
