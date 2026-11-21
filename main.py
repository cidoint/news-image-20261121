#!/usr/bin/env python3
"""Deterministically generate a 1024x1024 PNG poster summarizing
21 November 2026's world news, using only the Python standard library.

Run: python3 main.py  ->  writes /output/entry.png
"""
import os
import struct
import zlib

W = H = 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------- PNG writer

def write_png(path, w, h, pix):
    """pix: bytearray of RGB rows (w*h*3 bytes)."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)  # filter: none
        raw += pix[y * stride:(y + 1) * stride]
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- raster ops

def hexc(s):
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def rect(pix, x0, y0, x1, y1, color):
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(W, x1); y1 = min(H, y1)
    r, g, b = color
    stride = W * 3
    for y in range(y0, y1):
        i = y * stride + x0 * 3
        row = bytearray(b"\0") if False else pix  # keep reference
        for x in range(x0, x1):
            pix[i] = r; pix[i + 1] = g; pix[i + 2] = b
            i += 3


def blend(pix, x, y, color, alpha):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        r, g, b = color
        pix[i] = int(pix[i] * (1 - alpha) + r * alpha)
        pix[i + 1] = int(pix[i + 1] * (1 - alpha) + g * alpha)
        pix[i + 2] = int(pix[i + 2] * (1 - alpha) + b * alpha)


def rect_a(pix, x0, y0, x1, y1, color, alpha):
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            blend(pix, x, y, color, alpha)


def fill_ellipse(pix, cx, cy, rx, ry, color):
    for y in range(max(0, cy - ry), min(H, cy + ry + 1)):
        dy2 = ((y - cy) / ry) ** 2
        span = int(rx * max(0.0, 1.0 - dy2) ** 0.5)
        rect(pix, cx - span, y, cx + span + 1, y + 1, color)


def circle_outline(pix, cx, cy, r, color, t=2):
    x, y, err = r, 0, 1 - r
    while x >= y:
        for (px, py) in ((cx + x, cy + y), (cx + y, cy + x), (cx - y, cy + x),
                         (cx - x, cy + y), (cx - x, cy - y), (cx - y, cy - x),
                         (cx + y, cy - x), (cx + x, cy - y)):
            for dx in range(t):
                for dy in range(t):
                    blend(pix, px + dx, py + dy, color, 1.0)
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1


def line(pix, x0, y0, x1, y1, color, t=2):
    dx = abs(x1 - x0); dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        for ox in range(t):
            for oy in range(t):
                blend(pix, x0 + ox, y0 + oy, color, 1.0)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; x0 += sx
        if e2 < dx:
            err += dx; y0 += sy


def triangle(pix, p0, p1, p2, color):
    (x0, y0), (x1, y1), (x2, y2) = p0, p1, p2
    minx = max(0, min(x0, x1, x2)); maxx = min(W - 1, max(x0, x1, x2))
    miny = max(0, min(y0, y1, y2)); maxy = min(H - 1, max(y0, y1, y2))
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for y in range(miny, maxy + 1):
        for x in range(minx, maxx + 1):
            a = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / d
            b = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / d
            c = 1 - a - b
            if a >= 0 and b >= 0 and c >= 0:
                blend(pix, x, y, color, 1.0)


# ---------------------------------------------------------------- 5x7 font

FONT = {
"0":["111","101","101","101","111"],"1":[" 1 ","11 "," 1 "," 1 ","111"],
"2":["111","  1","111","1  ","111"],"3":["111","  1","111","  1","111"],
"4":["1 1","1 1","111","  1","  1"],"5":["111","1  ","111","  1","111"],
"6":["111","1  ","111","1 1","111"],"7":["111","  1","  1","  1","  1"],
"8":["111","1 1","111","1 1","111"],"9":["111","1 1","111","  1","111"],
"A":["111","1 1","111","1 1","1 1"],"B":["110","1 1","110","1 1","110"],
"C":["111","1  ","1  ","1  ","111"],"D":["110","1 1","1 1","1 1","110"],
"E":["111","1  ","111","1  ","111"],"F":["111","1  ","111","1  ","1  "],
"G":["111","1  ","1 1","1 1","111"],"H":["1 1","1 1","111","1 1","1 1"],
"I":["111"," 1 "," 1 "," 1 ","111"],"J":["  1","  1","  1","1 1","111"],
"K":["1 1","1 1","11 ","1 1","1 1"],"L":["1  ","1  ","1  ","1  ","111"],
"M":["1 1","111","111","1 1","1 1"],"N":["1 1","111","111","111","1 1"],
"O":["111","1 1","1 1","1 1","111"],"P":["111","1 1","111","1  ","1  "],
"Q":["111","1 1","1 1","111","  1"],"R":["111","1 1","111","11 ","1 1"],
"S":["111","1  ","111","  1","111"],"T":["111"," 1 "," 1 "," 1 "," 1 "],
"U":["1 1","1 1","1 1","1 1","111"],"V":["1 1","1 1","1 1","1 1"," 1 "],
"W":["1 1","1 1","111","111","1 1"],"X":["1 1","1 1"," 1 ","1 1","1 1"],
"Y":["1 1","1 1"," 1 "," 1 "," 1 "],"Z":["111","  1"," 1 ","1  ","111"],
"a":["   ","   ","111","1 1","111"],"b":["1  ","1  ","111","1 1","111"],
"c":["   ","   ","111","1  ","111"],"d":["  1","  1","111","1 1","111"],
"e":["   ","   ","111","111","111"],"f":[" 11"," 1 ","11 "," 1 "," 1 "],
"g":["   ","111","1 1","111","  1"],"h":["1  ","1  ","111","1 1","1 1"],
"i":[" 1 ","   "," 1 "," 1 "," 1 "],"j":["  1","   ","  1","1 1","111"],
"k":["1  ","1  ","1 1","11 ","1 1"],"l":[" 1 "," 1 "," 1 "," 1 "," 1 "],
"m":["   ","   ","111","111","1 1"],"n":["   ","   ","111","1 1","1 1"],
"o":["   ","   ","111","1 1","111"],"p":["   ","111","1 1","111","1  "],
"q":["   ","111","1 1","111","  1"],"r":["   ","   ","111","1  ","1  "],
"s":["   ","   ","111","11 ","011"],"t":[" 1 "," 1 ","11 "," 1 "," 1 "],
"u":["   ","   ","1 1","1 1","111"],"v":["   ","   ","1 1","1 1"," 1 "],
"w":["   ","   ","1 1","111","111"],"x":["   ","   ","1 1"," 1 ","1 1"],
"y":["   ","1 1","1 1","111","  1"],"z":["   ","   ","111"," 1 ","111"],
" ":["   ","   ","   ","   ","   "],".":["   ","   ","   ","   "," 1 "],
",":["   ","   ","   "," 1 "," 1 "],"-":["   ","   ","111","   ","   "],
"!":[" 1 "," 1 "," 1 ","   "," 1 "],"?":["111","  1"," 11","   "," 1 "],
":":["   "," 1 ","   "," 1 ","   "],"/":["  1","  1"," 1 ","1  ","1  "],
"$":[" 1 ","11 "," 10"," 1 ","111"],"'":[" 1 "," 1 ","   ","   ","   "],
"(":["  1"," 1 "," 1 "," 1 ","  1"],")":["1  "," 1 "," 1 "," 1 ","1  "],
"+":["   "," 1 ","111"," 1 ","   "],"'":[" 1 "," 1 ","   ","   ","   "],
'"':["1 1","1 1","   ","   ","   "],"\u00e9":["111","  1","111","1  ","111"],
}

# wide glyphs for some uppercase-ish accents handled by fallback map
FALLBACK = {"é": "e", "—": "-", "–": "-", "’": "'", "“": '"', "”": '"',
            "…": ".", "é": "e", "è": "e", "à": "a", "ç": "c"}


def draw_text(pix, x, y, text, color, scale=1, spacing=1):
    cx = x
    for ch in text:
        ch = FALLBACK.get(ch, ch) or " "
        gl = FONT.get(ch)
        if gl is None:
            up = ch.upper()
            gl = FONT.get(up, FONT["?"])
        for ry, row in enumerate(gl):
            for rx, c in enumerate(row):
                if c == "1":
                    rect(pix, cx + rx * scale, y + ry * scale,
                         cx + (rx + 1) * scale, y + (ry + 1) * scale, color)
        cx += (3 * scale) + spacing
    return cx - x


def text_width(text, scale=1, spacing=1):
    n = 0
    for ch in text:
        ch = FALLBACK.get(ch, ch)
        if ch not in FONT:
            up = ch.upper()
            ch = up if up in FONT else "?"
        n += 3 * scale + spacing
    return n - spacing if n else 0


def draw_centered(pix, y, text, color, scale=1, spacing=1, max_w=W - 40):
    w = text_width(text, scale, spacing)
    while w > max_w and scale > 1:
        scale -= 1
        w = text_width(text, scale, spacing)
    draw_text(pix, (W - w) // 2, y, text, color, scale, spacing)


# ---------------------------------------------------------------- content

NAVY = hexc("0B1220")
PANEL = hexc("121C2E")
PANEL2 = hexc("182438")
GOLD = hexc("F2C14E")
RED = hexc("E4572E")
TEAL = hexc("2EC4B6")
BLUE = hexc("4EA5D9")
WHITE = hexc("F4F6F8")
GREY = hexc("9AA7B8")
CREAM = hexc("FDF6E3")

HEADLINES = [
    (RED,   "US: Trump warns Iran over 'dirty bomb' plot;"),
    (RED,   "federal jury convicts 2025 Palisades Fire arsonist"),
    (GOLD,  "Strait of Hormuz: two tankers hit as Gulf tension rises"),
    (TEAL,  "COP31 in Turkiye: fossil-fuel row, talks extended"),
    (BLUE,  "UN talks to regulate 'killer robots' by 2028"),
    (BLUE,  "Denmark expels Russian defense attache over plot"),
    (GOLD,  "Germany-Qatar '360-degree' partnership, EUR 15B pledge"),
    (TEAL,  "Bitcoin hits 2-year low; S&P 500 in AI-selloff correction"),
    (RED,   "Ukraine: major Russian missile attack hits Kyiv bridges"),
    (BLUE,  "Japan: pilotless air taxi flies first passenger"),
    (TEAL,  "AI helps solve 167-year-old maths problem (abc conjecture)"),
    (RED,   "Spain: PM Sanchez heading for election defeat"),
]


def main():
    pix = bytearray(W * H * 3)

    # sky gradient background
    top = hexc("0A1024"); bot = hexc("1B2A44")
    for y in range(H):
        t = y / H
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        row = bytearray((r, g, b)) * W
        pix[y * W * 3:(y + 1) * W * 3] = row

    # decorative globe
    fill_ellipse(pix, 830, 180, 110, 110, PANEL2)
    circle_outline(pix, 830, 180, 110, TEAL, 2)
    line(pix, 720, 180, 940, 180, TEAL, 1)
    line(pix, 830, 70, 830, 290, TEAL, 1)
    line(pix, 750, 110, 910, 250, TEAL, 1)
    line(pix, 910, 110, 750, 250, TEAL, 1)

    # masthead
    rect(pix, 0, 0, W, 8, GOLD)
    draw_centered(pix, 34, "THE WORLD IN ONE FRAME", GOLD, 4, 2)
    draw_centered(pix, 92, "21 NOVEMBER 2026", WHITE, 5, 2)
    draw_centered(pix, 140, "global news digest", GREY, 2, 1)

    # flags row (small abstract flags on the globe's left)
    fx = 60
    for colors in ((RED, WHITE), (BLUE, WHITE), (TEAL, WHITE), (GOLD, RED),
                   (WHITE, BLUE), (RED, GOLD)):
        rect(pix, fx, 170, fx + 34, 200, colors[0])
        rect(pix, fx, 185, fx + 34, 200, colors[1])
        line(pix, fx + 17, 165, fx + 17, 205, GREY, 1)
        fx += 52

    # headline panel (drawn after layout is computed)
    y = 274
    line_ys = []
    for color, text in HEADLINES:
        line_ys.append((color, text, y))
        maxw = 880
        if text_width(text, 3, 1) > maxw:
            words = text.split()
            l1 = ""
            i = 0
            while i < len(words) and text_width(l1 + words[i], 3, 1) < maxw:
                l1 += words[i] + " "
                i += 1
            y += 70
        else:
            y += 54
    panel_bottom = y + 14
    rect_a(pix, 40, 250, 984, panel_bottom, PANEL, 0.92)
    rect(pix, 40, 250, 984, 256, GOLD)
    for color, text, ty in line_ys:
        rect(pix, 64, ty + 6, 70, ty + 30, color)
        if text_width(text, 3, 1) > 880:
            words = text.split()
            l1 = ""
            i = 0
            while i < len(words) and text_width(l1 + words[i], 3, 1) < 880:
                l1 += words[i] + " "
                i += 1
            l2 = " ".join(words[i:])
            draw_text(pix, 84, ty, l1.strip(), WHITE, 3, 1)
            draw_text(pix, 84, ty + 30, l2.strip(), WHITE, 3, 1)
        else:
            draw_text(pix, 84, ty + 6, text, WHITE, 3, 1)

    # footer icons row: simple pictograms
    base = 912
    # oil tanker (Hormuz)
    fill_ellipse(pix, 120, base + 20, 30, 12, BLUE)
    rect(pix, 100, base, 140, base + 12, BLUE)
    rect(pix, 112, base - 12, 120, base, RED)
    # climate leaf (COP31)
    fill_ellipse(pix, 280, base + 10, 26, 16, TEAL)
    line(pix, 280, base - 8, 280, base + 26, NAVY, 2)
    # robot chip (killer robots)
    rect(pix, 400, base - 10, 440, base + 30, PANEL2)
    rect(pix, 410, base, 430, base + 20, GOLD)
    circle_outline(pix, 420, base + 10, 6, NAVY, 1)
    # chart down (markets)
    line(pix, 540, base + 26, 560, base + 6, RED, 3)
    line(pix, 560, base + 6, 575, base + 16, RED, 3)
    line(pix, 575, base + 16, 600, base - 4, RED, 3)
    # plane (Japan air taxi)
    triangle(pix, (740, base + 24), (760, base + 2), (780, base + 24), BLUE)
    # euro/ai star
    for ang_pts in ((880, base + 10),):
        fill_ellipse(pix, 880, base + 10, 14, 14, GOLD)
    circle_outline(pix, 880, base + 10, 20, GOLD, 2)

    draw_centered(pix, 960, "AI-RENDERED DAILY BRIEF  |  MADE FOR MAKE.FUN", GREY, 2, 1)
    rect(pix, 0, 1016, W, 1024, GOLD)

    write_png(OUT, W, H, pix)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
