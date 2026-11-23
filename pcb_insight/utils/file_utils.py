"""File system safety and path validation utilities."""

import os
import shutil
from pathlib import Path
from typing import Union


def ensure_directory(dir_path: Union[str, Path]) -> Path:
    """Ensures a directory exists, creating parent directories safely."""
    path = Path(dir_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_file_exists(file_path: Union[str, Path]) -> Path:
    """Validates that a file path exists and is a regular file."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")
    return path


def safe_atomic_write(file_path: Union[str, Path], content: str, encoding: str = "utf-8") -> Path:
    """Writes content to a temporary file before atomically replacing destination."""
    dest = Path(file_path).resolve()
    ensure_directory(dest.parent)
    temp_path = dest.with_suffix(f"{dest.suffix}.tmp.{os.getpid()}")
    try:
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)
        shutil.move(str(temp_path), str(dest))
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return dest
