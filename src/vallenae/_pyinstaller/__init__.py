"""This package provides a hook for PyInstaller."""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).absolute().parent


def get_hook_dirs() -> list[str]:
    return [str(HERE)]


def get_tests() -> list[str]:
    return [str(HERE)]
