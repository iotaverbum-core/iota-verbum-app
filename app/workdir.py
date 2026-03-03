from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path


def get_work_dir() -> Path:
    configured = os.getenv("IV_WORK_DIR") or os.getenv("WORK_DIR")
    if configured:
        base = Path(configured).expanduser()
    else:
        base = Path(tempfile.gettempdir()) / "iota_verbum"
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_work_subdir(prefix: str = "run") -> Path:
    work_dir = get_work_dir()
    target = work_dir / f"{prefix}_{uuid.uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def cleanup_work_subdir(path: Path | None) -> None:
    if not path:
        return
    shutil.rmtree(path, ignore_errors=True)
