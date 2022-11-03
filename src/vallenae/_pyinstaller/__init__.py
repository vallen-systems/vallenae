"""This package provides a hook for PyInstaller."""

from pathlib import Path
from typing import List

HERE = Path(__file__).absolute().parent


def get_hook_dirs() -> List[str]:
    return [str(HERE)]


def get_tests() -> List[str]:
    return [str(HERE)]
