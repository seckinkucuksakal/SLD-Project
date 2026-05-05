#!/usr/bin/env python3
"""
SLD App — komut satırından çalıştırma.

Önerilen: python -m notepad_grid  veya  python notepad_grid.py

Uygulama kodu paket içinde: sld_app/
"""

from __future__ import annotations

from sld_app.app import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
