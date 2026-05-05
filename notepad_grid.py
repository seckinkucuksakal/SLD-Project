#!/usr/bin/env python3
"""
SLD App — kareli dünya; paletten şekil sürükleyip bırakma ve yerleşik şekilleri taşıma.

Tkinter standart kütüphanedir (pip gerekmez).

Etkileşim:
  Paletten şekle basılı tut → fare ucunda hayalet önizleme; tuval üzerinde bırak → yerleşir
  Yerleşik şekil üzerinde sol sürükle → taşı
  Ctrl veya orta/sağ + sürükle → pan
  Fare tekerleği → yakınlaştır / uzaklaştır | Shift/Ctrl + tekerlek → kaydır
  Sağ üst «Merkezle» → tüm şekilleri görünüme ortalar

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


def _point_in_triangle(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
) -> bool:
    def sign(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
        return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)

    d1 = sign(px, py, ax, ay, bx, by)
    d2 = sign(px, py, bx, by, cx, cy)
    d3 = sign(px, py, cx, cy, ax, ay)
    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)


def _tri_vertices(s: dict[str, float | str]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    cx = float(s["cx"])
    cy = float(s["cy"])
    tw = float(s["tw"])
    bh = float(s["bh"])
    ah = float(s["ah"])
    return (
        (cx - tw, cy + bh),
        (cx + tw, cy + bh),
        (cx, cy - ah),
    )


def main() -> None:
    _windows_dpi_before_tk()

    cell = 28
    bg = "#f4f4f5"
    grid_color = "#d4d4d8"
    block_pad = 3

    COL_SQUARE = "#2563eb"
    COL_RECT = "#16a34a"
    COL_TRI = "#ea580c"
    OUTLINE = "#171717"

    shapes: list[dict[str, float | str]] = []

    scroll_x = 0.0
    scroll_y = 0.0
    zoom = 1.0
    ZOOM_MIN = 0.08
    ZOOM_MAX = 16.0
    ZOOM_FACTOR = 1.12

    dragging_shape_idx: int | None = None
    drag_off_x = 0.0
    drag_off_y = 0.0
    pan_anchor: tuple[int, int, float, float] | None = None

    palette_drag_kind: str | None = None
    ghost_win: tk.Toplevel | None = None
    GHOST_WH = 72
    TRANSP_GHOST = "#ff00fe"

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("1080x640")
    root.minsize(480, 240)

    body = tk.Frame(root)
    body.pack(fill=tk.BOTH, expand=True)

    canvas_holder = tk.Frame(body)
    canvas_holder.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(canvas_holder, highlightthickness=0, bg=bg, cursor="crosshair")
    canvas.pack(fill=tk.BOTH, expand=True)

    panel_w = 256
    panel_bg = "#f8fafc"
    card_bg = "#ffffff"
    border_muted = "#e2e8f0"
    text_primary = "#0f172a"
    text_muted = "#64748b"

    panel = tk.Frame(body, width=panel_w, bg=panel_bg)
    panel.pack(side=tk.RIGHT, fill=tk.Y)
    panel.pack_propagate(False)

    panel_inner = tk.Frame(panel, bg=panel_bg)
    panel_inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=16)

    tk.Label(
        panel_inner,
        text="Şekiller",
        bg=panel_bg,
        fg=text_primary,
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w")

    tk.Label(
        panel_inner,
        text="Sürükleyip tuval üzerine bırakın.",
        bg=panel_bg,
        fg=text_muted,
        font=("Segoe UI", 9),
        wraplength=panel_w - 48,
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(4, 14))

    card = tk.Frame(
        panel_inner,
        bg=card_bg,
        highlightthickness=1,
        highlightbackground=border_muted,
        highlightcolor=border_muted,
    )
    card.pack(fill=tk.BOTH, expand=True)

    card_body = tk.Frame(card, bg=card_bg)
    card_body.pack(fill=tk.BOTH, expand=True, padx=2, pady=(10, 12))

    def make_shape(kind: str, cx: float, cy: float) -> dict[str, float | str]:
        if kind == "square":
            half = (cell - 2 * block_pad) / 2.0
            return {"kind": "square", "cx": cx, "cy": cy, "half": half}
        if kind == "rect":
            return {"kind": "rect", "cx": cx, "cy": cy, "hw": cell * 0.9, "hh": cell * 0.45}
        return {
            "kind": "triangle",
            "cx": cx,
            "cy": cy,
            "tw": cell * 0.5,
            "bh": cell * 0.25,
            "ah": cell * 0.5,
        }

    def shape_contains(mx: float, my: float, s: dict[str, float | str]) -> bool:
        k = str(s["kind"])
        cx = float(s["cx"])
        cy = float(s["cy"])
        if k == "square":
            h = float(s["half"])
            return abs(mx - cx) <= h and abs(my - cy) <= h
        if k == "rect":
            return abs(mx - cx) <= float(s["hw"]) and abs(my - cy) <= float(s["hh"])
        ax, ay = _tri_vertices(s)[0]
        bx, by = _tri_vertices(s)[1]
        cxp, cyp = _tri_vertices(s)[2]
        return _point_in_triangle(mx, my, ax, ay, bx, by, cxp, cyp)

    def hit_top_shape(sx: int, sy: int) -> int | None:
        mx, my = screen_to_world(sx, sy)
        for i in range(len(shapes) - 1, -1, -1):
            if shape_contains(mx, my, shapes[i]):
                return i
        return None

    def bbox_world() -> tuple[float, float, float, float] | None:
        if not shapes:
            return None
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for s in shapes:
            k = str(s["kind"])
            cx = float(s["cx"])
            cy = float(s["cy"])
            if k == "square":
                h = float(s["half"])
                min_x = min(min_x, cx - h)
                max_x = max(max_x, cx + h)
                min_y = min(min_y, cy - h)
                max_y = max(max_y, cy + h)
            elif k == "rect":
                hw = float(s["hw"])
                hh = float(s["hh"])
                min_x = min(min_x, cx - hw)
                max_x = max(max_x, cx + hw)
                min_y = min(min_y, cy - hh)
                max_y = max(max_y, cy + hh)
            else:
                for px, py in _tri_vertices(s):
                    min_x = min(min_x, px)
                    max_x = max(max_x, px)
                    min_y = min(min_y, py)
                    max_y = max(max_y, py)
        return min_x, min_y, max_x, max_y

    center_btn = tk.Button(
        canvas_holder,
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
        command=lambda: center_on_shapes(),
    )
    center_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

    def hide_ghost() -> None:
        nonlocal ghost_win
        if ghost_win is not None:
            try:
                ghost_win.destroy()
            except tk.TclError:
                pass
            ghost_win = None

    def draw_ghost_preview(c: tk.Canvas, kind: str, cx: int, cy: int) -> None:
        ol = "#1e293b"
        ow = 2
        if kind == "square":
            h = 22
            c.create_rectangle(
                cx - h,
                cy - h,
                cx + h,
                cy + h,
                fill=COL_SQUARE,
                outline=ol,
                width=ow,
            )
        elif kind == "rect":
            c.create_rectangle(
                cx - 28,
                cy - 14,
                cx + 28,
                cy + 14,
                fill=COL_RECT,
                outline=ol,
                width=ow,
            )
        else:
            c.create_polygon(
                cx,
                cy - 24,
                cx - 26,
                cy + 18,
                cx + 26,
                cy + 18,
                fill=COL_TRI,
                outline=ol,
                width=ow,
            )

    def show_ghost(kind: str) -> None:
        nonlocal ghost_win
        hide_ghost()
        ghost_win = tk.Toplevel(root)
        ghost_win.overrideredirect(True)
        ghost_win.attributes("-topmost", True)
        ghost_canvas_bg = TRANSP_GHOST
        try:
            ghost_win.attributes("-transparentcolor", TRANSP_GHOST)
        except tk.TclError:
            ghost_canvas_bg = "#ffffff"
        gc = tk.Canvas(
            ghost_win,
            width=GHOST_WH,
            height=GHOST_WH,
            bg=ghost_canvas_bg,
            highlightthickness=0,
        )
        gc.pack()
        draw_ghost_preview(gc, kind, GHOST_WH // 2, GHOST_WH // 2)
        rx, ry = root.winfo_pointerxy()
        ghost_win.geometry(
            f"{GHOST_WH}x{GHOST_WH}+{rx - GHOST_WH // 2}+{ry - GHOST_WH // 2}"
        )

    def palette_motion(_event: tk.Event | None = None) -> None:
        if palette_drag_kind is None or ghost_win is None:
            return
        rx, ry = root.winfo_pointerxy()
        ghost_win.geometry(
            f"{GHOST_WH}x{GHOST_WH}+{rx - GHOST_WH // 2}+{ry - GHOST_WH // 2}"
        )

    def screen_to_world(sx: int, sy: int) -> tuple[float, float]:
        return scroll_x + float(sx) / zoom, scroll_y + float(sy) / zoom

    def outline_w() -> int:
        return max(1, int(round(2 * zoom / max(zoom, 0.25))))

    def draw_shape_ui(s: dict[str, float | str]) -> None:
        z = zoom
        k = str(s["kind"])
        ox = outline_w()
        if k == "square":
            bx = (float(s["cx"]) - scroll_x) * z
            by = (float(s["cy"]) - scroll_y) * z
            hs = float(s["half"]) * z
            canvas.create_rectangle(
                bx - hs,
                by - hs,
                bx + hs,
                by + hs,
                fill=COL_SQUARE,
                outline=OUTLINE,
                width=ox,
            )
        elif k == "rect":
            bx = (float(s["cx"]) - scroll_x) * z
            by = (float(s["cy"]) - scroll_y) * z
            hw = float(s["hw"]) * z
            hh = float(s["hh"]) * z
            canvas.create_rectangle(
                bx - hw,
                by - hh,
                bx + hw,
                by + hh,
                fill=COL_RECT,
                outline=OUTLINE,
                width=ox,
            )
        else:
            pts: list[float] = []
            for px, py in _tri_vertices(s):
                pts.append((px - scroll_x) * z)
                pts.append((py - scroll_y) * z)
            canvas.create_polygon(*pts, fill=COL_TRI, outline=OUTLINE, width=ox)

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

        for s in shapes:
            draw_shape_ui(s)

    def on_resize(_event: tk.Event | None = None) -> None:
        redraw()

    def center_on_shapes() -> None:
        nonlocal scroll_x, scroll_y, zoom
        w = max(int(canvas.winfo_width()), 1)
        h = max(int(canvas.winfo_height()), 1)
        bb = bbox_world()
        if bb is None:
            scroll_x = 0.0
            scroll_y = 0.0
            zoom = 1.0
            redraw()
            return
        min_x, min_y, max_x, max_y = bb
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        scroll_x = cx - w / (2.0 * zoom)
        scroll_y = cy - h / (2.0 * zoom)
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

    def palette_press(kind: str) -> None:
        nonlocal palette_drag_kind
        palette_drag_kind = kind
        show_ghost(kind)
        root.bind_all("<B1-Motion>", palette_motion)
        root.bind_all("<ButtonRelease-1>", finish_palette_drop)

    def finish_palette_drop(_event: tk.Event | None = None) -> None:
        nonlocal palette_drag_kind
        if palette_drag_kind is None:
            return
        root.unbind_all("<B1-Motion>")
        root.unbind_all("<ButtonRelease-1>")
        hide_ghost()
        k = palette_drag_kind
        palette_drag_kind = None
        if k is None:
            return

        px = root.winfo_pointerx() - canvas.winfo_rootx()
        py = root.winfo_pointery() - canvas.winfo_rooty()
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if px < 0 or py < 0 or px >= cw or py >= ch:
            return

        wx, wy = screen_to_world(int(px), int(py))
        shapes.append(make_shape(k, wx, wy))
        redraw()

    def on_canvas_left_down(event: tk.Event) -> None:
        nonlocal dragging_shape_idx, drag_off_x, drag_off_y
        if palette_drag_kind is not None:
            return
        if event.state & 0x4:
            return
        idx = hit_top_shape(event.x, event.y)
        if idx is None:
            return
        dragging_shape_idx = idx
        wx, wy = screen_to_world(event.x, event.y)
        drag_off_x = wx - float(shapes[idx]["cx"])
        drag_off_y = wy - float(shapes[idx]["cy"])
        canvas.config(cursor="hand2")

    def on_canvas_left_motion(event: tk.Event) -> None:
        nonlocal dragging_shape_idx
        if dragging_shape_idx is None:
            return
        wx, wy = screen_to_world(event.x, event.y)
        i = dragging_shape_idx
        shapes[i]["cx"] = wx - drag_off_x
        shapes[i]["cy"] = wy - drag_off_y
        redraw()

    def on_canvas_left_up(_event: tk.Event | None = None) -> None:
        nonlocal dragging_shape_idx
        dragging_shape_idx = None
        canvas.config(cursor="crosshair")

    def pan_start(event: tk.Event) -> None:
        nonlocal pan_anchor
        if palette_drag_kind is not None:
            return
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
        canvas.config(cursor="crosshair" if dragging_shape_idx is None else "hand2")

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

    def cancel_palette_escape(_event: tk.Event | None = None) -> None:
        nonlocal palette_drag_kind
        if palette_drag_kind is None:
            return
        root.unbind_all("<B1-Motion>")
        root.unbind_all("<ButtonRelease-1>")
        palette_drag_kind = None
        hide_ghost()

    def make_palette_row(label: str, subtitle: str, kind: str, draw_fn) -> None:
        row = tk.Frame(card_body, bg=card_bg)
        row.pack(fill=tk.X, padx=12, pady=(0, 10))

        preview = tk.Frame(
            row,
            bg="#f8fafc",
            highlightthickness=1,
            highlightbackground=border_muted,
            highlightcolor=border_muted,
        )
        preview.pack(side=tk.LEFT)
        cv = tk.Canvas(
            preview,
            width=72,
            height=72,
            bg="#f8fafc",
            highlightthickness=0,
            cursor="hand2",
        )
        cv.pack(padx=6, pady=6)
        draw_fn(cv, 36, 36)
        cv.bind("<ButtonPress-1>", lambda _e, k=kind: palette_press(k))

        txt = tk.Frame(row, bg=card_bg)
        txt.pack(side=tk.LEFT, padx=(12, 0), fill=tk.Y)
        tk.Label(
            txt,
            text=label,
            bg=card_bg,
            fg=text_primary,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(anchor="nw")
        tk.Label(
            txt,
            text=subtitle,
            bg=card_bg,
            fg=text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=panel_w - 140,
            justify=tk.LEFT,
        ).pack(anchor="nw")

    def draw_prev_square(c: tk.Canvas, cx: int, cy: int) -> None:
        h = 22
        c.create_rectangle(cx - h, cy - h, cx + h, cy + h, fill=COL_SQUARE, outline=OUTLINE, width=2)

    def draw_prev_rect(c: tk.Canvas, cx: int, cy: int) -> None:
        c.create_rectangle(cx - 28, cy - 14, cx + 28, cy + 14, fill=COL_RECT, outline=OUTLINE, width=2)

    def draw_prev_tri(c: tk.Canvas, cx: int, cy: int) -> None:
        c.create_polygon(
            cx,
            cy - 24,
            cx - 26,
            cy + 18,
            cx + 26,
            cy + 18,
            fill=COL_TRI,
            outline=OUTLINE,
            width=2,
        )

    make_palette_row("Kare", "Eş kenarlı dörtgen", "square", draw_prev_square)
    make_palette_row("Dikdörtgen", "Geniş dikdörtgen", "rect", draw_prev_rect)
    make_palette_row("Üçgen", "Üç köşeli şekil", "triangle", draw_prev_tri)

    canvas.bind("<Configure>", on_resize)
    canvas.bind("<Button-1>", on_canvas_left_down)
    canvas.bind("<B1-Motion>", on_canvas_left_motion)
    canvas.bind("<ButtonRelease-1>", on_canvas_left_up)
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

    root.bind("<Escape>", cancel_palette_escape)
    canvas.bind("<Enter>", lambda _e: canvas.focus_set())

    root.after_idle(on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
