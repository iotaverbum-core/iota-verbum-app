from __future__ import annotations

import sys
from pathlib import Path


def _add_local_venv_site_packages() -> None:
    root = Path(__file__).resolve().parent
    candidate = root / ".venv" / "Lib" / "site-packages"
    if candidate.exists():
        site_packages = str(candidate)
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)


def _configure_pycache_prefix() -> None:
    root = Path(__file__).resolve().parent
    pycache_root = root / ".pycache"
    pycache_root.mkdir(parents=True, exist_ok=True)
    sys.pycache_prefix = str(pycache_root)


_add_local_venv_site_packages()
_configure_pycache_prefix()
