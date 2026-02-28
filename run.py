from __future__ import annotations

import sys

from elang.__main__ import main as elang_main


if __name__ == "__main__":
    # Delegate to the package's main entry point so both
    # `python -m elang file.elang` and `python run.py file.elang` work.
    elang_main(sys.argv[1:])

