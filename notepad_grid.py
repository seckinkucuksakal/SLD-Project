#!/usr/bin/env python3
"""
SLD App — geniş kareli dünya; görünümü kaydırma ve bloğu tıklayarak taşıma.

Tkinter standart kütüphanedir (pip gerekmez).

Etkileşim:
  Sol tık                    → bloğu tıklanan kareye taşır
  Ctrl veya orta/sağ + sürükle → görünümü kaydır (pan)
  Fare tekerleği             → dikey kaydır; Shift + tekerlek → yatay (Windows)

Çalıştırma: python notepad_grid.py
Ok tuşları / WASD ile blok yine hücre hücre hareket eder.
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

    world_cols = 512
    world_rows = 512

    scroll_x = 0
    scroll_y = 0
    bx = 0
    by = 0

    pan_anchor: tuple[int, int, int, int] | None = None

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("920x640")
    root.minsize(320, 240)

    canvas = tk.Canvas(root, highlightthickness=0, bg=bg, cursor="crosshair")
    canvas.pack(fill=tk.BOTH, expand=True)

    def max_scroll() -> tuple[int, int]:
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)
        max_sx = max(0, world_cols * cell - w)
        max_sy = max(0, world_rows * cell - h)
        return max_sx, max_sy

    def clamp_scroll() -> None:
        nonlocal scroll_x, scroll_y
        mx, my = max_scroll()
        scroll_x = max(0, min(scroll_x, mx))
        scroll_y = max(0, min(scroll_y, my))

    def clamp_block() -> None:
        nonlocal bx, by
        bx = max(0, min(bx, world_cols - 1))
        by = max(0, min(by, world_rows - 1))

    def redraw() -> None:
        canvas.delete("all")
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)

        x_world = (scroll_x // cell) * cell
        while x_world <= scroll_x + w:
            sx = x_world - scroll_x
            canvas.create_line(sx, 0, sx, h, fill=grid_color, width=1)
            x_world += cell

        y_world = (scroll_y // cell) * cell
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
        clamp_scroll()
        redraw()

    def screen_to_cell(sx: int, sy: int) -> tuple[int, int]:
        wx = sx + scroll_x
        wy = sy + scroll_y
        return int(wx // cell), int(wy // cell)

    def on_click(event: tk.Event) -> None:
        nonlocal bx, by
        if event.state & 0x4:
            return
        cx, cy = screen_to_cell(event.x, event.y)
        if 0 <= cx < world_cols and 0 <= cy < world_rows:
            bx, by = cx, cy
            redraw()

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
        clamp_scroll()
        redraw()

    def pan_end(_event: tk.Event | None = None) -> None:
        nonlocal pan_anchor
        pan_anchor = None
        canvas.config(cursor="crosshair")

    def on_wheel(event: tk.Event) -> str | None:
        nonlocal scroll_x, scroll_y
        mx, my = max_scroll()
        step = cell

        shift = bool(event.state & 0x1)

        if sys.platform == "win32":
            delta = int(event.delta // 120)
        else:
            delta = 1 if getattr(event, "num", 0) == 4 else -1

        if shift:
            scroll_x -= delta * step
            scroll_x = max(0, min(scroll_x, mx))
        else:
            scroll_y -= delta * step
            scroll_y = max(0, min(scroll_y, my))
        redraw()
        return "break"

    def on_wheel_linux_up(event: tk.Event) -> None:
        nonlocal scroll_x, scroll_y
        mx, my = max_scroll()
        if event.state & 0x1:
            scroll_x -= cell
            scroll_x = max(0, min(scroll_x, mx))
        else:
            scroll_y -= cell
            scroll_y = max(0, min(scroll_y, my))
        redraw()

    def on_wheel_linux_down(event: tk.Event) -> None:
        nonlocal scroll_x, scroll_y
        mx, my = max_scroll()
        if event.state & 0x1:
            scroll_x += cell
            scroll_x = max(0, min(scroll_x, mx))
        else:
            scroll_y += cell
            scroll_y = max(0, min(scroll_y, my))
        redraw()

    def move(dx: int, dy: int) -> None:
        nonlocal bx, by
        bx += dx
        by += dy
        clamp_block()
        redraw()

    def on_key(event: tk.Event) -> None:
        keysym = event.keysym
        if keysym == "Up":
            move(0, -1)
        elif keysym == "Down":
            move(0, 1)
        elif keysym == "Left":
            move(-1, 0)
        elif keysym == "Right":
            move(1, 0)
        elif keysym.lower() == "w":
            move(0, -1)
        elif keysym.lower() == "s":
            move(0, 1)
        elif keysym.lower() == "a":
            move(-1, 0)
        elif keysym.lower() == "d":
            move(1, 0)

    canvas.bind("<Configure>", on_resize)
    canvas.bind("<Button-1>", on_click)
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

    root.bind("<Key>", on_key)
    canvas.bind("<Enter>", lambda _e: canvas.focus_set())

    clamp_block()
    canvas.focus_set()
    root.after_idle(on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
