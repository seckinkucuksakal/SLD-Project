"""SLD App Tk arayüzü — durum ve olay döngüsü."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from tkinter import Menu
import tkinter.font as tkfont
import copy

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
    next_shape_label_num = 1
    edges: list[dict[str, float | int | tuple[int, int]]] = []
    next_edge_id = 1
    next_cable_num = 1
    free_lines: list[dict[str, float | int | str | tuple[int, str, int] | None]] = []
    next_free_line_id = 1
    selected_free_line_id: int | None = None

    areas: list[dict[str, float | int | str | bool]] = []
    next_area_id = 1
    selected_area_id: int | None = None
    dragging_area_id: int | None = None
    area_drag_off_x = 0.0
    area_drag_off_y = 0.0
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
    scale_mode = False
    tool_mode: str = "select"  # select | draw_free_line | area_rect | area_square | area_roundrect | area_hollow_rect | area_hollow_square
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

    undo_stack: list[dict[str, object]] = []
    UNDO_LIMIT = 80

    def _snapshot_state() -> dict[str, object]:
        return {
            "shapes": copy.deepcopy(shapes),
            "edges": copy.deepcopy(edges),
            "free_lines": copy.deepcopy(free_lines),
            "areas": copy.deepcopy(areas),
            "next_shape_label_num": next_shape_label_num,
            "next_edge_id": next_edge_id,
            "next_cable_num": next_cable_num,
            "next_free_line_id": next_free_line_id,
            "next_area_id": next_area_id,
            "selected_edge_id": selected_edge_id,
            "selected_free_line_id": selected_free_line_id,
            "selected_area_id": selected_area_id,
            "selected_shape_indices": copy.deepcopy(selected_shape_indices),
            "scroll_x": scroll_x,
            "scroll_y": scroll_y,
            "zoom": zoom,
            "ortho_mode": ortho_mode,
            "scale_mode": scale_mode,
            "tool_mode": tool_mode,
            "dragging_area_id": dragging_area_id,
            "area_drag_off_x": area_drag_off_x,
            "area_drag_off_y": area_drag_off_y,
        }

    def _restore_state(st: dict[str, object]) -> None:
        nonlocal shapes, edges, free_lines, areas
        nonlocal next_shape_label_num, next_edge_id, next_cable_num, next_free_line_id, next_area_id
        nonlocal selected_edge_id, selected_free_line_id, selected_area_id, selected_shape_indices
        nonlocal scroll_x, scroll_y, zoom, ortho_mode, scale_mode, tool_mode
        nonlocal dragging_area_id, area_drag_off_x, area_drag_off_y
        shapes = copy.deepcopy(st["shapes"])  # type: ignore[assignment]
        edges = copy.deepcopy(st["edges"])  # type: ignore[assignment]
        free_lines = copy.deepcopy(st["free_lines"])  # type: ignore[assignment]
        areas = copy.deepcopy(st["areas"])  # type: ignore[assignment]
        next_shape_label_num = int(st["next_shape_label_num"])  # type: ignore[arg-type]
        next_edge_id = int(st["next_edge_id"])  # type: ignore[arg-type]
        next_cable_num = int(st["next_cable_num"])  # type: ignore[arg-type]
        next_free_line_id = int(st["next_free_line_id"])  # type: ignore[arg-type]
        next_area_id = int(st["next_area_id"])  # type: ignore[arg-type]
        selected_edge_id = st["selected_edge_id"]  # type: ignore[assignment]
        selected_free_line_id = st["selected_free_line_id"]  # type: ignore[assignment]
        selected_area_id = st["selected_area_id"]  # type: ignore[assignment]
        selected_shape_indices = set(st["selected_shape_indices"])  # type: ignore[arg-type]
        scroll_x = float(st["scroll_x"])  # type: ignore[arg-type]
        scroll_y = float(st["scroll_y"])  # type: ignore[arg-type]
        zoom = float(st["zoom"])  # type: ignore[arg-type]
        ortho_mode = bool(st["ortho_mode"])  # type: ignore[arg-type]
        scale_mode = bool(st["scale_mode"])  # type: ignore[arg-type]
        tool_mode = str(st["tool_mode"])
        dragging_area_id = st.get("dragging_area_id")  # type: ignore[assignment]
        area_drag_off_x = float(st.get("area_drag_off_x", 0.0))  # type: ignore[arg-type]
        area_drag_off_y = float(st.get("area_drag_off_y", 0.0))  # type: ignore[arg-type]

    def push_undo() -> None:
        undo_stack.append(_snapshot_state())
        if len(undo_stack) > UNDO_LIMIT:
            del undo_stack[0]

    def undo(_event: tk.Event | None = None) -> str | None:
        if not undo_stack:
            return "break"
        st = undo_stack.pop()
        _restore_state(st)
        redraw()
        return "break"

    content_area = tk.Frame(root)
    content_area.pack(fill=tk.BOTH, expand=True)

    topbar = tk.Frame(content_area, bg=bar_bg, highlightthickness=1, highlightbackground=bar_bd)
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

    alan_menu_open = False
    cizgiler_menu_open = False

    def _btn_style(b: tk.Button) -> None:
        b.configure(
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

    def close_top_menus() -> None:
        nonlocal shapes_menu_open, alan_menu_open, cizgiler_menu_open
        if shapes_menu_open:
            shapes_menu_open = False
            shapes_popup.place_forget()
            shapes_toggle.configure(text="Şekiller  ▼")
        if alan_menu_open:
            alan_menu_open = False
            alan_popup.place_forget()
            alan_toggle.configure(text="Alan  ▼")
        if cizgiler_menu_open:
            cizgiler_menu_open = False
            cizgiler_popup.place_forget()
            cizgiler_toggle.configure(text="Çizgiler  ▼")
        hint_var.set("")

    def position_popup_under(btn: tk.Widget, popup: tk.Widget) -> None:
        root.update_idletasks()
        bx = btn.winfo_rootx() - root.winfo_rootx()
        by = btn.winfo_rooty() - root.winfo_rooty() + btn.winfo_height() + 6
        popup.place(x=bx, y=by)

    def toggle_alan_menu() -> None:
        nonlocal alan_menu_open
        if shapes_menu_open or cizgiler_menu_open:
            close_top_menus()
        alan_menu_open = not alan_menu_open
        if alan_menu_open:
            position_popup_under(alan_toggle, alan_popup)
            alan_popup.lift()
            alan_toggle.configure(text="Alan  ▲")
        else:
            alan_popup.place_forget()
            alan_toggle.configure(text="Alan  ▼")
            hint_var.set("")

    def toggle_cizgiler_menu() -> None:
        nonlocal cizgiler_menu_open
        if shapes_menu_open or alan_menu_open:
            close_top_menus()
        cizgiler_menu_open = not cizgiler_menu_open
        if cizgiler_menu_open:
            position_popup_under(cizgiler_toggle, cizgiler_popup)
            cizgiler_popup.lift()
            cizgiler_toggle.configure(text="Çizgiler  ▲")
        else:
            cizgiler_popup.place_forget()
            cizgiler_toggle.configure(text="Çizgiler  ▼")
            hint_var.set("")

    alan_toggle = tk.Button(left_head, text="Alan  ▼", command=toggle_alan_menu)
    _btn_style(alan_toggle)
    alan_toggle.pack(side=tk.LEFT, padx=(10, 0))

    cizgiler_toggle = tk.Button(left_head, text="Çizgiler  ▼", command=toggle_cizgiler_menu)
    _btn_style(cizgiler_toggle)
    cizgiler_toggle.pack(side=tk.LEFT, padx=(10, 0))

    select_btn = tk.Button(
        left_head,
        text="Seç",
        command=lambda: (close_top_menus(), set_tool("select", "")),
    )
    _btn_style(select_btn)
    select_btn.pack(side=tk.LEFT, padx=(10, 0))

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

    canvas_holder = tk.Frame(content_area)
    canvas_holder.pack(fill=tk.BOTH, expand=True)

    kind_labels_tr = {"square": "Kare", "rect": "Dikdörtgen", "triangle": "Üçgen"}

    def shape_kind_label(kind: str) -> str:
        return kind_labels_tr.get(kind, kind)

    def shape_row_title(si: int, s: dict[str, float | str]) -> str:
        raw = str(s.get("name", "")).strip()
        if raw:
            return raw
        return f"Şekil {si + 1}"

    def selection_ui_sync() -> None:
        return

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

    alan_popup = tk.Frame(
        root,
        bg=popup_bg,
        highlightthickness=1,
        highlightbackground=bar_bd,
        padx=14,
        pady=14,
    )

    cizgiler_popup = tk.Frame(
        root,
        bg=popup_bg,
        highlightthickness=1,
        highlightbackground=bar_bd,
        padx=14,
        pady=14,
    )

    def position_shapes_popup() -> None:
        position_popup_under(shapes_toggle, shapes_popup)

    def close_shapes_menu() -> None:
        nonlocal shapes_menu_open
        if not shapes_menu_open:
            return
        shapes_menu_open = False
        shapes_popup.place_forget()
        shapes_toggle.configure(text="Şekiller  ▼")
        hint_var.set("")

    def set_tool(mode: str, hint: str = "") -> None:
        nonlocal tool_mode, connecting_from, preview_wx, preview_wy
        tool_mode = mode
        connecting_from = None
        preview_wx = preview_wy = None
        hint_var.set(hint)
        redraw()

    def make_shape(kind: str, cx: float, cy: float, name: str) -> dict[str, float | str]:
        # label_dx/label_dy: isim konumu (şekil merkezine göre world offset)
        if kind == "square":
            half = (cell - 2 * block_pad) / 2.0
            return {
                "kind": "square",
                "cx": cx,
                "cy": cy,
                "half": half,
                "name": name,
                "label_dx": half + 14.0,
                "label_dy": -half - 10.0,
            }
        if kind == "rect":
            return {
                "kind": "rect",
                "cx": cx,
                "cy": cy,
                "hw": cell * 0.9,
                "hh": cell * 0.45,
                "name": name,
                "label_dx": cell * 0.9 + 14.0,
                "label_dy": -cell * 0.45 - 10.0,
            }
        return {
            "kind": "triangle",
            "cx": cx,
            "cy": cy,
            "tw": cell * 0.5,
            "bh": cell * 0.25,
            "ah": cell * 0.5,
            "name": name,
            "label_dx": cell * 0.5 + 14.0,
            "label_dy": -cell * 0.5 - 10.0,
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
        push_undo()
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
        selection_ui_sync()
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

    def edge_world_coords(e: dict[str, float | int | tuple]) -> tuple[float, float, float, float, float, float]:
        """mx,my,nx,ny,cx,cy"""
        a = e["a"]
        b = e["b"]
        assert isinstance(a, tuple) and isinstance(b, tuple)

        def anchor_of(h: tuple) -> tuple[float, float]:
            # shape handle: (si, role, idx)
            if len(h) == 3 and isinstance(h[0], int):
                si, role, idx = h
                return edge_anchor_world(int(si), str(role), int(idx))
            # world point: ("w", wx, wy)
            if len(h) == 3 and str(h[0]) == "w":
                return float(h[1]), float(h[2])
            return 0.0, 0.0

        mx, my = anchor_of(a)
        nx, ny = anchor_of(b)
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

    label_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    edge_label_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

    def shape_title_for_canvas(si: int, s: dict[str, float | str]) -> str:
        return shape_row_title(si, s)

    def label_world_pos(si: int) -> tuple[float, float]:
        s = shapes[si]
        cx = float(s["cx"])
        cy = float(s["cy"])
        dx = float(s.get("label_dx", 0.0))
        dy = float(s.get("label_dy", 0.0))
        return cx + dx, cy + dy

    def label_hit(sx: int, sy: int) -> int | None:
        wx, wy = screen_to_world(sx, sy)
        pad_px = 6.0
        for si in range(len(shapes) - 1, -1, -1):
            title = shape_title_for_canvas(si, shapes[si])
            if not title.strip():
                continue
            lx, ly = label_world_pos(si)
            w_px = float(label_font.measure(title)) + pad_px * 2
            h_px = float(label_font.metrics("linespace")) + pad_px * 2
            w_w = w_px / zoom
            h_w = h_px / zoom
            if (lx - w_w / 2.0) <= wx <= (lx + w_w / 2.0) and (ly - h_w / 2.0) <= wy <= (ly + h_w / 2.0):
                return si
        return None

    def draw_labels_layer() -> None:
        z = zoom
        for si, s in enumerate(shapes):
            title = shape_title_for_canvas(si, s)
            if not title.strip():
                continue
            wx, wy = label_world_pos(si)
            sx = (wx - scroll_x) * z
            sy = (wy - scroll_y) * z
            canvas.create_text(
                sx,
                sy,
                text=title,
                fill="#0f172a",
                font=label_font,
                anchor="center",
            )

    scaling_handle: tuple[int, int] | None = None
    scaling_anchor_world: tuple[float, float] | None = None
    scaling_base: dict[str, float] | None = None
    dragging_label_si: int | None = None
    label_drag_off_dx = 0.0
    label_drag_off_dy = 0.0
    dragging_edge_label_id: int | None = None
    edge_label_drag_off_dx = 0.0
    edge_label_drag_off_dy = 0.0

    def shape_scale_handles(si: int) -> list[tuple[int, float, float]]:
        # corner_idx, wx, wy (0..3 for rect/square, 0..2 for tri corners)
        s = shapes[si]
        k = str(s["kind"])
        cx = float(s["cx"])
        cy = float(s["cy"])
        if k == "square":
            h = float(s["half"])
            pts = [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
            return [(i, p[0], p[1]) for i, p in enumerate(pts)]
        if k == "rect":
            hw = float(s["hw"])
            hh = float(s["hh"])
            pts = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
            return [(i, p[0], p[1]) for i, p in enumerate(pts)]
        vs = geometry.tri_vertices(s)
        return [(i, p[0], p[1]) for i, p in enumerate(vs)]

    def scale_handle_hit_world(wx: float, wy: float) -> tuple[int, int] | None:
        if not scale_mode or len(selected_shape_indices) != 1:
            return None
        (si,) = tuple(selected_shape_indices)
        r = 9.0 / zoom
        best: tuple[int, int] | None = None
        best_d = r + 1.0
        for corner_idx, hx, hy in shape_scale_handles(si):
            d = math.hypot(wx - hx, wy - hy)
            if d < best_d and d <= r:
                best_d = d
                best = (si, corner_idx)
        return best

    def draw_scale_handles_layer() -> None:
        if not scale_mode or len(selected_shape_indices) != 1:
            return
        z = zoom
        (si,) = tuple(selected_shape_indices)
        rh = max(3.0, 3.4 * min(z, 1.35))
        ow = max(1, int(round(1.5 * min(z, 1.2))))
        for _ci, wx, wy in shape_scale_handles(si):
            sx = (wx - scroll_x) * z
            sy = (wy - scroll_y) * z
            canvas.create_rectangle(
                sx - rh,
                sy - rh,
                sx + rh,
                sy + rh,
                fill="#ffffff",
                outline="#334155",
                width=ow,
            )

    def apply_scale_from_pointer(si: int, corner_idx: int, wx: float, wy: float) -> None:
        nonlocal scaling_anchor_world, scaling_base
        if scaling_anchor_world is None or scaling_base is None:
            return
        ax, ay = scaling_anchor_world
        s = shapes[si]
        k = str(s["kind"])
        min_half = 8.0
        if k == "square":
            # Keep square proportions: use max(Δx, Δy) as the side so the pointer
            # always stays inside or on the edge of the new square.
            dxs = wx - ax
            dys = wy - ay
            side = max(min_half * 2, max(abs(dxs), abs(dys)))
            sx_sign = 1 if dxs >= 0 else -1
            sy_sign = 1 if dys >= 0 else -1
            half = side / 2.0
            s["half"] = half
            s["cx"] = ax + sx_sign * half
            s["cy"] = ay + sy_sign * half
        elif k == "rect":
            # Free aspect-ratio resize: anchor corner stays fixed, pointer is new opposite corner.
            nx0, nx1 = sorted([ax, wx])
            ny0, ny1 = sorted([ay, wy])
            hw = max(min_half, (nx1 - nx0) / 2.0)
            hh_v = max(min_half, (ny1 - ny0) / 2.0)
            s["hw"] = hw
            s["hh"] = hh_v
            s["cx"] = (nx0 + nx1) / 2.0
            s["cy"] = (ny0 + ny1) / 2.0
        else:
            # Triangle: uniform scale around center based on pointer distance from center.
            cx0 = float(scaling_base["cx"])
            cy0 = float(scaling_base["cy"])
            base_r = float(scaling_base["r"])
            cur_r = math.hypot(wx - cx0, wy - cy0)
            if base_r < 1e-6:
                return
            scale = max(0.15, min(10.0, cur_r / base_r))
            s["tw"] = max(min_half, float(scaling_base["tw"]) * scale)
            s["bh"] = max(min_half * 0.3, float(scaling_base["bh"]) * scale)
            s["ah"] = max(min_half, float(scaling_base["ah"]) * scale)
            s["cx"] = cx0
            s["cy"] = cy0

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

            # Cable label (edge name) — draw to the "right" side of direction.
            raw_name = str(e.get("name", "")).strip()
            if raw_name:
                name = raw_name
            else:
                name = f"Cable {eid}"

            # Use chord direction for both line and arc for stable label placement.
            dx = nx - mx
            dy = ny - my
            ln = math.hypot(dx, dy)
            if ln < 1e-9:
                continue
            # right normal (screen coords y down): (dy, -dx)
            rx = dy / ln
            ry = -dx / ln
            midx = (mx + nx) / 2.0
            midy = (my + ny) / 2.0
            off_w = 18.0 / zoom
            base_lwx = midx + rx * off_w
            base_lwy = midy + ry * off_w
            # persistent offset in world coords (draggable label)
            dx_w = float(e.get("label_dx", 0.0))
            dy_w = float(e.get("label_dy", 0.0))
            lwx = base_lwx + dx_w
            lwy = base_lwy + dy_w
            tsx = (lwx - scroll_x) * z
            tsy = (lwy - scroll_y) * z
            canvas.create_text(
                tsx,
                tsy,
                text=name,
                fill="#0f172a",
                font=edge_label_font,
                anchor="w",
            )

    def edge_label_base_world(e: dict[str, float | int | tuple[int, int]]) -> tuple[float, float] | None:
        mx, my, nx, ny, _cx, _cy = edge_world_coords(e)
        dx = nx - mx
        dy = ny - my
        ln = math.hypot(dx, dy)
        if ln < 1e-9:
            return None
        rx = dy / ln
        ry = -dx / ln
        midx = (mx + nx) / 2.0
        midy = (my + ny) / 2.0
        off_w = 18.0 / zoom
        return midx + rx * off_w, midy + ry * off_w

    def edge_label_hit(sx: int, sy: int) -> int | None:
        wx, wy = screen_to_world(sx, sy)
        pad_px = 6.0
        for e in reversed(edges):
            eid = int(e["id"])
            raw = str(e.get("name", "")).strip()
            name = raw if raw else f"Cable {eid}"
            base = edge_label_base_world(e)
            if base is None:
                continue
            bx, by = base
            lx = bx + float(e.get("label_dx", 0.0))
            ly = by + float(e.get("label_dy", 0.0))
            w_px = float(edge_label_font.measure(name)) + pad_px * 2
            h_px = float(edge_label_font.metrics("linespace")) + pad_px * 2
            w_w = w_px / zoom
            h_w = h_px / zoom
            # anchor="w" so left edge starts at lx; hitbox uses that.
            if lx <= wx <= (lx + w_w) and (ly - h_w / 2.0) <= wy <= (ly + h_w / 2.0):
                return eid
        return None

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

    drawing_anchor: tuple[float, float] | None = None
    drawing_cur: tuple[float, float] | None = None
    drawing_start_handle: tuple[int, str, int] | None = None

    def snap_to_handle(wx: float, wy: float) -> tuple[int, str, int] | None:
        thr = 14.0 / zoom
        best: tuple[int, str, int] | None = None
        best_d = thr + 1.0
        for si in range(len(shapes)):
            for role, idx, hx, hy in iter_handles(si):
                d = math.hypot(wx - hx, wy - hy)
                if d < best_d and d <= thr:
                    best_d = d
                    best = (si, role, idx)
        return best

    def _anchor_world(a: tuple[int, str, int] | None, wx: float, wy: float) -> tuple[float, float]:
        if a is None:
            return wx, wy
        si, role, idx = a
        return edge_anchor_world(si, role, idx)

    def nearest_point_on_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> tuple[float, float]:
        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay
        ab2 = abx * abx + aby * aby
        if ab2 < 1e-12:
            return ax, ay
        t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
        return ax + t * abx, ay + t * aby

    def free_line_end_world(fl: dict, key: str) -> tuple[float, float]:
        a = fl.get(key)
        if isinstance(a, tuple):
            si, role, idx = a
            return edge_anchor_world(int(si), str(role), int(idx))
        return float(fl[f"{key}x"]), float(fl[f"{key}y"])

    def draw_free_lines_layer() -> None:
        z = zoom
        for fl in free_lines:
            fid = int(fl["id"])
            sel = selected_free_line_id == fid
            col = "#0f172a" if sel else "#334155"
            lw = max(2, int(round((4 if sel else 2) * min(z, 2))))
            ax, ay = free_line_end_world(fl, "a")
            bx, by = free_line_end_world(fl, "b")
            sx0 = (ax - scroll_x) * z
            sy0 = (ay - scroll_y) * z
            sx1 = (bx - scroll_x) * z
            sy1 = (by - scroll_y) * z
            canvas.create_line(sx0, sy0, sx1, sy1, fill=col, width=lw, capstyle=tk.ROUND)

    def draw_junctions_layer() -> None:
        used: set[tuple[int, str, int]] = set()
        for e in edges:
            a = e["a"]
            b = e["b"]
            assert isinstance(a, tuple) and isinstance(b, tuple)
            if len(a) == 3 and isinstance(a[0], int):
                used.add((int(a[0]), str(a[1]), int(a[2])))
            if len(b) == 3 and isinstance(b[0], int):
                used.add((int(b[0]), str(b[1]), int(b[2])))
        for fl in free_lines:
            aa = fl.get("a")
            bb = fl.get("b")
            if isinstance(aa, tuple):
                used.add((int(aa[0]), str(aa[1]), int(aa[2])))
            if isinstance(bb, tuple):
                used.add((int(bb[0]), str(bb[1]), int(bb[2])))
        if not used:
            pass
        z = zoom
        r = max(3.0, 3.6 * min(z, 1.35))
        for si, role, idx in used:
            wx, wy = edge_anchor_world(si, role, idx)
            sx = (wx - scroll_x) * z
            sy = (wy - scroll_y) * z
            canvas.create_oval(
                sx - r,
                sy - r,
                sx + r,
                sy + r,
                fill="#0f172a",
                outline="#0f172a",
                width=1,
            )

        # also draw junctions for world-point endpoints (e.g. handle → line body)
        for e in edges:
            for h in (e["a"], e["b"]):
                if isinstance(h, tuple) and len(h) == 3 and str(h[0]) == "w":
                    wx = float(h[1])
                    wy = float(h[2])
                    sx = (wx - scroll_x) * z
                    sy = (wy - scroll_y) * z
                    canvas.create_oval(
                        sx - r,
                        sy - r,
                        sx + r,
                        sy + r,
                        fill="#0f172a",
                        outline="#0f172a",
                        width=1,
                    )

    area_label_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

    def draw_round_rect(sx0: float, sy0: float, sx1: float, sy1: float, r: float, **kwargs) -> None:
        r = max(2.0, min(r, abs(sx1 - sx0) / 2.0, abs(sy1 - sy0) / 2.0))
        pts = [
            sx0 + r,
            sy0,
            sx1 - r,
            sy0,
            sx1,
            sy0,
            sx1,
            sy0 + r,
            sx1,
            sy1 - r,
            sx1,
            sy1,
            sx1 - r,
            sy1,
            sx0 + r,
            sy1,
            sx0,
            sy1,
            sx0,
            sy1 - r,
            sx0,
            sy0 + r,
            sx0,
            sy0,
        ]
        canvas.create_polygon(pts, smooth=True, splinesteps=12, **kwargs)

    def area_bbox_world(a: dict) -> tuple[float, float, float, float]:
        x0 = float(a["x0"])
        y0 = float(a["y0"])
        x1 = float(a["x1"])
        y1 = float(a["y1"])
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def draw_areas_layer() -> None:
        z = zoom
        for a in areas:
            aid = int(a["id"])
            sel = selected_area_id == aid
            x0, y0, x1, y1 = area_bbox_world(a)
            sx0 = (x0 - scroll_x) * z
            sy0 = (y0 - scroll_y) * z
            sx1 = (x1 - scroll_x) * z
            sy1 = (y1 - scroll_y) * z
            # Alanlar: sadece kesikli (içi boş)
            dash = (6, 4)
            outline = C.SELECTION_OUTLINE if sel else "#334155"
            width = max(2, int(round((3.0 if sel else 2.0) * min(z, 1.6))))
            fill = ""
            if str(a.get("kind")) == "roundrect":
                draw_round_rect(
                    sx0,
                    sy0,
                    sx1,
                    sy1,
                    r=max(8.0, 10.0 * min(z, 1.1)),
                    fill=fill,
                    outline=outline,
                    width=width,
                    dash=dash,
                )
            else:
                canvas.create_rectangle(sx0, sy0, sx1, sy1, fill=fill, outline=outline, width=width, dash=dash)
            nm = str(a.get("name", "")).strip()
            if nm:
                canvas.create_text(sx1 + 6, sy0 + 6, text=nm, fill="#0f172a", font=area_label_font, anchor="nw")

    def draw_tool_preview() -> None:
        if drawing_anchor is None or drawing_cur is None:
            return
        ax, ay = drawing_anchor
        bx, by = drawing_cur
        z = zoom
        sx0 = (ax - scroll_x) * z
        sy0 = (ay - scroll_y) * z
        sx1 = (bx - scroll_x) * z
        sy1 = (by - scroll_y) * z
        if tool_mode == "draw_free_line":
            canvas.create_line(
                sx0,
                sy0,
                sx1,
                sy1,
                fill="#64748b",
                width=max(1, int(round(2 * min(z, 2)))),
                dash=(6, 4),
                capstyle=tk.ROUND,
            )
        elif tool_mode.startswith("area_"):
            dash = (6, 4)
            if tool_mode == "area_roundrect":
                draw_round_rect(
                    sx0,
                    sy0,
                    sx1,
                    sy1,
                    r=max(8.0, 10.0 * min(z, 1.1)),
                    fill="",
                    outline="#64748b",
                    width=2,
                    dash=dash,
                )
            else:
                canvas.create_rectangle(
                    sx0,
                    sy0,
                    sx1,
                    sy1,
                    fill="",
                    outline="#64748b",
                    width=2,
                    dash=dash,
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

        draw_areas_layer()
        draw_edges_layer()
        draw_free_lines_layer()
        draw_junctions_layer()

        for si, s in enumerate(shapes):
            draw_shape_ui(s, si)

        draw_selection_boxes()

        draw_handles_layer()
        draw_scale_handles_layer()
        draw_preview_connector()
        draw_marquee_rect()
        draw_labels_layer()
        draw_tool_preview()

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
        nonlocal palette_drag_kind, next_shape_label_num
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
        label = f"Şekil {next_shape_label_num}"
        next_shape_label_num += 1
        push_undo()
        shapes.append(make_shape(k, wx, wy, label))
        redraw()

    line_menu: tk.Menu | None = None
    shape_ctx_menu: tk.Menu | None = None
    shape_props_modal: tk.Toplevel | None = None
    edge_props_modal: tk.Toplevel | None = None

    def close_shape_props_modal() -> None:
        nonlocal shape_props_modal
        if shape_props_modal is not None:
            try:
                shape_props_modal.destroy()
            except tk.TclError:
                pass
            shape_props_modal = None

    def close_edge_props_modal() -> None:
        nonlocal edge_props_modal
        if edge_props_modal is not None:
            try:
                edge_props_modal.destroy()
            except tk.TclError:
                pass
            edge_props_modal = None

    def center_modal_dialog(win: tk.Toplevel) -> None:
        root.update_idletasks()
        win.update_idletasks()
        rw = root.winfo_width()
        rh = root.winfo_height()
        ww = win.winfo_reqwidth()
        wh = win.winfo_reqheight()
        x = root.winfo_rootx() + max(0, (rw - ww) // 2)
        y = root.winfo_rooty() + max(0, (rh - wh) // 2)
        win.geometry(f"+{x}+{y}")

    def show_shape_properties_modal(si: int) -> None:
        nonlocal shape_props_modal
        if si < 0 or si >= len(shapes):
            return
        close_shape_props_modal()
        dlg = tk.Toplevel(root)
        shape_props_modal = dlg
        dlg.title("Özellikler")
        dlg.resizable(False, False)
        dlg.transient(root)
        dlg.configure(bg=popup_bg, highlightthickness=1, highlightbackground=bar_bd)
        dlg.protocol("WM_DELETE_WINDOW", close_shape_props_modal)

        pad = tk.Frame(dlg, bg=popup_bg, padx=22, pady=18)
        pad.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            pad,
            text="İsim",
            bg=popup_bg,
            fg=ink,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        k = str(shapes[si]["kind"])
        tk.Label(
            pad,
            text=shape_kind_label(k),
            bg=popup_bg,
            fg=muted,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        name_val = str(shapes[si].get("name", ""))
        name_e = tk.Entry(
            pad,
            width=32,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=bar_bd,
            highlightcolor=C.SELECTION_OUTLINE,
        )
        name_e.pack(fill=tk.X, pady=(0, 16))
        name_e.insert(0, name_val)
        name_e.select_range(0, tk.END)
        name_e.focus_set()

        btn_row = tk.Frame(pad, bg=popup_bg)
        btn_row.pack(fill=tk.X)

        def on_ok() -> None:
            if 0 <= si < len(shapes):
                push_undo()
                shapes[si]["name"] = str(name_e.get()).strip()
                selection_ui_sync()
                redraw()
            close_shape_props_modal()

        def on_cancel() -> None:
            close_shape_props_modal()

        tk.Button(
            btn_row,
            text="İptal",
            command=on_cancel,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#f1f5f9",
            fg=ink,
            font=("Segoe UI", 9),
            padx=16,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            btn_row,
            text="Tamam",
            command=on_ok,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=8,
        ).pack(side=tk.RIGHT)

        dlg.bind("<Return>", lambda _e: on_ok())
        dlg.bind("<Escape>", lambda _e: on_cancel())
        center_modal_dialog(dlg)
        dlg.update_idletasks()
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    def edge_row_title(e: dict[str, float | int | tuple[int, int]]) -> str:
        raw = str(e.get("name", "")).strip()
        if raw:
            return raw
        return f"Cable {int(e['id'])}"

    def show_edge_properties_modal(eid: int) -> None:
        nonlocal edge_props_modal
        close_edge_props_modal()

        target: dict[str, float | int | tuple[int, int]] | None = None
        for e in edges:
            if int(e["id"]) == eid:
                target = e
                break
        if target is None:
            return

        dlg = tk.Toplevel(root)
        edge_props_modal = dlg
        dlg.title("Cable Özellikleri")
        dlg.resizable(False, False)
        dlg.transient(root)
        dlg.configure(bg=popup_bg, highlightthickness=1, highlightbackground=bar_bd)
        dlg.protocol("WM_DELETE_WINDOW", close_edge_props_modal)

        pad = tk.Frame(dlg, bg=popup_bg, padx=22, pady=18)
        pad.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            pad,
            text="İsim",
            bg=popup_bg,
            fg=ink,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            pad,
            text=f"ID: {eid}",
            bg=popup_bg,
            fg=muted,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        name_val = edge_row_title(target)
        name_e = tk.Entry(
            pad,
            width=32,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=bar_bd,
            highlightcolor=C.SELECTION_OUTLINE,
        )
        name_e.pack(fill=tk.X, pady=(0, 16))
        name_e.insert(0, name_val)
        name_e.select_range(0, tk.END)
        name_e.focus_set()

        btn_row = tk.Frame(pad, bg=popup_bg)
        btn_row.pack(fill=tk.X)

        def on_ok() -> None:
            push_undo()
            for e in edges:
                if int(e["id"]) == eid:
                    e["name"] = str(name_e.get()).strip()
                    break
            redraw()
            close_edge_props_modal()

        def on_cancel() -> None:
            close_edge_props_modal()

        tk.Button(
            btn_row,
            text="İptal",
            command=on_cancel,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#f1f5f9",
            fg=ink,
            font=("Segoe UI", 9),
            padx=16,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            btn_row,
            text="Tamam",
            command=on_ok,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=8,
        ).pack(side=tk.RIGHT)

        dlg.bind("<Return>", lambda _e: on_ok())
        dlg.bind("<Escape>", lambda _e: on_cancel())
        center_modal_dialog(dlg)
        dlg.update_idletasks()
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    def set_edge_line(eid: int) -> None:
        push_undo()
        for e in edges:
            if int(e["id"]) == eid:
                e["kind"] = "line"
                mx, my, nx, ny, _, _ = edge_world_coords(e)
                e["cx"] = (mx + nx) / 2.0
                e["cy"] = (my + ny) / 2.0
                break
        redraw()

    def set_edge_arc(eid: int) -> None:
        push_undo()
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
        line_menu.add_command(label="Özellikler", command=lambda: (close_edge_props_modal(), show_edge_properties_modal(eid)))
        line_menu.add_separator()
        line_menu.add_command(label="Düz çizgi", command=lambda: set_edge_line(eid))
        line_menu.add_command(label="Yay (arc)", command=lambda: set_edge_arc(eid))
        try:
            line_menu.tk_popup(event.x_root, event.y_root)
        finally:
            line_menu.grab_release()

    def show_shape_context_menu(event: tk.Event, si: int) -> None:
        nonlocal shape_ctx_menu
        if shape_ctx_menu is not None:
            try:
                shape_ctx_menu.destroy()
            except tk.TclError:
                pass
        shape_ctx_menu = tk.Menu(canvas, tearoff=0)
        shape_ctx_menu.add_command(
            label="Özellikler",
            command=lambda idx=si: (close_shape_props_modal(), show_shape_properties_modal(idx)),
        )
        shape_ctx_menu.add_separator()
        shape_ctx_menu.add_command(
            label=("Scale Mode: Açık" if scale_mode else "Scale Mode: Kapalı"),
            command=lambda: toggle_scale_mode(),
        )
        try:
            shape_ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            shape_ctx_menu.grab_release()

    def toggle_scale_mode() -> None:
        nonlocal scale_mode
        scale_mode = not scale_mode
        redraw()

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
        nonlocal next_edge_id, next_cable_num
        nonlocal next_free_line_id, selected_free_line_id
        nonlocal next_area_id, selected_area_id
        nonlocal shape_drag_ortho_anchor, shape_group_origin
        nonlocal arc_drag_base_cx, arc_drag_base_cy, arc_drag_ptr_x, arc_drag_ptr_y
        nonlocal selected_shape_indices, marquee_active
        nonlocal marquee_ax, marquee_ay, marquee_cur_x, marquee_cur_y
        nonlocal drawing_anchor, drawing_cur, drawing_start_handle
        nonlocal dragging_area_id, area_drag_off_x, area_drag_off_y
        close_top_menus()
        if palette_drag_kind is not None:
            return
        if event.state & 0x4:
            return

        wx0, wy0 = screen_to_world(event.x, event.y)

        # Alan sürükleme — şekil/handle'lardan önce (alan içindeyken öncelik)
        if tool_mode == "select" and connecting_from is None:
            aid_drag = hit_area(event.x, event.y)
            if aid_drag is not None:
                push_undo()
                dragging_area_id = aid_drag
                selected_area_id = aid_drag
                selected_edge_id = None
                selected_free_line_id = None
                selected_shape_indices = set()
                connecting_from = None
                preview_wx = preview_wy = None
                area_drag_off_x = wx0
                area_drag_off_y = wy0
                canvas.config(cursor="fleur")
                redraw()
                return

        # Cable label drag (lowest priority among non-selection, but before starting marquee)
        eid_lbl = edge_label_hit(event.x, event.y)
        if eid_lbl is not None:
            nonlocal dragging_edge_label_id, edge_label_drag_off_dx, edge_label_drag_off_dy
            push_undo()
            dragging_edge_label_id = eid_lbl
            # compute offset relative to base label position
            for e in edges:
                if int(e["id"]) == eid_lbl:
                    base = edge_label_base_world(e)
                    if base is None:
                        break
                    bx, by = base
                    cur_dx = float(e.get("label_dx", 0.0))
                    cur_dy = float(e.get("label_dy", 0.0))
                    # want: new_dx = (wx - bx) - drag_off_dx; so drag_off_dx = (wx - bx) - cur_dx
                    edge_label_drag_off_dx = (wx0 - bx) - cur_dx
                    edge_label_drag_off_dy = (wy0 - by) - cur_dy
                    break
            selected_edge_id = eid_lbl
            selected_free_line_id = None
            selected_area_id = None
            selected_shape_indices = set()
            canvas.config(cursor="hand2")
            redraw()
            return

        if tool_mode == "draw_free_line":
            drawing_start_handle = snap_to_handle(wx0, wy0)
            ax, ay = _anchor_world(drawing_start_handle, wx0, wy0)
            drawing_anchor = (ax, ay)
            drawing_cur = (wx0, wy0)
            canvas.config(cursor="pencil")
            redraw()
            return
        if tool_mode.startswith("area_"):
            drawing_anchor = (wx0, wy0)
            drawing_cur = (wx0, wy0)
            canvas.config(cursor="tcross")
            redraw()
            return

        # 1. Arc body drag
        aid = hit_arc_body_for_drag(event.x, event.y)
        if aid is not None:
            push_undo()
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
            selection_ui_sync()
            redraw()
            return

        # 2. Scale handles — checked BEFORE connection handles so they take priority
        sh = scale_handle_hit_world(wx0, wy0)
        if sh is not None:
            push_undo()
            nonlocal scaling_handle, scaling_anchor_world, scaling_base
            si, corner_idx = sh
            scaling_handle = (si, corner_idx)
            s = shapes[si]
            k = str(s["kind"])
            if k in ("square", "rect"):
                corners = shape_scale_handles(si)
                opp = (corner_idx + 2) % 4
                ax, ay = corners[opp][1], corners[opp][2]
                scaling_anchor_world = (ax, ay)
                scaling_base = {"cx": float(s["cx"]), "cy": float(s["cy"])}
            else:
                cx0 = float(s["cx"])
                cy0 = float(s["cy"])
                vs = geometry.tri_vertices(s)
                vx, vy = vs[corner_idx]
                scaling_anchor_world = (cx0, cy0)
                scaling_base = {
                    "cx": cx0,
                    "cy": cy0,
                    "tw": float(s["tw"]),
                    "bh": float(s["bh"]),
                    "ah": float(s["ah"]),
                    "r": max(1e-6, math.hypot(vx - cx0, vy - cy0)),
                }
            canvas.config(cursor="sizing")
            redraw()
            return

        # 3. Connection handles — disabled when scale_mode is active for the selected shape
        #    to prevent handle clicks from starting connections instead of resizing.
        if not (scale_mode and len(selected_shape_indices) == 1):
            hh = handle_hit_world(wx0, wy0)
            if hh is not None:
                selected_shape_indices = set()
                selection_ui_sync()
                si, role, idx = hh
                if connecting_from is None:
                    connecting_from = (si, role, idx)
                    preview_wx, preview_wy = wx0, wy0
                else:
                    fa, fra, fi = connecting_from
                    if fa == si and fra == role and fi == idx:
                        connecting_from = None
                        preview_wx = preview_wy = None
                        redraw()
                        return
                    push_undo()
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
                            "name": f"Cable {next_cable_num}",
                            "label_dx": 0.0,
                            "label_dy": 0.0,
                        }
                    )
                    next_cable_num += 1
                    next_edge_id += 1
                    connecting_from = None
                    preview_wx = preview_wy = None
                    selected_edge_id = None
                redraw()
                return

        # If we are in connection mode and user clicks a line body, connect to nearest point.
        if connecting_from is not None:
            fid = hit_free_line(event.x, event.y)
            if fid is not None:
                wx, wy = screen_to_world(event.x, event.y)
                for fl in free_lines:
                    if int(fl["id"]) == fid:
                        ax, ay = free_line_end_world(fl, "a")
                        bx, by = free_line_end_world(fl, "b")
                        px, py = nearest_point_on_segment(wx, wy, ax, ay, bx, by)
                        break
                else:
                    px, py = wx, wy
                push_undo()
                fa, fra, fi = connecting_from
                mx, my = edge_anchor_world(fa, fra, fi)
                edges.append(
                    {
                        "id": next_edge_id,
                        "kind": "line",
                        "a": connecting_from,
                        "b": ("w", px, py),
                        "cx": (mx + px) / 2.0,
                        "cy": (my + py) / 2.0,
                        "name": f"Cable {next_cable_num}",
                        "label_dx": 0.0,
                        "label_dy": 0.0,
                    }
                )
                next_cable_num += 1
                next_edge_id += 1
                connecting_from = None
                preview_wx = preview_wy = None
                selected_edge_id = None
                redraw()
                return

            eid_hit = hit_edge(event.x, event.y)
            if eid_hit is not None:
                wx, wy = screen_to_world(event.x, event.y)
                # nearest point on chord (good enough for arc too)
                for e in edges:
                    if int(e["id"]) == eid_hit:
                        mx0, my0, nx0, ny0, _cx, _cy = edge_world_coords(e)
                        px, py = nearest_point_on_segment(wx, wy, mx0, my0, nx0, ny0)
                        break
                else:
                    px, py = wx, wy
                push_undo()
                fa, fra, fi = connecting_from
                mx, my = edge_anchor_world(fa, fra, fi)
                edges.append(
                    {
                        "id": next_edge_id,
                        "kind": "line",
                        "a": connecting_from,
                        "b": ("w", px, py),
                        "cx": (mx + px) / 2.0,
                        "cy": (my + py) / 2.0,
                        "name": f"Cable {next_cable_num}",
                        "label_dx": 0.0,
                        "label_dy": 0.0,
                    }
                )
                next_cable_num += 1
                next_edge_id += 1
                connecting_from = None
                preview_wx = preview_wy = None
                selected_edge_id = None
                redraw()
                return

        # 4. Shape body — checked BEFORE label so clicking on the shape always selects it
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
                selection_ui_sync()
                redraw()
                return
            wx, wy = screen_to_world(event.x, event.y)
            if idx_shape in selected_shape_indices and len(selected_shape_indices) > 1:
                shape_group_origin = {i: (float(shapes[i]["cx"]), float(shapes[i]["cy"])) for i in selected_shape_indices}
            else:
                selected_shape_indices = {idx_shape}
                shape_group_origin = None
            selected_edge_id = None
            push_undo()
            dragging_shape_idx = idx_shape
            drag_off_x = wx - float(shapes[idx_shape]["cx"])
            drag_off_y = wy - float(shapes[idx_shape]["cy"])
            shape_drag_ortho_anchor = (
                float(shapes[idx_shape]["cx"]),
                float(shapes[idx_shape]["cy"]),
            )
            selection_ui_sync()
            canvas.config(cursor="hand2")
            redraw()
            return

        eid_hit = hit_edge(event.x, event.y)
        if eid_hit is not None:
            selected_edge_id = eid_hit
            selected_shape_indices = set()
            selected_free_line_id = None
            selected_area_id = None
            selection_ui_sync()
            redraw()
            return

        fid = hit_free_line(event.x, event.y)
        if fid is not None:
            selected_free_line_id = fid
            selected_edge_id = None
            selected_area_id = None
            selected_shape_indices = set()
            selection_ui_sync()
            redraw()
            return

        # 5. Label hit — lowest priority so shape clicks are never stolen by the label
        li = label_hit(event.x, event.y)
        if li is not None:
            nonlocal dragging_label_si, label_drag_off_dx, label_drag_off_dy
            push_undo()
            dragging_label_si = li
            cx = float(shapes[li]["cx"])
            cy = float(shapes[li]["cy"])
            cur_dx = float(shapes[li].get("label_dx", 0.0))
            cur_dy = float(shapes[li].get("label_dy", 0.0))
            label_drag_off_dx = (wx0 - cx) - cur_dx
            label_drag_off_dy = (wy0 - cy) - cur_dy
            selected_shape_indices = {li}
            selected_edge_id = None
            selection_ui_sync()
            canvas.config(cursor="hand2")
            redraw()
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
            selection_ui_sync()
        redraw()

    def on_canvas_left_motion(event: tk.Event) -> None:
        nonlocal dragging_shape_idx, preview_wx, preview_wy
        nonlocal dragging_arc_edge_id
        nonlocal arc_drag_base_cx, arc_drag_base_cy, arc_drag_ptr_x, arc_drag_ptr_y
        nonlocal marquee_cur_x, marquee_cur_y
        nonlocal shape_group_origin
        nonlocal dragging_label_si
        nonlocal scaling_handle
        nonlocal drawing_anchor, drawing_cur
        nonlocal dragging_edge_label_id
        nonlocal dragging_area_id, area_drag_off_x, area_drag_off_y
        if marquee_active:
            marquee_cur_x = event.x
            marquee_cur_y = event.y
            redraw()
            return
        if dragging_edge_label_id is not None:
            eid = dragging_edge_label_id
            wx, wy = screen_to_world(event.x, event.y)
            for e in edges:
                if int(e["id"]) == eid:
                    base = edge_label_base_world(e)
                    if base is None:
                        break
                    bx, by = base
                    e["label_dx"] = (wx - bx) - edge_label_drag_off_dx
                    e["label_dy"] = (wy - by) - edge_label_drag_off_dy
                    break
            redraw()
            return
        if dragging_area_id is not None:
            wx, wy = screen_to_world(event.x, event.y)
            dx = wx - area_drag_off_x
            dy = wy - area_drag_off_y
            translate_area_by_delta(int(dragging_area_id), dx, dy)
            area_drag_off_x = wx
            area_drag_off_y = wy
            redraw()
            return
        if drawing_anchor is not None:
            wx, wy = screen_to_world(event.x, event.y)
            if tool_mode in ("area_square", "area_hollow_square"):
                ax, ay = drawing_anchor
                dx = wx - ax
                dy = wy - ay
                side = max(abs(dx), abs(dy))
                wx = ax + (side if dx >= 0 else -side)
                wy = ay + (side if dy >= 0 else -side)
            drawing_cur = (wx, wy)
            redraw()
            return
        if dragging_label_si is not None:
            si = dragging_label_si
            wx, wy = screen_to_world(event.x, event.y)
            cx = float(shapes[si]["cx"])
            cy = float(shapes[si]["cy"])
            shapes[si]["label_dx"] = (wx - cx) - label_drag_off_dx
            shapes[si]["label_dy"] = (wy - cy) - label_drag_off_dy
            redraw()
            return
        if scaling_handle is not None:
            si, corner_idx = scaling_handle
            wx, wy = screen_to_world(event.x, event.y)
            apply_scale_from_pointer(si, corner_idx, wx, wy)
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
        nonlocal dragging_label_si, scaling_handle, scaling_anchor_world, scaling_base
        nonlocal dragging_edge_label_id
        nonlocal dragging_area_id, area_drag_off_x, area_drag_off_y
        nonlocal drawing_anchor, drawing_cur, drawing_start_handle
        nonlocal next_edge_id, next_cable_num
        nonlocal next_free_line_id, selected_free_line_id
        nonlocal next_area_id, selected_area_id
        if marquee_active:
            marquee_active = False
            wx0, wy0 = screen_to_world(marquee_ax, marquee_ay)
            wx1, wy1 = screen_to_world(marquee_cur_x, marquee_cur_y)
            selected_shape_indices = shapes_in_marquee_world(wx0, wy0, wx1, wy1)
            selected_edge_id = None
            selection_ui_sync()
            redraw()
            return
        if drawing_anchor is not None and drawing_cur is not None:
            ax, ay = drawing_anchor
            bx, by = drawing_cur
            if tool_mode == "draw_free_line":
                push_undo()
                end_handle = snap_to_handle(bx, by)
                ex, ey = _anchor_world(end_handle, bx, by)
                # Both ends snapped → create a real Cable (edge)
                if drawing_start_handle is not None and end_handle is not None:
                    mx, my = edge_anchor_world(*drawing_start_handle)
                    nx, ny = edge_anchor_world(*end_handle)
                    edges.append(
                        {
                            "id": next_edge_id,
                            "kind": "line",
                            "a": drawing_start_handle,
                            "b": end_handle,
                            "cx": (mx + nx) / 2.0,
                            "cy": (my + ny) / 2.0,
                            "name": f"Cable {next_cable_num}",
                            "label_dx": 0.0,
                            "label_dy": 0.0,
                        }
                    )
                    selected_edge_id = next_edge_id
                    selected_free_line_id = None
                    next_cable_num += 1
                    next_edge_id += 1
                else:
                    free_lines.append(
                        {
                            "id": next_free_line_id,
                            "ax": ax,
                            "ay": ay,
                            "bx": ex,
                            "by": ey,
                            "a": drawing_start_handle,
                            "b": end_handle,
                        }
                    )
                    selected_free_line_id = next_free_line_id
                    next_free_line_id += 1
            elif tool_mode.startswith("area_"):
                push_undo()
                hollow = tool_mode in ("area_hollow_rect", "area_hollow_square")
                kind = "roundrect" if tool_mode == "area_roundrect" else "rect"
                areas.append(
                    {
                        "id": next_area_id,
                        "kind": kind,
                        "x0": ax,
                        "y0": ay,
                        "x1": bx,
                        "y1": by,
                        "hollow": hollow,
                        "name": f"Alan {next_area_id}",
                    }
                )
                selected_area_id = next_area_id
                next_area_id += 1
            drawing_anchor = None
            drawing_cur = None
            drawing_start_handle = None
            canvas.config(cursor="crosshair")
            redraw()
            return
        dragging_label_si = None
        dragging_edge_label_id = None
        dragging_area_id = None
        area_drag_off_x = 0.0
        area_drag_off_y = 0.0
        scaling_handle = None
        scaling_anchor_world = None
        scaling_base = None
        dragging_shape_idx = None
        dragging_arc_edge_id = None
        shape_drag_ortho_anchor = None
        shape_group_origin = None
        canvas.config(cursor="crosshair")

    def on_delete_key(_event: tk.Event | None = None) -> None:
        if selected_area_id is not None:
            delete_area(int(selected_area_id))
            return
        if selected_free_line_id is not None:
            delete_free_line(int(selected_free_line_id))
            return
        delete_selected_shapes()

    def on_canvas_right(event: tk.Event) -> None:
        nonlocal selected_edge_id, connecting_from, preview_wx, preview_wy, selected_shape_indices
        nonlocal selected_free_line_id, selected_area_id
        close_top_menus()
        # Right click on a label should behave like right click on its shape.
        li = label_hit(event.x, event.y)
        if li is not None:
            selected_shape_indices = {li}
            selected_edge_id = None
            selected_free_line_id = None
            selected_area_id = None
            connecting_from = None
            preview_wx = preview_wy = None
            selection_ui_sync()
            redraw()
            show_shape_context_menu(event, li)
            return
        idx_shape = hit_top_shape(event.x, event.y)
        if idx_shape is not None:
            selected_shape_indices = {idx_shape}
            selected_edge_id = None
            selected_free_line_id = None
            selected_area_id = None
            connecting_from = None
            preview_wx = preview_wy = None
            selection_ui_sync()
            redraw()
            show_shape_context_menu(event, idx_shape)
            return
        eid_hit = hit_edge(event.x, event.y)
        if eid_hit is not None:
            selected_edge_id = eid_hit
            selected_free_line_id = None
            selected_area_id = None
            redraw()
            show_edge_menu(event, eid_hit)
            return

        fid = hit_free_line(event.x, event.y)
        if fid is not None:
            selected_free_line_id = fid
            selected_edge_id = None
            selected_area_id = None
            selected_shape_indices = set()
            redraw()
            show_free_line_menu(event, fid)
            return

        aid = hit_area(event.x, event.y)
        if aid is not None:
            selected_area_id = aid
            selected_edge_id = None
            selected_free_line_id = None
            selected_shape_indices = set()
            redraw()
            show_area_menu(event, aid)
            return

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
        nonlocal selected_free_line_id, selected_area_id
        nonlocal tool_mode, drawing_anchor, drawing_cur, drawing_start_handle
        nonlocal dragging_area_id, area_drag_off_x, area_drag_off_y
        close_shape_props_modal()
        close_edge_props_modal()
        close_area_props_modal()
        selected_shape_indices = set()
        selected_edge_id = None
        selected_free_line_id = None
        selected_area_id = None
        marquee_active = False
        # Çizim modunu kapat → seçim moduna dön
        tool_mode = "select"
        drawing_anchor = None
        drawing_cur = None
        drawing_start_handle = None
        dragging_area_id = None
        area_drag_off_x = 0.0
        area_drag_off_y = 0.0
        canvas.config(cursor="crosshair")
        selection_ui_sync()

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

    def hit_free_line(sx: int, sy: int) -> int | None:
        wx, wy = screen_to_world(sx, sy)
        thr = 10.0 / zoom
        best: int | None = None
        best_d = thr + 1.0
        for fl in free_lines:
            ax, ay = free_line_end_world(fl, "a")
            bx, by = free_line_end_world(fl, "b")
            d = geometry.dist_point_segment(wx, wy, ax, ay, bx, by)
            if d < best_d and d <= thr:
                best_d = d
                best = int(fl["id"])
        return best

    def hit_area(sx: int, sy: int) -> int | None:
        wx, wy = screen_to_world(sx, sy)
        for a in reversed(areas):
            x0, y0, x1, y1 = area_bbox_world(a)
            if x0 <= wx <= x1 and y0 <= wy <= y1:
                return int(a["id"])
        return None

    def translate_area_by_delta(aid: int, dx: float, dy: float) -> None:
        for a in areas:
            if int(a["id"]) != aid:
                continue
            a["x0"] = float(a["x0"]) + dx
            a["y0"] = float(a["y0"]) + dy
            a["x1"] = float(a["x1"]) + dx
            a["y1"] = float(a["y1"]) + dy
            break

    free_line_menu: tk.Menu | None = None
    area_menu: tk.Menu | None = None
    area_props_modal: tk.Toplevel | None = None

    def close_area_props_modal() -> None:
        nonlocal area_props_modal
        if area_props_modal is not None:
            try:
                area_props_modal.destroy()
            except tk.TclError:
                pass
            area_props_modal = None

    def show_area_properties_modal(aid: int) -> None:
        nonlocal area_props_modal
        close_area_props_modal()
        target: dict | None = None
        for a in areas:
            if int(a["id"]) == aid:
                target = a
                break
        if target is None:
            return
        dlg = tk.Toplevel(root)
        area_props_modal = dlg
        dlg.title("Alan Özellikleri")
        dlg.resizable(False, False)
        dlg.transient(root)
        dlg.configure(bg=popup_bg, highlightthickness=1, highlightbackground=bar_bd)
        dlg.protocol("WM_DELETE_WINDOW", close_area_props_modal)

        pad = tk.Frame(dlg, bg=popup_bg, padx=22, pady=18)
        pad.pack(fill=tk.BOTH, expand=True)

        tk.Label(pad, text="İsim", bg=popup_bg, fg=ink, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(pad, text=f"ID: {aid}", bg=popup_bg, fg=muted, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 8))

        name_e = tk.Entry(
            pad,
            width=32,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=bar_bd,
            highlightcolor=C.SELECTION_OUTLINE,
        )
        name_e.pack(fill=tk.X, pady=(0, 16))
        name_e.insert(0, str(target.get("name", "")).strip())
        name_e.select_range(0, tk.END)
        name_e.focus_set()

        btn_row = tk.Frame(pad, bg=popup_bg)
        btn_row.pack(fill=tk.X)

        def on_ok() -> None:
            push_undo()
            for a in areas:
                if int(a["id"]) == aid:
                    a["name"] = str(name_e.get()).strip()
                    break
            redraw()
            close_area_props_modal()

        def on_cancel() -> None:
            close_area_props_modal()

        tk.Button(
            btn_row,
            text="İptal",
            command=on_cancel,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#f1f5f9",
            fg=ink,
            font=("Segoe UI", 9),
            padx=16,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            btn_row,
            text="Tamam",
            command=on_ok,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=8,
        ).pack(side=tk.RIGHT)

        dlg.bind("<Return>", lambda _e: on_ok())
        dlg.bind("<Escape>", lambda _e: on_cancel())
        center_modal_dialog(dlg)
        dlg.update_idletasks()
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    def delete_free_line(fid: int) -> None:
        nonlocal free_lines, selected_free_line_id
        push_undo()
        free_lines = [fl for fl in free_lines if int(fl["id"]) != fid]
        if selected_free_line_id == fid:
            selected_free_line_id = None
        redraw()

    def show_free_line_menu(event: tk.Event, fid: int) -> None:
        nonlocal free_line_menu
        if free_line_menu is not None:
            try:
                free_line_menu.destroy()
            except tk.TclError:
                pass
        free_line_menu = tk.Menu(canvas, tearoff=0)
        free_line_menu.add_command(label="Sil", command=lambda: delete_free_line(fid))
        try:
            free_line_menu.tk_popup(event.x_root, event.y_root)
        finally:
            free_line_menu.grab_release()

    def delete_area(aid: int) -> None:
        nonlocal areas, selected_area_id
        push_undo()
        areas = [a for a in areas if int(a["id"]) != aid]
        if selected_area_id == aid:
            selected_area_id = None
        redraw()

    def show_area_menu(event: tk.Event, aid: int) -> None:
        nonlocal area_menu
        if area_menu is not None:
            try:
                area_menu.destroy()
            except tk.TclError:
                pass
        area_menu = tk.Menu(canvas, tearoff=0)
        area_menu.add_command(label="Özellikler", command=lambda: (close_area_props_modal(), show_area_properties_modal(aid)))
        area_menu.add_separator()
        area_menu.add_command(label="Sil", command=lambda: delete_area(aid))
        try:
            area_menu.tk_popup(event.x_root, event.y_root)
        finally:
            area_menu.grab_release()

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

    def make_tool_tile(parent: tk.Frame, title: str, subtitle: str, hint: str, on_pick) -> None:
        row = tk.Frame(parent, bg=popup_bg)
        row.pack(fill=tk.X, pady=(0, 12))
        btn = tk.Button(
            row,
            text=title,
            command=on_pick,
            cursor="hand2",
            relief=tk.FLAT,
            bg="#f8fafc",
            fg=ink,
            activebackground="#f1f5f9",
            activeforeground=ink,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=14,
            pady=10,
            highlightthickness=1,
            highlightbackground=bar_bd,
        )
        btn.pack(side=tk.LEFT)
        col = tk.Frame(row, bg=popup_bg)
        col.pack(side=tk.LEFT, padx=(12, 0), fill=tk.Y)
        tk.Label(
            col,
            text=subtitle,
            bg=popup_bg,
            fg=muted,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=260,
            justify=tk.LEFT,
        ).pack(anchor="nw")
        btn.bind("<Enter>", lambda _e, h=hint: hint_var.set(h))
        btn.bind("<Leave>", lambda _e: hint_var.set(""))

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

    make_tool_tile(
        cizgiler_popup,
        "Düz çizgi",
        "Tuvale serbest düz çizgi çizer (handle'lara bağlanır).",
        "Düz çizgi: tuvalde tıkla-sürükle-bırak.",
        lambda: (close_top_menus(), set_tool("draw_free_line", "Düz çizgi: tıkla-sürükle-bırak")),
    )

    make_tool_tile(
        alan_popup,
        "Dikdörtgen alan",
        "Kesikli, içi boş alan çerçevesi çizer.",
        "Dikdörtgen alan: tıkla-sürükle-bırak.",
        lambda: (close_top_menus(), set_tool("area_rect", "Alan: dikdörtgen tıkla-sürükle-bırak")),
    )
    make_tool_tile(
        alan_popup,
        "Kare alan",
        "Kesikli, içi boş kare çerçevesi çizer.",
        "Kare alan: tıkla-sürükle-bırak.",
        lambda: (close_top_menus(), set_tool("area_square", "Alan: kare tıkla-sürükle-bırak")),
    )
    make_tool_tile(
        alan_popup,
        "Yuvarlak dikdörtgen alan",
        "Kesikli, içi boş yuvarlak dikdörtgen çizer.",
        "Yuvarlak dikdörtgen: tıkla-sürükle-bırak.",
        lambda: (close_top_menus(), set_tool("area_roundrect", "Alan: yuvarlak dikdörtgen tıkla-sürükle-bırak")),
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
    root.bind_all("<Control-z>", undo)
    canvas.bind("<Enter>", lambda _e: canvas.focus_set())

    root.after_idle(on_resize)
    root.mainloop()
