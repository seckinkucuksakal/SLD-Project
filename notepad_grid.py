#!/usr/bin/env python3
"""
SLD App — sınırsız kareli dünya; blok dünya koordinatlarında pürüzsüz hareket eder.

Tkinter standart kütüphanedir (pip gerekmez).

Etkileşim:
  Bloğun üzerinde sol tık + sürükle → pürüzsüz taşı (çizgiler arasında durabilir)
  Ctrl veya orta/sağ + sürükle → görünümü kaydır (pan, sınırsız)
  Fare tekerleği → yakınlaştır / uzaklaştır (imleç altı sabit kalır)
  Shift + tekerlek → yatay kaydır | Ctrl + tekerlek → dikey kaydır
  Sağ üst «Merkezle» → görünümü bloğun üzerine odaklar

Çalıştırma: python notepad_grid.py
"""

from __future__ import annotations

import math
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

    block_half = (cell - 2 * block_pad) / 2.0

    # Blok merkezi, dünya birimi (zoom'dan bağımsız)
    block_cx = cell / 2.0
    block_cy = cell / 2.0

    scroll_x = 0.0
    scroll_y = 0.0
    zoom = 1.0
    ZOOM_MIN = 0.08
    ZOOM_MAX = 16.0
    ZOOM_FACTOR = 1.12

    dragging_block = False
    drag_off_x = 0.0
    drag_off_y = 0.0
    pan_anchor: tuple[int, int, float, float] | None = None

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("920x640")
    root.minsize(320, 240)

    canvas = tk.Canvas(root, highlightthickness=0, bg=bg, cursor="crosshair")
    canvas.pack(fill=tk.BOTH, expand=True)

    center_btn = tk.Button(
        canvas,
        text="Merkezle",
        cursor="hand2",
        relief=tk.FLAT,
        bg="#fafafa",
        fg="#334155",
        activebackground="#e4e4e7",
        activeforeground="#0f172a",
        bd=0,
        padx=12,
        pady=6,
        highlightthickness=1,
        highlightbackground="#d4d4d8",
        highlightcolor="#d4d4d8",
        command=lambda: center_on_block(),
    )
    center_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

    def screen_to_world(sx: int, sy: int) -> tuple[float, float]:
        return scroll_x + float(sx) / zoom, scroll_y + float(sy) / zoom

    def hit_block(sx: int, sy: int) -> bool:
        mx, my = screen_to_world(sx, sy)
        return (
            abs(mx - block_cx) <= block_half
            and abs(my - block_cy) <= block_half
        )

    def redraw() -> None:
        canvas.delete("all")
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)

        z = zoom
        wx_left = scroll_x
        wx_right = scroll_x + w / z

        first_v = math.floor(wx_left / cell) * cell
        x_world = first_v
        while x_world <= wx_right + 1e-9:
            sx = (x_world - scroll_x) * z
            if -2 <= sx <= w + 2:
                lw = max(1, int(round(z)))
                canvas.create_line(sx, 0, sx, h, fill=grid_color, width=min(lw, 3))
            x_world += cell

        wy_top = scroll_y
        wy_bot = scroll_y + h / z
        first_h = math.floor(wy_top / cell) * cell
        y_world = first_h
        while y_world <= wy_bot + 1e-9:
            sy = (y_world - scroll_y) * z
            if -2 <= sy <= h + 2:
                lw = max(1, int(round(z)))
                canvas.create_line(0, sy, w, sy, fill=grid_color, width=min(lw, 3))
            y_world += cell

        bx = (block_cx - scroll_x) * z
        by = (block_cy - scroll_y) * z
        half_s = block_half * z
        canvas.create_rectangle(
            bx - half_s,
            by - half_s,
            bx + half_s,
            by + half_s,
            fill=block_fill,
            outline=block_outline,
            width=max(1, int(round(2 * z / max(zoom, 0.25)))),
            tags="block",
        )

        center_btn.lift()

    def on_resize(_event: tk.Event | None = None) -> None:
        redraw()

    def center_on_block() -> None:
        nonlocal scroll_x, scroll_y
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)
        scroll_x = block_cx - w / (2.0 * zoom)
        scroll_y = block_cy - h / (2.0 * zoom)
        redraw()

    def zoom_at_screen(mx: int, my: int, delta_notches: int) -> None:
        nonlocal scroll_x, scroll_y, zoom
        if delta_notches == 0:
            return
        old_z = zoom
        new_z = old_z * (ZOOM_FACTOR**delta_notches)
        new_z = max(ZOOM_MIN, min(ZOOM_MAX, new_z))
        if new_z == old_z:
            return
        wx = scroll_x + mx / old_z
        wy = scroll_y + my / old_z
        zoom = new_z
        scroll_x = wx - mx / zoom
        scroll_y = wy - my / zoom
        redraw()

    def on_left_down(event: tk.Event) -> None:
        nonlocal dragging_block, drag_off_x, drag_off_y
        if event.state & 0x4:
            return
        if hit_block(event.x, event.y):
            dragging_block = True
            wx, wy = screen_to_world(event.x, event.y)
            drag_off_x = wx - block_cx
            drag_off_y = wy - block_cy
            canvas.config(cursor="hand2")

    def on_left_motion(event: tk.Event) -> None:
        nonlocal block_cx, block_cy
        if not dragging_block:
            return
        wx, wy = screen_to_world(event.x, event.y)
        block_cx = wx - drag_off_x
        block_cy = wy - drag_off_y
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
        scroll_x = sx0 + (ax - event.x) / zoom
        scroll_y = sy0 + (ay - event.y) / zoom
        redraw()

    def pan_end(_event: tk.Event | None = None) -> None:
        nonlocal pan_anchor
        pan_anchor = None
        canvas.config(cursor="crosshair" if not dragging_block else "hand2")

    def on_wheel_win(event: tk.Event) -> str | None:
        shift = bool(event.state & 0x1)
        ctrl = bool(event.state & 0x4)
        delta_lines = int(event.delta // 120)
        if delta_lines == 0 and event.delta != 0:
            delta_lines = 1 if event.delta > 0 else -1

        if not shift and not ctrl:
            zoom_at_screen(event.x, event.y, delta_lines)
            return "break"

        step = float(cell)
        if shift:
            scroll_x -= delta_lines * step
        else:
            scroll_y -= delta_lines * step
        redraw()
        return "break"

    def on_wheel_linux(event: tk.Event) -> None:
        shift = bool(event.state & 0x1)
        ctrl = bool(event.state & 0x4)
        up = event.num == 4
        delta_lines = 1 if up else -1

        if not shift and not ctrl:
            zoom_at_screen(event.x, event.y, delta_lines)
            return

        step = float(cell)
        if shift:
            scroll_x -= delta_lines * step
        else:
            scroll_y -= delta_lines * step
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
        canvas.bind("<MouseWheel>", on_wheel_win)
    else:
        canvas.bind("<Button-4>", on_wheel_linux)
        canvas.bind("<Button-5>", on_wheel_linux)

    canvas.bind("<Enter>", lambda _e: canvas.focus_set())

    root.after_idle(on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
