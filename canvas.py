"""终端画布：真彩单元格、宽字符、按行 diff 输出。"""

from __future__ import annotations

import unicodedata

Color = tuple[int, int, int]

BG = (6, 8, 14)
PANEL = (13, 17, 27)
PANEL2 = (18, 23, 36)
INK = (226, 231, 238)
DIM = (126, 136, 158)
FAINT = (64, 74, 96)

TEAL = (72, 230, 200)
GREEN = (126, 240, 158)
AMBER = (255, 190, 92)
PINK = (255, 108, 170)
PURPLE = (178, 128, 255)
RED = (255, 86, 98)
BLUE = (96, 164, 255)
WHITE = (248, 248, 242)

Cell = tuple[str, Color, Color, bool]


def mix(c1: Color, c2: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return (
        round(c1[0] + (c2[0] - c1[0]) * t),
        round(c1[1] + (c2[1] - c1[1]) * t),
        round(c1[2] + (c2[2] - c1[2]) * t),
    )


def scale(c: Color, k: float) -> Color:
    return (
        max(0, min(255, round(c[0] * k))),
        max(0, min(255, round(c[1] * k))),
        max(0, min(255, round(c[2] * k))),
    )


def wcw(ch: str) -> int:
    if not ch:
        return 0
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def twidth(s: str) -> int:
    return sum(wcw(ch) for ch in s)


def truncate(s: str, width: int, ellipsis: str = "…") -> str:
    if width <= 0:
        return ""
    if twidth(s) <= width:
        return s
    out = []
    used = 0
    limit = max(0, width - twidth(ellipsis))
    for ch in s:
        w = wcw(ch)
        if used + w > limit:
            break
        out.append(ch)
        used += w
    return "".join(out) + ellipsis


def style(fg: Color, bg: Color, bold: bool) -> str:
    parts = [f"38;2;{fg[0]};{fg[1]};{fg[2]}", f"48;2;{bg[0]};{bg[1]};{bg[2]}"]
    if bold:
        parts.append("1")
    return "\x1b[" + ";".join(parts) + "m"


class Canvas:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.rows: list[list[Cell]] = [
            [(" ", INK, BG, False) for _ in range(w)] for _ in range(h)
        ]

    def _clear(self, x: int, y: int) -> None:
        row = self.rows[y]
        ch = row[x][0]
        if ch == "":
            if x > 0:
                row[x - 1] = (" ", INK, BG, False)
            row[x] = (" ", INK, BG, False)
        elif wcw(ch) == 2:
            if x + 1 < self.w:
                row[x + 1] = (" ", INK, BG, False)

    def put(self, x: int, y: int, text: str, fg: Color | None = None,
            bg: Color | None = None, bold: bool = False) -> int:
        if y < 0 or y >= self.h:
            return x
        fg = fg or INK
        bg = bg or BG
        cx = x
        row = self.rows[y]
        for ch in text:
            w = wcw(ch)
            if w <= 0:
                continue
            if cx < 0:
                cx += w
                continue
            if cx >= self.w or cx + w > self.w:
                break
            self._clear(cx, y)
            row[cx] = (ch, fg, bg, bold)
            if w == 2:
                row[cx + 1] = ("", fg, bg, bold)
            cx += w
        return cx

    def fill(self, x: int, y: int, w: int, h: int, ch: str = " ",
             fg: Color | None = None, bg: Color | None = None) -> None:
        x0, x1 = max(0, x), min(self.w, x + w)
        y0, y1 = max(0, y), min(self.h, y + h)
        if x0 >= x1 or y0 >= y1:
            return
        cell = (ch, fg or INK, bg or BG, False)
        for yy in range(y0, y1):
            row = self.rows[yy]
            # 别把横跨边界的宽字符切一半
            if x0 > 0 and row[x0][0] == "":
                row[x0 - 1] = (" ", INK, BG, False)
            if 0 < x1 < self.w and wcw(row[x1 - 1][0]) == 2:
                row[x1] = (" ", INK, BG, False)
            for xx in range(x0, x1):
                row[xx] = cell

    def hline(self, x: int, y: int, w: int, ch: str = "─",
              fg: Color | None = None, bg: Color | None = None) -> None:
        if 0 <= y < self.h:
            self.put(x, y, ch * max(0, w), fg, bg)

    def vline(self, x: int, y: int, h: int, ch: str = "│",
              fg: Color | None = None, bg: Color | None = None) -> None:
        for yy in range(max(0, y), min(self.h, y + h)):
            self.put(x, yy, ch, fg, bg)

    def box(self, x: int, y: int, w: int, h: int, fg: Color = DIM,
            bg: Color = BG, title: str = "", title_fg: Color | None = None,
            fill: bool = True) -> None:
        if w < 2 or h < 2:
            return
        if fill:
            self.fill(x, y, w, h, " ", INK, bg)
        self.put(x, y, "┌" + "─" * (w - 2) + "┐", fg, bg)
        self.put(x, y + h - 1, "└" + "─" * (w - 2) + "┘", fg, bg)
        self.vline(x, y + 1, h - 2, "│", fg, bg)
        self.vline(x + w - 1, y + 1, h - 2, "│", fg, bg)
        if title:
            label = f" {title} "
            if twidth(label) <= w - 4:
                self.put(x + 2, y, label, title_fg or fg, bg, bold=True)

    def right(self, x: int, y: int, text: str, fg: Color | None = None,
              bg: Color | None = None, bold: bool = False) -> None:
        self.put(x - twidth(text), y, text, fg, bg, bold)

    def center(self, y: int, text: str, fg: Color | None = None,
               bg: Color | None = None, bold: bool = False) -> None:
        self.put(max(0, (self.w - twidth(text)) // 2), y, text, fg, bg, bold)

    def cursor(self, x: int, y: int, ch: str = " ") -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            _, fg, bg, bold = self.rows[y][x]
            self.rows[y][x] = (ch or " ", bg, fg, bold)

    def bar(self, x: int, y: int, width: int, ratio: float, full: str = "█",
            empty: str = "░", fg: Color = TEAL, bg: Color = BG) -> None:
        ratio = max(0.0, min(1.0, ratio))
        n = int(round(width * ratio))
        self.put(x, y, full * n, fg, bg)
        self.put(x + n, y, empty * (width - n), FAINT, bg)

    @staticmethod
    def _row_ansi(row: list[Cell]) -> str:
        out: list[str] = []
        cur: tuple[Color, Color, bool] | None = None
        for ch, fg, bg, bold in row:
            if ch == "":
                continue
            st = (fg, bg, bold)
            if st != cur:
                out.append(style(fg, bg, bold))
                cur = st
            out.append(ch)
        return "".join(out)

    def render(self, prev: list[str] | None = None) -> tuple[str, list[str]]:
        out: list[str] = []
        rows: list[str] = []
        for y, row in enumerate(self.rows):
            line = self._row_ansi(row)
            rows.append(line)
            if prev is None or y >= len(prev) or prev[y] != line:
                out.append(f"\x1b[{y + 1};1H{line}\x1b[0m")
        return "".join(out), rows
