#!/usr/bin/env python3
"""
Kareli not defteri görünümünde basit bir yazı penceresi.
Tkinter standart kütüphanedir; pip gerekmez. Linux’ta genelde:
  sudo apt install python3-tk
Çalıştırma: python3 notepad_grid.py
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import scrolledtext


def _pick_serif(size: int) -> tuple[str, int]:
    for name in ("Georgia", "DejaVu Serif", "Liberation Serif", "Noto Serif", "Times New Roman"):
        if name in tkfont.families():
            return (name, size)
    return ("serif", size)


def draw_grid(canvas: tk.Canvas, cell: int, margin: int, color: str) -> None:
    canvas.delete("grid")
    w = int(canvas.winfo_width())
    h = int(canvas.winfo_height())
    if w <= 1 or h <= 1:
        return
    x0, y0 = margin, margin
    x1, y1 = w - margin, h - margin
    x = x0
    while x <= x1:
        canvas.create_line(x, y0, x, y1, fill=color, width=1, tags="grid")
        x += cell
    y = y0
    while y <= y1:
        canvas.create_line(x0, y, x1, y, fill=color, width=1, tags="grid")
        y += cell


def main() -> None:
    root = tk.Tk()
    root.title("Kareli Not Defteri")
    root.geometry("920x640")
    root.minsize(400, 300)

    paper = "#fefce8"
    grid_color = "#c8c4b8"
    cell = 20
    margin = 40

    canvas = tk.Canvas(root, highlightthickness=0, bg=paper)
    canvas.pack(fill=tk.BOTH, expand=True)

    font_spec = _pick_serif(13)
    text_bg = "#fffef5"
    text = scrolledtext.ScrolledText(
        canvas,
        wrap=tk.WORD,
        font=font_spec,
        bg=text_bg,
        fg="#1c1917",
        insertbackground="#1c1917",
        relief=tk.FLAT,
        borderwidth=0,
        padx=14,
        pady=14,
        highlightthickness=1,
        highlightbackground="#d6d3d1",
        highlightcolor="#a8a29e",
    )

    def place_text() -> None:
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        text.place_configure(
            x=margin,
            y=margin,
            width=max(cw - 2 * margin, 100),
            height=max(ch - 2 * margin, 100),
        )

    def on_configure(_event: tk.Event | None = None) -> None:
        draw_grid(canvas, cell, margin, grid_color)
        place_text()

    canvas.bind("<Configure>", on_configure)
    root.after_idle(on_configure)

    text.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
