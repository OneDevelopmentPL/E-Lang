from __future__ import annotations

import sys
from pathlib import Path

from .errors import ELangError
from .interpreter import run_file


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 1:
        print("Usage: python -m elang <file.elang>")
        sys.exit(1)

    path = Path(argv[0])
    if not path.exists():
        print(f"Something went wrong: I could not find a file called '{path}'.")
        sys.exit(1)

    try:
        run_file(str(path))
    except ELangError as e:
        print(f"Something went wrong: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

