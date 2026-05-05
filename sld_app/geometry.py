"""Saf matematik: üçgen, yay ve mesafe — Tkinter bağımsız."""

from __future__ import annotations

import math


def point_in_triangle(
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


def tri_vertices(s: dict[str, float | str]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
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


def circle_through_three(
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


def tk_angle_deg(ox: float, oy: float, px: float, py: float) -> float:
    """Tk canvas ile uyumlu: 0 doğu, pozitif saat yönü (ekran, +y aşağı)."""
    return math.degrees(math.atan2(-(py - oy), px - ox))


def arc_geometry(
    mx: float,
    my: float,
    nx: float,
    ny: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float, float, float] | None:
    """ox, oy, r, start_deg (Tk), extent_deg (Tk)."""
    circ = circle_through_three(mx, my, nx, ny, cx, cy)
    if circ is None:
        return None
    ox, oy, r = circ
    am = tk_angle_deg(ox, oy, mx, my)
    an = tk_angle_deg(ox, oy, nx, ny)
    ac = tk_angle_deg(ox, oy, cx, cy)

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


def arc_canvas_params(
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
    g = arc_geometry(mx, my, nx, ny, cx, cy)
    if g is None:
        return None
    ox, oy, r, start, extent = g
    x0 = (ox - r - scroll_x) * zoom
    y0 = (oy - r - scroll_y) * zoom
    x1 = (ox + r - scroll_x) * zoom
    y1 = (oy + r - scroll_y) * zoom
    return x0, y0, x1, y1, start, extent


def dist_point_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
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


def point_on_arc_tk(
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
    ap = tk_angle_deg(ox, oy, px, py)

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


def dist_point_arc(
    mx: float,
    my: float,
    nx: float,
    ny: float,
    cx: float,
    cy: float,
    px: float,
    py: float,
) -> float:
    g = arc_geometry(mx, my, nx, ny, cx, cy)
    if g is None:
        return dist_point_segment(px, py, mx, my, nx, ny)
    ox, oy, r, start, extent = g
    if point_on_arc_tk(px, py, ox, oy, r, start, extent):
        pr = math.hypot(px - ox, py - oy)
        return abs(pr - r)
    return min(math.hypot(px - mx, py - my), math.hypot(px - nx, py - ny))
