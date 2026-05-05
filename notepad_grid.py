#!/usr/bin/env python3
"""
SLD App — kareli dünya; şekiller, tutamaçlar ve şekiller arası bağlantı çizgileri.

Tkinter standart kütüphanedir (pip gerekmez).

Etkileşim:
  Şekiller menüsünden sürükleyip bırak → şekil eklenir
  Köşe ve kenar ortası tutamaçlarından birine tıkla, başka tutamağa tıkla → çizgi bağlar
  Esc → bağlantı önizlemesini iptal
  Çizgiye sol tık → seçili vurgu (turuncu)
  Çizgiye sağ tık → Düz çizgi / Yay menüsü; yayda yay gövdesini sürükleyerek eğriyi ayarla
  Yerleşik şekil dolgu alanında sol sürükle → şekli taşı
  Ctrl veya orta fare + sürükle → pan | Tekerlek → yakınlaştır | Shift/Ctrl + tekerlek → kaydır
  Üst çubukta Merkezle → görünümü ortalar

Çalıştırma: python notepad_grid.py
"""

from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import Menu


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


def _circle_through_three(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float] | None:
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    return ux, uy, r


def _tk_angle_deg(ox: float, oy: float, px: float, py: float) -> float:
    """Tk canvas ile uyumlu: 0 doğu, pozitif saat yönü (ekran, +y aşağı)."""
    return math.degrees(math.atan2(-(py - oy), px - ox))


def _arc_geometry(
    mx: float,
    my: float,
    nx: float,
    ny: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float, float, float] | None:
    """ox, oy, r, start_deg (Tk), extent_deg (Tk)."""
    circ = _circle_through_three(mx, my, nx, ny, cx, cy)
    if circ is None:
        return None
    ox, oy, r = circ
    am = _tk_angle_deg(ox, oy, mx, my)
    an = _tk_angle_deg(ox, oy, nx, ny)
    ac = _tk_angle_deg(ox, oy, cx, cy)

    def norm360(a: float) -> float:
        while a < 0:
            a += 360.0
        while a >= 360:
            a -= 360.0
        return a

    def on_positive_sweep(start: float, extent: float, ap: float) -> bool:
        if extent >= 0:
            da = norm360(ap - start)
            return da <= extent + 0.5 or extent >= 360 - 1e-6
        da = norm360(start - ap)
        return da <= -extent + 0.5

    # İki yay adayı: kısa ve uzun
    d_ccw = norm360(an - am)
    if d_ccw <= 180:
        ext_ccw = d_ccw
        ext_cw = d_ccw - 360
    else:
        ext_ccw = d_ccw - 360
        ext_cw = d_ccw

    on_ccw = on_positive_sweep(am, ext_ccw, ac)
    on_cw = on_positive_sweep(am, ext_cw, ac)

    if on_ccw and not on_cw:
        start, extent = am, ext_ccw
    elif on_cw and not on_ccw:
        start, extent = am, ext_cw
    elif on_ccw and on_cw:
        start, extent = am, ext_ccw
    else:
        start, extent = am, ext_ccw if abs(ext_ccw) <= abs(ext_cw) else ext_cw

    return ox, oy, r, start, extent


def _arc_canvas_params(
    mx: float,
    my: float,
    nx: float,
    ny: float,
    cx: float,
    cy: float,
    scroll_x: float,
    scroll_y: float,
    zoom: float,
) -> tuple[float, float, float, float, float, float] | None:
    g = _arc_geometry(mx, my, nx, ny, cx, cy)
    if g is None:
        return None
    ox, oy, r, start, extent = g
    x0 = (ox - r - scroll_x) * zoom
    y0 = (oy - r - scroll_y) * zoom
    x1 = (ox + r - scroll_x) * zoom
    y1 = (oy + r - scroll_y) * zoom
    return x0, y0, x1, y1, start, extent


def _dist_point_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab2 = abx * abx + aby * aby
    if ab2 < 1e-18:
        return math.hypot(apx, apy)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    qx = ax + t * abx
    qy = ay + t * aby
    return math.hypot(px - qx, py - qy)


def _point_on_arc_tk(
    px: float,
    py: float,
    ox: float,
    oy: float,
    r: float,
    start: float,
    extent: float,
) -> bool:
    pr = math.hypot(px - ox, py - oy)
    if abs(pr - r) > max(3.0, r * 0.05):
        return False
    ap = _tk_angle_deg(ox, oy, px, py)

    def norm360(a: float) -> float:
        while a < 0:
            a += 360.0
        while a >= 360:
            a -= 360.0
        return a

    if extent >= 0:
        da = norm360(ap - start)
        return da <= extent + 1.0 or extent >= 359.5
    da = norm360(start - ap)
    return da <= -extent + 1.0


def _dist_point_arc(
    mx: float,
    my: float,
    nx: float,
    ny: float,
    cx: float,
    cy: float,
    px: float,
    py: float,
) -> float:
    g = _arc_geometry(mx, my, nx, ny, cx, cy)
    if g is None:
        return _dist_point_segment(px, py, mx, my, nx, ny)
    ox, oy, r, start, extent = g
    if _point_on_arc_tk(px, py, ox, oy, r, start, extent):
        pr = math.hypot(px - ox, py - oy)
        return abs(pr - r)
    return min(math.hypot(px - mx, py - my), math.hypot(px - nx, py - ny))


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
    edges: list[dict[str, float | int | tuple[int, int]]] = []
    next_edge_id = 1
    selected_edge_id: int | None = None
    connecting_from: tuple[int, int] | None = None
    preview_wx: float | None = None
    preview_wy: float | None = None
    dragging_arc_edge_id: int | None = None
    drag_arc_off_x = 0.0
    drag_arc_off_y = 0.0

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
    shapes_menu_open = False

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("1000x640")
    root.minsize(480, 240)

    bar_bg = "#f8fafc"
    bar_bd = "#e2e8f0"
    popup_bg = "#ffffff"
    muted = "#64748b"
    ink = "#0f172a"

    body = tk.Frame(root)
    body.pack(fill=tk.BOTH, expand=True)

    topbar = tk.Frame(body, bg=bar_bg, highlightthickness=1, highlightbackground=bar_bd)
    topbar.pack(fill=tk.X)

    left_head = tk.Frame(topbar, bg=bar_bg)
    left_head.pack(side=tk.LEFT, padx=(14, 10), pady=10)

    hint_var = tk.StringVar(value="")

    def toggle_shapes_menu() -> None:
        nonlocal shapes_menu_open
        shapes_menu_open = not shapes_menu_open
        if shapes_menu_open:
            position_shapes_popup()
            shapes_popup.lift()
            shapes_toggle.configure(text="Şekiller  ▲")
        else:
            shapes_popup.place_forget()
            shapes_toggle.configure(text="Şekiller  ▼")
            hint_var.set("")

    shapes_toggle = tk.Button(
        left_head,
        text="Şekiller  ▼",
        command=toggle_shapes_menu,
        cursor="hand2",
        relief=tk.FLAT,
        bg=bar_bg,
        fg=ink,
        activebackground="#f1f5f9",
        activeforeground=ink,
        font=("Segoe UI", 10, "bold"),
        bd=0,
        padx=10,
        pady=6,
        highlightthickness=1,
        highlightbackground=bar_bd,
    )
    shapes_toggle.pack(side=tk.LEFT)

    tk.Label(
        left_head,
        textvariable=hint_var,
        bg=bar_bg,
        fg=muted,
        font=("Segoe UI", 9),
    ).pack(side=tk.LEFT, padx=(18, 0))

    tk.Button(
        topbar,
        text="Merkezle",
        command=lambda: center_on_shapes(),
        cursor="hand2",
        relief=tk.FLAT,
        bg="#ffffff",
        fg=ink,
        activebackground="#f1f5f9",
        activeforeground=ink,
        font=("Segoe UI", 9),
        bd=0,
        padx=14,
        pady=6,
        highlightthickness=1,
        highlightbackground=bar_bd,
    ).pack(side=tk.RIGHT, padx=(8, 14), pady=10)

    canvas_holder = tk.Frame(body)
    canvas_holder.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(canvas_holder, highlightthickness=0, bg=bg, cursor="crosshair")
    canvas.pack(fill=tk.BOTH, expand=True)

    shapes_popup = tk.Frame(
        root,
        bg=popup_bg,
        highlightthickness=1,
        highlightbackground=bar_bd,
        padx=14,
        pady=14,
    )

    def position_shapes_popup() -> None:
        root.update_idletasks()
        bx = shapes_toggle.winfo_rootx() - root.winfo_rootx()
        by = shapes_toggle.winfo_rooty() - root.winfo_rooty() + shapes_toggle.winfo_height() + 6
        shapes_popup.place(x=bx, y=by)

    def close_shapes_menu() -> None:
        nonlocal shapes_menu_open
        if not shapes_menu_open:
            return
        shapes_menu_open = False
        shapes_popup.place_forget()
        shapes_toggle.configure(text="Şekiller  ▼")
        hint_var.set("")

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

    def hit_edge(sx: int, sy: int) -> int | None:
        wx, wy = screen_to_world(sx, sy)
        thr = 10.0 / zoom
        best: int | None = None
        best_d = thr + 1.0
        for e in edges:
            eid = int(e["id"])
            mx, my, nx, ny, cx, cy = edge_world_coords(e)
            if str(e["kind"]) == "line":
                d = _dist_point_segment(wx, wy, mx, my, nx, ny)
            else:
                d = _dist_point_arc(mx, my, nx, ny, cx, cy, wx, wy)
            if d < best_d and d <= thr:
                best_d = d
                best = eid
        return best

    def bbox_world() -> tuple[float, float, float, float] | None:
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
        for e in edges:
            mx, my, nx, ny, cx, cy = edge_world_coords(e)
            for px, py in ((mx, my), (nx, ny), (cx, cy)):
                min_x = min(min_x, px)
                max_x = max(max_x, px)
                min_y = min(min_y, py)
                max_y = max(max_y, py)
        if min_x == float("inf"):
            return None
        return min_x, min_y, max_x, max_y

    def iter_handles(si: int) -> list[tuple[str, int, float, float]]:
        """Her öğe: role ('corner'|'mid'), index, wx, wy."""
        s = shapes[si]
        k = str(s["kind"])
        cx = float(s["cx"])
        cy = float(s["cy"])
        out: list[tuple[str, int, float, float]] = []
        if k == "square":
            h = float(s["half"])
            pts = [
                (cx - h, cy - h),
                (cx + h, cy - h),
                (cx + h, cy + h),
                (cx - h, cy + h),
            ]
            for i, (px, py) in enumerate(pts):
                out.append(("corner", i, px, py))
            mids = [
                (cx, cy - h),
                (cx + h, cy),
                (cx, cy + h),
                (cx - h, cy),
            ]
            for i, (px, py) in enumerate(mids):
                out.append(("mid", i, px, py))
        elif k == "rect":
            hw = float(s["hw"])
            hh = float(s["hh"])
            pts = [
                (cx - hw, cy - hh),
                (cx + hw, cy - hh),
                (cx + hw, cy + hh),
                (cx - hw, cy + hh),
            ]
            for i, (px, py) in enumerate(pts):
                out.append(("corner", i, px, py))
            mids = [
                (cx, cy - hh),
                (cx + hw, cy),
                (cx, cy + hh),
                (cx - hw, cy),
            ]
            for i, (px, py) in enumerate(mids):
                out.append(("mid", i, px, py))
        else:
            vs = _tri_vertices(s)
            for i, (px, py) in enumerate(vs):
                out.append(("corner", i, px, py))
            for i in range(3):
                ax, ay = vs[i]
                bx, by = vs[(i + 1) % 3]
                out.append(("mid", i, (ax + bx) / 2.0, (ay + by) / 2.0))
        return out

    def handle_hit_world(wx: float, wy: float) -> tuple[int, str, int] | None:
        r = 12.0 / zoom
        best: tuple[int, str, int] | None = None
        best_d = r + 1.0
        for si in range(len(shapes)):
            for role, idx, hx, hy in iter_handles(si):
                d = math.hypot(wx - hx, wy - hy)
                if d < best_d and d <= r:
                    best_d = d
                    best = (si, role, idx)
        return best

    def edge_anchor_world(si: int, role: str, idx: int) -> tuple[float, float]:
        for r, i, wx, wy in iter_handles(si):
            if r == role and i == idx:
                return wx, wy
        return 0.0, 0.0

    def edge_world_coords(e: dict[str, float | int | tuple[int, int]]) -> tuple[float, float, float, float, float, float]:
        """mx,my,nx,ny,cx,cy"""
        a = e["a"]
        b = e["b"]
        assert isinstance(a, tuple) and isinstance(b, tuple)
        si_a, role_a, idx_a = a
        si_b, role_b, idx_b = b
        mx, my = edge_anchor_world(si_a, role_a, idx_a)
        nx, ny = edge_anchor_world(si_b, role_b, idx_b)
        cx = float(e["cx"])
        cy = float(e["cy"])
        return mx, my, nx, ny, cx, cy

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

    def draw_edges_layer() -> None:
        z = zoom
        for e in edges:
            eid = int(e["id"])
            sel = selected_edge_id == eid
            lw = max(2, int(round((4 if sel else 2) * min(z, 2))))
            col = "#f59e0b" if sel else "#475569"
            mx, my, nx, ny, cx, cy = edge_world_coords(e)
            if str(e["kind"]) == "line":
                sx0 = (mx - scroll_x) * z
                sy0 = (my - scroll_y) * z
                sx1 = (nx - scroll_x) * z
                sy1 = (ny - scroll_y) * z
                canvas.create_line(sx0, sy0, sx1, sy1, fill=col, width=lw, capstyle=tk.ROUND)
            else:
                prms = _arc_canvas_params(mx, my, nx, ny, cx, cy, scroll_x, scroll_y, z)
                if prms is None:
                    sx0 = (mx - scroll_x) * z
                    sy0 = (my - scroll_y) * z
                    sx1 = (nx - scroll_x) * z
                    sy1 = (ny - scroll_y) * z
                    canvas.create_line(sx0, sy0, sx1, sy1, fill=col, width=lw, capstyle=tk.ROUND)
                else:
                    x0, y0, x1, y1, st, ext = prms
                    canvas.create_arc(
                        x0,
                        y0,
                        x1,
                        y1,
                        start=st,
                        extent=ext,
                        style=tk.ARC,
                        outline=col,
                        width=lw,
                    )

    def draw_handles_layer() -> None:
        z = zoom
        rh = max(3.0, 5.0 * min(z, 1.5))
        for si in range(len(shapes)):
            for _role, _idx, wx, wy in iter_handles(si):
                sx = (wx - scroll_x) * z
                sy = (wy - scroll_y) * z
                canvas.create_oval(
                    sx - rh,
                    sy - rh,
                    sx + rh,
                    sy + rh,
                    fill="#ffffff",
                    outline="#64748b",
                    width=max(1, int(round(2 * min(z, 1.2)))),
                )

    def draw_preview_connector() -> None:
        if connecting_from is None or preview_wx is None or preview_wy is None:
            return
        z = zoom
        si, role, idx = connecting_from
        wx0, wy0 = edge_anchor_world(si, role, idx)
        sx0 = (wx0 - scroll_x) * z
        sy0 = (wy0 - scroll_y) * z
        sx1 = (preview_wx - scroll_x) * z
        sy1 = (preview_wy - scroll_y) * z
        canvas.create_line(
            sx0,
            sy0,
            sx1,
            sy1,
            fill="#94a3b8",
            width=max(1, int(round(2 * z))),
            dash=(6, 4),
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

        draw_edges_layer()

        for si, s in enumerate(shapes):
            draw_shape_ui(s)

        draw_handles_layer()
        draw_preview_connector()

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
        close_shapes_menu()
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

    line_menu: tk.Menu | None = None

    def set_edge_line(eid: int) -> None:
        for e in edges:
            if int(e["id"]) == eid:
                e["kind"] = "line"
                mx, my, nx, ny, _, _ = edge_world_coords(e)
                e["cx"] = (mx + nx) / 2.0
                e["cy"] = (my + ny) / 2.0
                break
        redraw()

    def set_edge_arc(eid: int) -> None:
        for e in edges:
            if int(e["id"]) == eid:
                e["kind"] = "arc"
                mx, my, nx, ny, _, _ = edge_world_coords(e)
                dx = nx - mx
                dy = ny - my
                ln = math.hypot(dx, dy)
                if ln < 1e-9:
                    e["cx"] = (mx + nx) / 2.0
                    e["cy"] = (my + ny) / 2.0 - 20.0
                else:
                    px = -dy / ln * 24.0
                    py = dx / ln * 24.0
                    e["cx"] = (mx + nx) / 2.0 + px
                    e["cy"] = (my + ny) / 2.0 + py
                break
        redraw()

    def show_edge_menu(event: tk.Event, eid: int) -> None:
        nonlocal line_menu
        if line_menu is not None:
            try:
                line_menu.destroy()
            except tk.TclError:
                pass
        line_menu = tk.Menu(canvas, tearoff=0)
        line_menu.add_command(label="Düz çizgi", command=lambda: set_edge_line(eid))
        line_menu.add_command(label="Yay (arc)", command=lambda: set_edge_arc(eid))
        try:
            line_menu.tk_popup(event.x_root, event.y_root)
        finally:
            line_menu.grab_release()

    def hit_arc_body_for_drag(sx: int, sy: int) -> int | None:
        wx, wy = screen_to_world(sx, sy)
        thr = 10.0 / zoom
        end_thr = max(14.0 / zoom, 8.0)
        best: int | None = None
        best_d = thr + 1.0
        for e in edges:
            if str(e["kind"]) != "arc":
                continue
            eid = int(e["id"])
            mx, my, nx, ny, cx, cy = edge_world_coords(e)
            if math.hypot(wx - mx, wy - my) <= end_thr or math.hypot(wx - nx, wy - ny) <= end_thr:
                continue
            d = _dist_point_arc(mx, my, nx, ny, cx, cy, wx, wy)
            if d < best_d and d <= thr:
                best_d = d
                best = eid
        return best

    def on_canvas_left_down(event: tk.Event) -> None:
        nonlocal dragging_shape_idx, drag_off_x, drag_off_y
        nonlocal connecting_from, preview_wx, preview_wy
        nonlocal selected_edge_id, dragging_arc_edge_id, drag_arc_off_x, drag_arc_off_y
        nonlocal next_edge_id
        close_shapes_menu()
        if palette_drag_kind is not None:
            return
        if event.state & 0x4:
            return

        aid = hit_arc_body_for_drag(event.x, event.y)
        if aid is not None:
            dragging_arc_edge_id = aid
            wx, wy = screen_to_world(event.x, event.y)
            for e in edges:
                if int(e["id"]) == aid:
                    drag_arc_off_x = wx - float(e["cx"])
                    drag_arc_off_y = wy - float(e["cy"])
                    selected_edge_id = aid
                    break
            return

        eid_hit = hit_edge(event.x, event.y)
        if eid_hit is not None:
            selected_edge_id = eid_hit
            redraw()
            return

        hh = handle_hit_world(*screen_to_world(event.x, event.y))
        if hh is not None:
            si, role, idx = hh
            if connecting_from is None:
                connecting_from = (si, role, idx)
                preview_wx, preview_wy = screen_to_world(event.x, event.y)
            else:
                fa, fra, fi = connecting_from
                if fa == si and fra == role and fi == idx:
                    connecting_from = None
                    preview_wx = preview_wy = None
                    redraw()
                    return
                mx, my = edge_anchor_world(fa, fra, fi)
                nx, ny = edge_anchor_world(si, role, idx)
                edges.append(
                    {
                        "id": next_edge_id,
                        "kind": "line",
                        "a": connecting_from,
                        "b": (si, role, idx),
                        "cx": (mx + nx) / 2.0,
                        "cy": (my + ny) / 2.0,
                    }
                )
                next_edge_id += 1
                connecting_from = None
                preview_wx = preview_wy = None
                selected_edge_id = None
            redraw()
            return

        idx_shape = hit_top_shape(event.x, event.y)
        if idx_shape is not None:
            connecting_from = None
            preview_wx = preview_wy = None
            dragging_shape_idx = idx_shape
            wx, wy = screen_to_world(event.x, event.y)
            drag_off_x = wx - float(shapes[idx_shape]["cx"])
            drag_off_y = wy - float(shapes[idx_shape]["cy"])
            canvas.config(cursor="hand2")
            return

        connecting_from = None
        preview_wx = preview_wy = None
        selected_edge_id = None
        redraw()

    def on_canvas_left_motion(event: tk.Event) -> None:
        nonlocal dragging_shape_idx, preview_wx, preview_wy
        nonlocal dragging_arc_edge_id
        if dragging_arc_edge_id is not None:
            wx, wy = screen_to_world(event.x, event.y)
            for e in edges:
                if int(e["id"]) == dragging_arc_edge_id:
                    e["cx"] = wx - drag_arc_off_x
                    e["cy"] = wy - drag_arc_off_y
                    break
            redraw()
            return
        if connecting_from is not None:
            preview_wx, preview_wy = screen_to_world(event.x, event.y)
            redraw()
            return
        if dragging_shape_idx is None:
            return
        wx, wy = screen_to_world(event.x, event.y)
        i = dragging_shape_idx
        shapes[i]["cx"] = wx - drag_off_x
        shapes[i]["cy"] = wy - drag_off_y
        redraw()

    def on_canvas_left_up(_event: tk.Event | None = None) -> None:
        nonlocal dragging_shape_idx, dragging_arc_edge_id
        dragging_shape_idx = None
        dragging_arc_edge_id = None
        canvas.config(cursor="crosshair")

    def on_canvas_right(event: tk.Event) -> None:
        nonlocal selected_edge_id
        eid_hit = hit_edge(event.x, event.y)
        if eid_hit is None:
            return
        selected_edge_id = eid_hit
        redraw()
        show_edge_menu(event, eid_hit)

    def on_canvas_motion_hover(event: tk.Event) -> None:
        nonlocal preview_wx, preview_wy
        if connecting_from is None:
            return
        preview_wx, preview_wy = screen_to_world(event.x, event.y)
        redraw()

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
        nonlocal palette_drag_kind, connecting_from, preview_wx, preview_wy
        if palette_drag_kind is None and connecting_from is None:
            return
        root.unbind_all("<B1-Motion>")
        root.unbind_all("<ButtonRelease-1>")
        palette_drag_kind = None
        connecting_from = None
        preview_wx = preview_wy = None
        hide_ghost()
        redraw()

    def make_palette_tile(title: str, subtitle: str, hint: str, kind: str, draw_fn) -> None:
        row = tk.Frame(shapes_popup, bg=popup_bg)
        row.pack(fill=tk.X, pady=(0, 12))

        preview_wrap = tk.Frame(
            row,
            bg="#f8fafc",
            highlightthickness=1,
            highlightbackground=bar_bd,
            highlightcolor=bar_bd,
        )
        preview_wrap.pack(side=tk.LEFT)
        cv = tk.Canvas(
            preview_wrap,
            width=64,
            height=64,
            bg="#f8fafc",
            highlightthickness=0,
            cursor="hand2",
        )
        cv.pack(padx=8, pady=8)
        draw_fn(cv, 32, 32)
        cv.bind("<ButtonPress-1>", lambda _e, k=kind: palette_press(k))
        cv.bind("<Enter>", lambda _e, h=hint: hint_var.set(h))
        cv.bind("<Leave>", lambda _e: hint_var.set(""))

        col = tk.Frame(row, bg=popup_bg)
        col.pack(side=tk.LEFT, padx=(12, 0), fill=tk.Y)
        tk.Label(
            col,
            text=title,
            bg=popup_bg,
            fg=ink,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(anchor="nw")
        tk.Label(
            col,
            text=subtitle,
            bg=popup_bg,
            fg=muted,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=200,
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

    make_palette_tile(
        "Kare",
        "Eş kenarlı dörtgen",
        "Tuval üzerine kare yerleştirir.",
        "square",
        draw_prev_square,
    )
    make_palette_tile(
        "Dikdörtgen",
        "Yatay dikdörtgen",
        "Tuval üzerine dikdörtgen yerleştirir.",
        "rect",
        draw_prev_rect,
    )
    make_palette_tile(
        "Üçgen",
        "Üç köşe",
        "Tuval üzerine üçgen yerleştirir.",
        "triangle",
        draw_prev_tri,
    )

    canvas.bind("<Configure>", on_resize)
    canvas.bind("<Button-1>", on_canvas_left_down)
    canvas.bind("<B1-Motion>", on_canvas_left_motion)
    canvas.bind("<ButtonRelease-1>", on_canvas_left_up)
    canvas.bind("<Motion>", on_canvas_motion_hover)
    canvas.bind("<Button-3>", on_canvas_right)
    canvas.bind("<Control-Button-1>", pan_start)
    canvas.bind("<Control-B1-Motion>", pan_motion)
    canvas.bind("<Control-ButtonRelease-1>", pan_end)
    canvas.bind("<Button-2>", pan_start)
    canvas.bind("<B2-Motion>", pan_motion)
    canvas.bind("<ButtonRelease-2>", pan_end)

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
