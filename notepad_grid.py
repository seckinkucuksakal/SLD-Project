#!/usr/bin/env python3
"""
SLD App — düz kareli zemin üzerinde tek karelik bloğu hareket ettirme.

Tkinter standart kütüphanedir (pip gerekmez).
- Windows: python.org kurulumunda Tk genelde hazırdır.
- Linux: sudo apt install python3-tk

Çalıştırma: python notepad_grid.py  veya  python3 notepad_grid.py
Ok tuşları veya WASD ile blok hücre hücre hareket eder.
"""

from __future__ import annotations

import sys
import tkinter as tk


def _windows_dpi_before_tk() -> None:
    """Yüksek DPI ekranlarda bulanık görünmeyi azaltır (Windows). Tk() öncesi çağrılmalı."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def main() -> None:
    _windows_dpi_before_tk()

    cell = 28
    bg = "#f4f4f5"
    grid_color = "#d4d4d8"
    block_fill = "#3b82f6"
    block_outline = "#1d4ed8"
    block_pad = 3

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("920x640")
    root.minsize(320, 240)

    canvas = tk.Canvas(root, highlightthickness=0, bg=bg)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Grid boyutu ve blok konumu (hücre indeksleri)
    cols = 1
    rows = 1
    bx = 0
    by = 0

    def clamp_pos() -> None:
        nonlocal bx, by
        bx = max(0, min(bx, cols - 1))
        by = max(0, min(by, rows - 1))

    def redraw() -> None:
        canvas.delete("all")
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)

        # Dikey çizgiler
        x = 0
        while x <= w:
            canvas.create_line(x, 0, x, h, fill=grid_color, width=1)
            x += cell
        # Yatay çizgiler
        y = 0
        while y <= h:
            canvas.create_line(0, y, w, y, fill=grid_color, width=1)
            y += cell

        x0 = bx * cell + block_pad
        y0 = by * cell + block_pad
        x1 = (bx + 1) * cell - block_pad
        y1 = (by + 1) * cell - block_pad
        if x1 > x0 and y1 > y0:
            canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=block_fill,
                outline=block_outline,
                width=2,
            )

    def on_resize(_event: tk.Event | None = None) -> None:
        nonlocal cols, rows
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)
        cols = max(1, w // cell)
        rows = max(1, h // cell)
        clamp_pos()
        redraw()

    def move(dx: int, dy: int) -> None:
        nonlocal bx, by
        bx += dx
        by += dy
        clamp_pos()
        redraw()

    def on_key(event: tk.Event) -> None:
        keysym = event.keysym
        # Ok tuşları
        if keysym == "Up":
            move(0, -1)
        elif keysym == "Down":
            move(0, 1)
        elif keysym == "Left":
            move(-1, 0)
        elif keysym == "Right":
            move(1, 0)
        # WASD
        elif keysym.lower() == "w":
            move(0, -1)
        elif keysym.lower() == "s":
            move(0, 1)
        elif keysym.lower() == "a":
            move(-1, 0)
        elif keysym.lower() == "d":
            move(1, 0)

    canvas.bind("<Configure>", on_resize)
    root.bind("<Key>", on_key)

    canvas.focus_set()
    root.after_idle(on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
