from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ELangError(Exception):
    """Base class for all E-Lang related errors."""

    message: str
    line: Optional[int] = None
    column: Optional[int] = None

    def __str__(self) -> str:
        location = ""
        if self.line is not None:
            location = f" on line {self.line}"
            if self.column is not None:
                location += f", column {self.column}"
        return f"{self.message}{location}."


class ELangSyntaxError(ELangError):
    """Raised when the source does not follow E-Lang grammar."""


class ELangNameError(ELangError):
    """Raised when using a variable or function that does not exist."""


class ELangTypeError(ELangError):
    """Raised when an operation is applied to values of incompatible types."""


class ELangRuntimeError(ELangError):
    """Raised for other runtime failures not covered by more specific errors."""

