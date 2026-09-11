"""Resolve bundled asset paths (dev tree and frozen PyInstaller builds)."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        candidates: list[Path] = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass))
        candidates.append(exe.parent)
        # Digico-x-Soundscape.app/Contents/MacOS/… → Resources / Frameworks
        if exe.parent.name == "MacOS":
            contents = exe.parent.parent
            candidates.append(contents / "Resources")
            candidates.append(contents / "Frameworks")
        for base in candidates:
            if (base / "assets").is_dir():
                return base
        return candidates[0] if candidates else exe.parent
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return project_root() / "assets"


def asset_path(*parts: str) -> Path:
    return assets_dir().joinpath(*parts)
