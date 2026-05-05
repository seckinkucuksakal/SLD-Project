#!/usr/bin/env python3
"""
SLD App — sınırsız kareli dünya; blok yalnızca fare ile sürüklenir.

Tkinter standart kütüphanedir (pip gerekmez).

Etkileşim:
  Blok üzerinde sol tık + sürükle → bloğu ızgarada taşı
  Ctrl veya orta/sağ + sürükle → görünümü kaydır (pan, sınırsız)
  Fare tekerleği → kaydır; Shift + tekerlek → yatay (Windows)
  Sağ üst «Merkezle» → görünümü bloğun üzerine odaklar

Çalıştırma: python notepad_grid.py
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

    scroll_x = 0
    scroll_y = 0
    bx = 0
    by = 0

    dragging_block = False
    pan_anchor: tuple[int, int, int, int] | None = None

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("920x640")
    root.minsize(320, 240)

    bar = tk.Frame(root)
    bar.pack(fill=tk.X)
    center_btn = tk.Button(
        bar,
        text="Merkezle",
        cursor="hand2",
        command=lambda: center_on_block(),
    )
    center_btn.pack(side=tk.RIGHT, padx=10, pady=6)

    canvas = tk.Canvas(root, highlightthickness=0, bg=bg, cursor="crosshair")
    canvas.pack(fill=tk.BOTH, expand=True)

    def screen_to_cell(sx: int, sy: int) -> tuple[int, int]:
        wx = sx + scroll_x
        wy = sy + scroll_y
        return int(wx // cell), int(wy // cell)

    def hit_block(sx: int, sy: int) -> bool:
        cx, cy = screen_to_cell(sx, sy)
        return cx == bx and cy == by

    def redraw() -> None:
        canvas.delete("all")
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)

        first_v = (scroll_x // cell) * cell
        x_world = first_v
        while x_world <= scroll_x + w:
            sx = x_world - scroll_x
            canvas.create_line(sx, 0, sx, h, fill=grid_color, width=1)
            x_world += cell

        first_h = (scroll_y // cell) * cell
        y_world = first_h
        while y_world <= scroll_y + h:
            sy = y_world - scroll_y
            canvas.create_line(0, sy, w, sy, fill=grid_color, width=1)
            y_world += cell

        x0 = bx * cell - scroll_x + block_pad
        y0 = by * cell - scroll_y + block_pad
        x1 = (bx + 1) * cell - scroll_x - block_pad
        y1 = (by + 1) * cell - scroll_y - block_pad
        if x1 > x0 and y1 > y0:
            canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=block_fill,
                outline=block_outline,
                width=2,
                tags="block",
            )

    def on_resize(_event: tk.Event | None = None) -> None:
        redraw()

    def center_on_block() -> None:
        nonlocal scroll_x, scroll_y
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)
        scroll_x = bx * cell + cell // 2 - w // 2
        scroll_y = by * cell + cell // 2 - h // 2
        redraw()

    def on_left_down(event: tk.Event) -> None:
        nonlocal dragging_block
        if event.state & 0x4:
            return
        if hit_block(event.x, event.y):
            dragging_block = True
            canvas.config(cursor="hand2")

    def on_left_motion(event: tk.Event) -> None:
        nonlocal bx, by
        if not dragging_block:
            return
        bx, by = screen_to_cell(event.x, event.y)
        redraw()

    def on_left_up(_event: tk.Event | None = None) -> None:
        nonlocal dragging_block
        dragging_block = False
        canvas.config(cursor="crosshair")

    def pan_start(event: tk.Event) -> None:
        nonlocal pan_anchor
        pan_anchor = (event.x, event.y, scroll_x, scroll_y)
        canvas.config(cursor="fleur")

    def pan_motion(event: tk.Event) -> None:
        nonlocal scroll_x, scroll_y, pan_anchor
        if pan_anchor is None:
            return
        ax, ay, sx0, sy0 = pan_anchor
        scroll_x = sx0 + (ax - event.x)
        scroll_y = sy0 + (ay - event.y)
        redraw()

    def pan_end(_event: tk.Event | None = None) -> None:
        nonlocal pan_anchor
        pan_anchor = None
        canvas.config(cursor="crosshair" if not dragging_block else "hand2")

    def on_wheel(event: tk.Event) -> str | None:
        nonlocal scroll_x, scroll_y
        step = cell
        shift = bool(event.state & 0x1)

        if sys.platform == "win32":
            delta = int(event.delta // 120)
        else:
            delta = 1 if getattr(event, "num", 0) == 4 else -1

        if shift:
            scroll_x -= delta * step
        else:
            scroll_y -= delta * step
        redraw()
        return "break"

    def on_wheel_linux_up(event: tk.Event) -> None:
        nonlocal scroll_x, scroll_y
        if event.state & 0x1:
            scroll_x -= cell
        else:
            scroll_y -= cell
        redraw()

    def on_wheel_linux_down(event: tk.Event) -> None:
        nonlocal scroll_x, scroll_y
        if event.state & 0x1:
            scroll_x += cell
        else:
            scroll_y += cell
        redraw()

    canvas.bind("<Configure>", on_resize)
    canvas.bind("<Button-1>", on_left_down)
    canvas.bind("<B1-Motion>", on_left_motion)
    canvas.bind("<ButtonRelease-1>", on_left_up)
    canvas.bind("<Control-Button-1>", pan_start)
    canvas.bind("<Control-B1-Motion>", pan_motion)
    canvas.bind("<Control-ButtonRelease-1>", pan_end)
    canvas.bind("<Button-2>", pan_start)
    canvas.bind("<B2-Motion>", pan_motion)
    canvas.bind("<ButtonRelease-2>", pan_end)
    canvas.bind("<Button-3>", pan_start)
    canvas.bind("<B3-Motion>", pan_motion)
    canvas.bind("<ButtonRelease-3>", pan_end)

    if sys.platform == "win32":
        canvas.bind("<MouseWheel>", on_wheel)
    else:
        canvas.bind("<Button-4>", on_wheel_linux_up)
        canvas.bind("<Button-5>", on_wheel_linux_down)

    canvas.bind("<Enter>", lambda _e: canvas.focus_set())

    root.after_idle(on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
