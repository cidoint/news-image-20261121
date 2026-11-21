#!/usr/bin/env python3
"""Deterministic 1024x1024 world-news poster -> /output/entry.png.

Pure Python 3 standard library.  The PNG is written by hand (zlib + struct),
text is drawn with a hand-coded 5x7 bitmap font, and shapes are drawn with a
hand-written rasterizer.  No network, no randomness, no timestamps: two runs
produce a byte-identical file.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# --------------------------------------------------------------------------
# Hand-coded 5x7 bitmap font.  Each glyph is 7 rows of 5 columns, written as
# little ASCII-art strings ('#' = lit).  bit 0 of a row mask is the leftmost
# column; bit 4 is the rightmost column.
# --------------------------------------------------------------------------
_FONT_RAW = {
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".###.", "#...#", "#....", ".###.", "....#", "#...#", ".###."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ',': (".....", ".....", ".....", ".....", "..#..", "..#..", ".#..."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '&': (".##..", "#..#.", "#..#.", ".##..", "#.#.#", "#..#.", ".##.#"),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    'a': (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".###.", "#....", "#....", "#...#", ".###."),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    'g': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    'j': ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    'q': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "###..", ".#...", ".#...", ".#..#", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", ".....", "#...#", "#...#", "#...#", ".####", "....#"),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
}


def _mask(row):
    m = 0
    for c in range(5):
        if row[c] == '#':
            m |= 1 << c
    return m


FONT = {ch: tuple(_mask(r) for r in rows) for ch, rows in _FONT_RAW.items()}

ADV = 6  # advance width (5 glyph columns + 1 spacing column)


# --------------------------------------------------------------------------
# Rasterizer helpers
# --------------------------------------------------------------------------
def px(fb, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = x * 3
        fb[y][i] = c[0]
        fb[y][i + 1] = c[1]
        fb[y][i + 2] = c[2]


def fill_rect(fb, x0, y0, x1, y1, c):
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x1 > W:
        x1 = W
    if y1 > H:
        y1 = H
    if x0 >= x1 or y0 >= y1:
        return
    seg = bytes((c[0], c[1], c[2])) * (x1 - x0)
    for y in range(y0, y1):
        fb[y][x0 * 3:x1 * 3] = seg


def draw_line(fb, x0, y0, x1, y1, c):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(fb, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_circle(fb, cx, cy, r, c):
    x = r
    y = 0
    err = 1 - r
    while x >= y:
        for dx, dy in ((x, y), (-x, y), (x, -y), (-x, -y),
                       (y, x), (-y, x), (y, -x), (-y, -x)):
            px(fb, cx + dx, cy + dy, c)
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1


def fill_disc(fb, cx, cy, r, c):
    r2 = r * r
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r2:
                px(fb, cx + dx, cy + dy, c)


def _plot4(fb, cx, cy, x, y, c):
    px(fb, cx + x, cy + y, c)
    px(fb, cx - x, cy + y, c)
    px(fb, cx + x, cy - y, c)
    px(fb, cx - x, cy - y, c)


def draw_ellipse(fb, cx, cy, rx, ry, c):
    """Integer midpoint ellipse (outline only)."""
    rx2 = rx * rx
    ry2 = ry * ry
    two_rx2 = 2 * rx2
    two_ry2 = 2 * ry2
    x = 0
    y = ry
    px_ = 0
    py_ = two_rx2 * y
    p = ry2 - rx2 * ry + (rx2 >> 2)
    while px_ < py_:
        _plot4(fb, cx, cy, x, y, c)
        x += 1
        px_ += two_ry2
        if p < 0:
            p += ry2 + px_
        else:
            y -= 1
            py_ -= two_rx2
            p += ry2 + px_ - py_
    p = ry2 * (x * x + x) + rx2 * (y - 1) * (y - 1) - rx2 * ry2
    while y >= 0:
        _plot4(fb, cx, cy, x, y, c)
        y -= 1
        py_ -= two_rx2
        if p > 0:
            p += rx2 - py_
        else:
            x += 1
            px_ += two_ry2
            p += rx2 - py_ + px_


def text_width(text, scale):
    return ADV * len(text) * scale


def draw_text(fb, text, x, y, scale, color):
    for ch in text:
        g = FONT.get(ch, FONT['?'])
        for r in range(7):
            bits = g[r]
            for c in range(5):
                if bits & (1 << c):
                    fill_rect(fb, x + c * scale, y + r * scale,
                              x + (c + 1) * scale, y + (r + 1) * scale, color)
        x += ADV * scale


def wrap_text(text, scale, max_px):
    words = text.split(' ')
    lines = []
    cur = ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, scale) <= max_px:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def _lighten(c, t):
    return tuple(int(v + (255 - v) * t) for v in c)


def _darken(c, t):
    return tuple(int(v * (1.0 - t)) for v in c)


def _mix(c0, c1, t):
    return tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))


# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------
HEADLINES = [
    "US: Trump warns Iran over 'dirty bomb' plot",
    "federal jury convicts 2025 Palisades Fire arsonist",
    "Strait of Hormuz: two tankers hit as Gulf tension rises",
    "COP31 in Turkiye: fossil-fuel row, talks extended",
    "UN talks to regulate 'killer robots' by 2028",
    "Denmark expels Russian defense attache over plot",
    "Germany-Qatar '360-degree' partnership, EUR 15B pledge",
    "Bitcoin hits 2-year low",
    "S&P 500 in AI-selloff correction",
    "Ukraine: major Russian missile attack hits Kyiv bridges",
    "Japan: pilotless air taxi flies first passenger",
    "AI helps solve 167-year-old maths problem (abc conjecture)",
    "Spain: PM Sanchez heading for election defeat",
]

PALETTE = [
    (235, 80, 80),
    (240, 150, 60),
    (60, 180, 170),
    (80, 190, 110),
    (170, 100, 220),
    (225, 90, 180),
    (160, 120, 70),
    (250, 205, 60),
    (80, 130, 230),
    (235, 95, 75),
    (80, 200, 160),
    (205, 115, 225),
    (240, 130, 95),
]


# --------------------------------------------------------------------------
# PNG encoding (hand-written)
# --------------------------------------------------------------------------
def _chunk(typ, data):
    out = struct.pack('>I', len(data)) + typ + data
    out += struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def encode_png(fb):
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for row in fb:
        raw.append(0)  # filter type 0: None
        raw.extend(row)
    idat = zlib.compress(bytes(raw), 9)
    return (b'\x89PNG\r\n\x1a\n'
            + _chunk(b'IHDR', ihdr)
            + _chunk(b'IDAT', idat)
            + _chunk(b'IEND', b''))


# --------------------------------------------------------------------------
# Layout / composition
# --------------------------------------------------------------------------
def main():
    band = (26, 33, 52)
    cream = (240, 235, 220)
    gold = (214, 178, 90)
    ink = (222, 224, 232)

    bg_top = (21, 27, 44)
    bg_bottom = (9, 12, 21)
    fb = []
    for y in range(H):
        c = _mix(bg_top, bg_bottom, y / (H - 1))
        fb.append(bytearray(bytes((c[0], c[1], c[2])) * W))

    # Top masthead band.
    fill_rect(fb, 0, 0, W, 200, band)

    title = "THE WORLD IN ONE FRAME"
    tscale = 4
    draw_text(fb, title, (W - text_width(title, tscale)) // 2, 40, tscale, cream)

    # Small gold rule under the title.
    fill_rect(fb, (W - 320) // 2, 78, (W + 320) // 2, 80, gold)

    sub = "21 NOVEMBER 2026"
    sscale = 2
    draw_text(fb, sub, (W - text_width(sub, sscale)) // 2, 90, sscale, gold)

    # Decorative globe (top-right of the band).
    gx, gy, gr = 930, 100, 34
    fill_disc(fb, gx, gy, gr, (40, 86, 140))
    grid = (150, 205, 240)
    draw_circle(fb, gx, gy, gr, grid)
    draw_line(fb, gx - gr, gy, gx + gr, gy, grid)          # equator
    draw_line(fb, gx, gy - gr, gx, gy + gr, grid)          # prime meridian
    draw_ellipse(fb, gx, gy, gr // 2, gr, grid)            # meridian arc

    # A row of abstract flags.
    fw, fh, fgap = 26, 16, 8
    n = len(PALETTE)
    row_w = n * fw + (n - 1) * fgap
    fx0 = (W - row_w) // 2
    fy = 150
    for i, c in enumerate(PALETTE):
        x0 = fx0 + i * (fw + fgap)
        fill_rect(fb, x0, fy, x0 + fw, fy + 5, c)
        fill_rect(fb, x0, fy + 5, x0 + fw, fy + 11, _lighten(c, 0.55))
        fill_rect(fb, x0, fy + 11, x0 + fw, fy + fh, _darken(c, 0.55))
        outline = (8, 10, 16)
        draw_line(fb, x0, fy, x0 + fw - 1, fy, outline)
        draw_line(fb, x0, fy + fh - 1, x0 + fw - 1, fy + fh - 1, outline)
        draw_line(fb, x0, fy, x0, fy + fh - 1, outline)
        draw_line(fb, x0 + fw - 1, fy, x0 + fw - 1, fy + fh - 1, outline)

    # Divider between band and body.
    fill_rect(fb, 40, 201, W - 40, 203, gold)

    # Headlines (vertically centered in the body area).
    hscale = 3
    line_h = 28
    gap = 12
    bullet_r = 6
    x_text = 84
    x_bullet = 58
    max_px = W - x_text - 72

    total = 0
    for h in HEADLINES:
        total += len(wrap_text(h, hscale, max_px)) * line_h
    total += (len(HEADLINES) - 1) * gap

    body_top, body_bottom = 224, 936
    y = body_top + (body_bottom - body_top - total) // 2

    for idx, h in enumerate(HEADLINES):
        lines = wrap_text(h, hscale, max_px)
        for j, ln in enumerate(lines):
            if j == 0:
                fill_disc(fb, x_bullet, y + 10, bullet_r, PALETTE[idx])
            draw_text(fb, ln, x_text, y, hscale, ink)
            y += line_h
        y += gap

    # Footer strip.
    fill_rect(fb, 0, 940, W, H, band)
    fill_rect(fb, 0, 940, W, 942, gold)
    ft1 = "THE WORLD IN ONE FRAME"
    ft2 = "13 stories - 21 November 2026 - one deterministic frame"
    ft1_scale = 2
    ft2_scale = 1
    ft_gap = 12
    ft_block_h = 7 * ft1_scale + ft_gap + 7 * ft2_scale
    strip_top, strip_bottom = 940, H
    ft_y = strip_top + (strip_bottom - strip_top - ft_block_h) // 2
    draw_text(fb, ft1, (W - text_width(ft1, ft1_scale)) // 2, ft_y, ft1_scale, cream)
    draw_text(fb, ft2, (W - text_width(ft2, ft2_scale)) // 2,
              ft_y + 7 * ft1_scale + ft_gap, ft2_scale, gold)

    os.makedirs('/output', exist_ok=True)
    with open('/output/entry.png', 'wb') as f:
        f.write(encode_png(fb))


if __name__ == '__main__':
    main()
