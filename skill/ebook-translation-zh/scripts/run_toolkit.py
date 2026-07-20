#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys

from locate_toolkit import locate


def main() -> int:
    toolkit = locate()
    environment = dict(os.environ)
    source = str(toolkit / "src")
    environment["PYTHONPATH"] = source + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    return subprocess.call([sys.executable, "-m", "ebook_translation_toolkit", *sys.argv[1:]], env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
