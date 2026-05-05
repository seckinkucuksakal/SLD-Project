"""SLD App Tk arayüzü — durum ve olay döngüsü."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import Menu

from sld_app import constants as C
from sld_app import geometry
from sld_app.platform_win import apply_windows_dpi_awareness


def run() -> None:
    apply_windows_dpi_awareness()


    cell = C.CELL
    bg = C.BG
    grid_color = C.GRID_COLOR
    block_pad = C.BLOCK_PAD

    shapes: list[dict[str, float | str]] = []
    edges: list[dict[str, float | int | tuple[int, int]]] = []
    next_edge_id = 1
    selected_edge_id: int | None = None
    connecting_from: tuple[int, int] | None = None
    preview_wx: float | None = None
    preview_wy: float | None = None
    dragging_arc_edge_id: int | None = None
    arc_drag_base_cx = 0.0
    arc_drag_base_cy = 0.0
    arc_drag_ptr_x = 0.0
    arc_drag_ptr_y = 0.0

    scroll_x = 0.0
    scroll_y = 0.0
    zoom = 1.0
    dragging_shape_idx: int | None = None
    drag_off_x = 0.0
    drag_off_y = 0.0
    shape_drag_ortho_anchor: tuple[float, float] | None = None
    shape_group_origin: dict[int, tuple[float, float]] | None = None
    pan_anchor: tuple[int, int, float, float] | None = None

    ortho_mode = False
    palette_drag_kind: str | None = None
    ghost_win: tk.Toplevel | None = None
    shapes_menu_open = False

    selected_shape_indices: set[int] = set()
    marquee_active = False
    marquee_ax = 0
    marquee_ay = 0
    marquee_cur_x = 0
    marquee_cur_y = 0

    root = tk.Tk()
    root.title("SLD App")
    root.geometry("1000x640")
    root.minsize(480, 240)

    bar_bg = C.BAR_BG
    bar_bd = C.BAR_BD
    popup_bg = C.POPUP_BG
    muted = C.TEXT_MUTED
    ink = C.TEXT_INK

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

    def toggle_ortho() -> None:
        nonlocal ortho_mode
        ortho_mode = not ortho_mode
        _sync_ortho_btn()

    ortho_btn = tk.Button(
        topbar,
        text="ORTHO",
        command=toggle_ortho,
        cursor="hand2",
        relief=tk.FLAT,
        bg="#ffffff",
        fg=ink,
        activebackground="#f1f5f9",
        activeforeground=ink,
        font=("Segoe UI", 9, "bold"),
        bd=0,
        padx=12,
        pady=6,
        highlightthickness=1,
        highlightbackground=bar_bd,
    )
    ortho_btn.pack(side=tk.RIGHT, padx=(8, 0), pady=10)

    def _sync_ortho_btn() -> None:
        if ortho_mode:
            ortho_btn.configure(bg="#dcfce7", fg="#166534", highlightbackground="#86efac")
        else:
            ortho_btn.configure(bg="#ffffff", fg=ink, highlightbackground=bar_bd)

    _sync_ortho_btn()

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
        ax, ay = geometry.tri_vertices(s)[0]
        bx, by = geometry.tri_vertices(s)[1]
        cxp, cyp = geometry.tri_vertices(s)[2]
        return geometry.point_in_triangle(mx, my, ax, ay, bx, by, cxp, cyp)

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
                d = geometry.dist_point_segment(wx, wy, mx, my, nx, ny)
            else:
                d = geometry.dist_point_arc(mx, my, nx, ny, cx, cy, wx, wy)
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
                for px, py in geometry.tri_vertices(s):
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

    def shape_bbox_world(si: int) -> tuple[float, float, float, float]:
        s = shapes[si]
        k = str(s["kind"])
        cx = float(s["cx"])
        cy = float(s["cy"])
        if k == "square":
            h = float(s["half"])
            return cx - h, cy - h, cx + h, cy + h
        if k == "rect":
            hw = float(s["hw"])
            hh = float(s["hh"])
            return cx - hw, cy - hh, cx + hw, cy + hh
        xs = [p[0] for p in geometry.tri_vertices(s)]
        ys = [p[1] for p in geometry.tri_vertices(s)]
        return min(xs), min(ys), max(xs), max(ys)

    def rects_overlap_world(
        ax0: float,
        ay0: float,
        ax1: float,
        ay1: float,
        bx0: float,
        by0: float,
        bx1: float,
        by1: float,
    ) -> bool:
        return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)

    def shapes_in_marquee_world(wx0: float, wy0: float, wx1: float, wy1: float) -> set[int]:
        mx0, mx1 = min(wx0, wx1), max(wx0, wx1)
        my0, my1 = min(wy0, wy1), max(wy0, wy1)
        out: set[int] = set()
        for si in range(len(shapes)):
            bx0, by0, bx1, by1 = shape_bbox_world(si)
            if rects_overlap_world(mx0, my0, mx1, my1, bx0, by0, bx1, by1):
                out.add(si)
        return out

    def delete_selected_shapes() -> None:
        nonlocal shapes, edges, next_edge_id, selected_edge_id
        nonlocal selected_shape_indices
        if not selected_shape_indices:
            return
        keep_old = set(selected_shape_indices)
        shapes = [s for i, s in enumerate(shapes) if i not in selected_shape_indices]

        def remap(si: int) -> int:
            c = 0
            for i in range(si):
                if i not in keep_old:
                    c += 1
            return c

        def remap_handle(h: tuple[int, str, int]) -> tuple[int, str, int] | None:
            si, role, idx = h
            if si in keep_old:
                return None
            return remap(si), role, idx

        new_edges: list[dict[str, float | int | tuple[int, int]]] = []
        max_id = 0
        for e in edges:
            a = e["a"]
            b = e["b"]
            assert isinstance(a, tuple) and isinstance(b, tuple)
            na = remap_handle(a)
            nb = remap_handle(b)
            if na is None or nb is None:
                continue
            ne = dict(e)
            ne["a"] = na
            ne["b"] = nb
            new_edges.append(ne)
            max_id = max(max_id, int(e["id"]))
        edges = new_edges
        next_edge_id = max(next_edge_id, max_id + 1)
        selected_edge_id = None
        selected_shape_indices = set()
        redraw()

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
            vs = geometry.tri_vertices(s)
            for i, (px, py) in enumerate(vs):
                out.append(("corner", i, px, py))
            for i in range(3):
                ax, ay = vs[i]
                bx, by = vs[(i + 1) % 3]
                out.append(("mid", i, (ax + bx) / 2.0, (ay + by) / 2.0))
        return out

    def handle_hit_world(wx: float, wy: float) -> tuple[int, str, int] | None:
        r = 7.0 / zoom
        best: tuple[int, str, int] | None = None
        best_d = r + 1.0
        for si in range(len(shapes)):
            if connecting_from is None and si not in selected_shape_indices:
                continue
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
                fill=C.COL_SQUARE,
                outline=ol,
                width=ow,
            )
        elif kind == "rect":
            c.create_rectangle(
                cx - 28,
                cy - 14,
                cx + 28,
                cy + 14,
                fill=C.COL_RECT,
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
                fill=C.COL_TRI,
                outline=ol,
                width=ow,
            )

    def show_ghost(kind: str) -> None:
        nonlocal ghost_win
        hide_ghost()
        ghost_win = tk.Toplevel(root)
        ghost_win.overrideredirect(True)
        ghost_win.attributes("-topmost", True)
        ghost_canvas_bg = C.TRANSP_GHOST
        try:
            ghost_win.attributes("-transparentcolor", C.TRANSP_GHOST)
        except tk.TclError:
            ghost_canvas_bg = "#ffffff"
        gc = tk.Canvas(
            ghost_win,
            width=C.GHOST_WH,
            height=C.GHOST_WH,
            bg=ghost_canvas_bg,
            highlightthickness=0,
        )
        gc.pack()
        draw_ghost_preview(gc, kind, C.GHOST_WH // 2, C.GHOST_WH // 2)
        rx, ry = root.winfo_pointerxy()
        ghost_win.geometry(
            f"{C.GHOST_WH}x{C.GHOST_WH}+{rx - C.GHOST_WH // 2}+{ry - C.GHOST_WH // 2}"
        )

    def palette_motion(_event: tk.Event | None = None) -> None:
        if palette_drag_kind is None or ghost_win is None:
            return
        rx, ry = root.winfo_pointerxy()
        ghost_win.geometry(
            f"{C.GHOST_WH}x{C.GHOST_WH}+{rx - C.GHOST_WH // 2}+{ry - C.GHOST_WH // 2}"
        )

    def screen_to_world(sx: int, sy: int) -> tuple[float, float]:
        return scroll_x + float(sx) / zoom, scroll_y + float(sy) / zoom

    def ortho_snap(from_x: float, from_y: float, to_x: float, to_y: float) -> tuple[float, float]:
        if not ortho_mode:
            return to_x, to_y
        dx = to_x - from_x
        dy = to_y - from_y
        if abs(dx) >= abs(dy):
            return to_x, from_y
        return from_x, to_y

    def outline_w() -> int:
        return max(1, int(round(2 * zoom / max(zoom, 0.25))))

    def draw_shape_ui(s: dict[str, float | str], si: int) -> None:
        z = zoom
        k = str(s["kind"])
        ox = outline_w()
        sel = si in selected_shape_indices
        outline_col = C.SELECTION_OUTLINE if sel else C.OUTLINE
        ow = ox + (1 if sel else 0)
        if k == "square":
            bx = (float(s["cx"]) - scroll_x) * z
            by = (float(s["cy"]) - scroll_y) * z
            hs = float(s["half"]) * z
            canvas.create_rectangle(
                bx - hs,
                by - hs,
                bx + hs,
                by + hs,
                fill=C.COL_SQUARE,
                outline=outline_col,
                width=ow,
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
                fill=C.COL_RECT,
                outline=outline_col,
                width=ow,
            )
        else:
            pts: list[float] = []
            for px, py in geometry.tri_vertices(s):
                pts.append((px - scroll_x) * z)
                pts.append((py - scroll_y) * z)
            canvas.create_polygon(*pts, fill=C.COL_TRI, outline=outline_col, width=ow)

    def draw_selection_boxes() -> None:
        z = zoom
        dash_len = max(3, int(round(4 * min(z, 1.2))))
        gap = max(2, int(round(3 * min(z, 1.2))))
        for si in selected_shape_indices:
            bx0, by0, bx1, by1 = shape_bbox_world(si)
            sx0 = (bx0 - scroll_x) * z
            sy0 = (by0 - scroll_y) * z
            sx1 = (bx1 - scroll_x) * z
            sy1 = (by1 - scroll_y) * z
            canvas.create_rectangle(
                sx0,
                sy0,
                sx1,
                sy1,
                outline=C.SELECTION_OUTLINE,
                width=max(1, int(round(1.5 * min(z, 1.5)))),
                dash=(dash_len, gap),
            )

    def draw_marquee_rect() -> None:
        if not marquee_active:
            return
        x0 = min(marquee_ax, marquee_cur_x)
        y0 = min(marquee_ay, marquee_cur_y)
        x1 = max(marquee_ax, marquee_cur_x)
        y1 = max(marquee_ay, marquee_cur_y)
        canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            outline=C.MARQUEE_COLOR,
            width=1,
            dash=(5, 4),
        )

    def draw_edges_layer() -> None:
        z = zoom
        for e in edges:
            eid = int(e["id"])
            sel = selected_edge_id == eid
            lw = max(2, int(round((4 if sel else 2) * min(z, 2))))
            col = C.EDGE_SELECTED if sel else C.EDGE_COLOR
            mx, my, nx, ny, cx, cy = edge_world_coords(e)
            if str(e["kind"]) == "line":
                sx0 = (mx - scroll_x) * z
                sy0 = (my - scroll_y) * z
                sx1 = (nx - scroll_x) * z
                sy1 = (ny - scroll_y) * z
                canvas.create_line(sx0, sy0, sx1, sy1, fill=col, width=lw, capstyle=tk.ROUND)
            else:
                prms = geometry.arc_canvas_params(mx, my, nx, ny, cx, cy, scroll_x, scroll_y, z)
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
        rh = max(2.0, 2.8 * min(z, 1.3))
        ow = max(1, int(round(1.3 * min(z, 1.1))))
        show_for: set[int] = set(selected_shape_indices)
        if connecting_from is not None:
            show_for.update(range(len(shapes)))
        if not show_for:
            return
        for si in show_for:
            if si < 0 or si >= len(shapes):
                continue
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
                    width=ow,
                )

    def draw_preview_connector() -> None:
        if connecting_from is None or preview_wx is None or preview_wy is None:
            return
        z = zoom
        si, role, idx = connecting_from
        wx0, wy0 = edge_anchor_world(si, role, idx)
        tx, ty = ortho_snap(wx0, wy0, preview_wx, preview_wy)
        sx0 = (wx0 - scroll_x) * z
        sy0 = (wy0 - scroll_y) * z
        sx1 = (tx - scroll_x) * z
        sy1 = (ty - scroll_y) * z
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
            draw_shape_ui(s, si)

        draw_selection_boxes()

        draw_handles_layer()
        draw_preview_connector()
        draw_marquee_rect()

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
        new_z = old_z * (C.ZOOM_FACTOR**delta_notches)
        new_z = max(C.ZOOM_MIN, min(C.ZOOM_MAX, new_z))
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
            d = geometry.dist_point_arc(mx, my, nx, ny, cx, cy, wx, wy)
            if d < best_d and d <= thr:
                best_d = d
                best = eid
        return best

    def on_canvas_left_down(event: tk.Event) -> None:
        nonlocal dragging_shape_idx, drag_off_x, drag_off_y
        nonlocal connecting_from, preview_wx, preview_wy
        nonlocal selected_edge_id, dragging_arc_edge_id
        nonlocal next_edge_id
        nonlocal shape_drag_ortho_anchor, shape_group_origin
        nonlocal arc_drag_base_cx, arc_drag_base_cy, arc_drag_ptr_x, arc_drag_ptr_y
        nonlocal selected_shape_indices, marquee_active
        nonlocal marquee_ax, marquee_ay, marquee_cur_x, marquee_cur_y
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
                    arc_drag_base_cx = float(e["cx"])
                    arc_drag_base_cy = float(e["cy"])
                    arc_drag_ptr_x = wx
                    arc_drag_ptr_y = wy
                    selected_edge_id = aid
                    break
            selected_shape_indices = set()
            return

        eid_hit = hit_edge(event.x, event.y)
        if eid_hit is not None:
            selected_edge_id = eid_hit
            selected_shape_indices = set()
            redraw()
            return

        hh = handle_hit_world(*screen_to_world(event.x, event.y))
        if hh is not None:
            selected_shape_indices = set()
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
            if event.state & 0x1:
                if idx_shape in selected_shape_indices:
                    selected_shape_indices.discard(idx_shape)
                else:
                    selected_shape_indices.add(idx_shape)
                selected_edge_id = None
                redraw()
                return
            wx, wy = screen_to_world(event.x, event.y)
            if idx_shape in selected_shape_indices and len(selected_shape_indices) > 1:
                shape_group_origin = {i: (float(shapes[i]["cx"]), float(shapes[i]["cy"])) for i in selected_shape_indices}
            else:
                selected_shape_indices = {idx_shape}
                shape_group_origin = None
            selected_edge_id = None
            dragging_shape_idx = idx_shape
            drag_off_x = wx - float(shapes[idx_shape]["cx"])
            drag_off_y = wy - float(shapes[idx_shape]["cy"])
            shape_drag_ortho_anchor = (
                float(shapes[idx_shape]["cx"]),
                float(shapes[idx_shape]["cy"]),
            )
            canvas.config(cursor="hand2")
            return

        connecting_from = None
        preview_wx = preview_wy = None
        selected_edge_id = None
        marquee_active = True
        marquee_ax = event.x
        marquee_ay = event.y
        marquee_cur_x = event.x
        marquee_cur_y = event.y
        if not (event.state & 0x1):
            selected_shape_indices = set()
        redraw()

    def on_canvas_left_motion(event: tk.Event) -> None:
        nonlocal dragging_shape_idx, preview_wx, preview_wy
        nonlocal dragging_arc_edge_id
        nonlocal arc_drag_base_cx, arc_drag_base_cy, arc_drag_ptr_x, arc_drag_ptr_y
        nonlocal marquee_cur_x, marquee_cur_y
        nonlocal shape_group_origin
        if marquee_active:
            marquee_cur_x = event.x
            marquee_cur_y = event.y
            redraw()
            return
        if dragging_arc_edge_id is not None:
            wx, wy = screen_to_world(event.x, event.y)
            dwx = wx - arc_drag_ptr_x
            dwy = wy - arc_drag_ptr_y
            if ortho_mode:
                if abs(dwx) >= abs(dwy):
                    dwy = 0.0
                else:
                    dwx = 0.0
            for e in edges:
                if int(e["id"]) == dragging_arc_edge_id:
                    e["cx"] = arc_drag_base_cx + dwx
                    e["cy"] = arc_drag_base_cy + dwy
                    break
            redraw()
            return
        if connecting_from is not None:
            wx, wy = screen_to_world(event.x, event.y)
            si, role, idx = connecting_from
            ax, ay = edge_anchor_world(si, role, idx)
            preview_wx, preview_wy = ortho_snap(ax, ay, wx, wy)
            redraw()
            return
        if dragging_shape_idx is None:
            return
        wx, wy = screen_to_world(event.x, event.y)
        tcx = wx - drag_off_x
        tcy = wy - drag_off_y
        i = dragging_shape_idx
        if shape_group_origin is not None:
            dx = tcx - float(shapes[i]["cx"])
            dy = tcy - float(shapes[i]["cy"])
            if ortho_mode and shape_drag_ortho_anchor is not None:
                adx, ady = ortho_snap(0.0, 0.0, dx, dy)
                dx, dy = adx, ady
            for sj, (ox, oy) in shape_group_origin.items():
                shapes[sj]["cx"] = ox + dx
                shapes[sj]["cy"] = oy + dy
        else:
            if ortho_mode and shape_drag_ortho_anchor is not None:
                tcx, tcy = ortho_snap(
                    shape_drag_ortho_anchor[0], shape_drag_ortho_anchor[1], tcx, tcy
                )
            shapes[i]["cx"] = tcx
            shapes[i]["cy"] = tcy
        redraw()

    def on_canvas_left_up(_event: tk.Event | None = None) -> None:
        nonlocal dragging_shape_idx, dragging_arc_edge_id, shape_drag_ortho_anchor
        nonlocal marquee_active, selected_shape_indices, selected_edge_id
        nonlocal shape_group_origin
        if marquee_active:
            marquee_active = False
            wx0, wy0 = screen_to_world(marquee_ax, marquee_ay)
            wx1, wy1 = screen_to_world(marquee_cur_x, marquee_cur_y)
            selected_shape_indices = shapes_in_marquee_world(wx0, wy0, wx1, wy1)
            selected_edge_id = None
            redraw()
            return
        dragging_shape_idx = None
        dragging_arc_edge_id = None
        shape_drag_ortho_anchor = None
        shape_group_origin = None
        canvas.config(cursor="crosshair")

    def on_delete_key(_event: tk.Event | None = None) -> None:
        delete_selected_shapes()

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
        wx, wy = screen_to_world(event.x, event.y)
        si, role, idx = connecting_from
        ax, ay = edge_anchor_world(si, role, idx)
        preview_wx, preview_wy = ortho_snap(ax, ay, wx, wy)
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
        canvas.config(cursor="crosshair")

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
        nonlocal selected_shape_indices, selected_edge_id, marquee_active
        selected_shape_indices = set()
        selected_edge_id = None
        marquee_active = False

        had_drag = palette_drag_kind is not None
        had_conn = connecting_from is not None
        if had_drag or had_conn:
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
        c.create_rectangle(cx - h, cy - h, cx + h, cy + h, fill=C.COL_SQUARE, outline=C.OUTLINE, width=2)

    def draw_prev_rect(c: tk.Canvas, cx: int, cy: int) -> None:
        c.create_rectangle(cx - 28, cy - 14, cx + 28, cy + 14, fill=C.COL_RECT, outline=C.OUTLINE, width=2)

    def draw_prev_tri(c: tk.Canvas, cx: int, cy: int) -> None:
        c.create_polygon(
            cx,
            cy - 24,
            cx - 26,
            cy + 18,
            cx + 26,
            cy + 18,
            fill=C.COL_TRI,
            outline=C.OUTLINE,
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
    root.bind("<Delete>", on_delete_key)
    root.bind("<BackSpace>", on_delete_key)
    canvas.bind("<Enter>", lambda _e: canvas.focus_set())

    root.after_idle(on_resize)
    root.mainloop()
