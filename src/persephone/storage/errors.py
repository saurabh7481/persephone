from __future__ import annotations


class StorageError(RuntimeError):
    """Base class for local artifact storage failures."""


class UnsupportedStateValueError(StorageError):
    """Raised when state storage receives a value kind it cannot persist."""
