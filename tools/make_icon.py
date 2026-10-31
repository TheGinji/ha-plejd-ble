"""Tekent het icoon van Plejd BLE en schrijft icon.png en icon@2x.png.

Gebruik:  python tools/make_icon.py lijn|huis <doelmap>

Het is een eigen ontwerp. Het bevat geen logo van Plejd of Home Assistant,
alleen de groenblauwe kleur die ook in de Plejd-app wordt gebruikt.
Er zijn geen extra pakketten nodig.
"""

from __future__ import annotations

import math
from pathlib import Path
import struct
import sys
import zlib

SIZE = 512
SUPERSAMPLE = 3
TEAL = (0x48, 0xC5, 0xD6)
WHITE = (255, 255, 255)
GLOW = (255, 214, 102)


def seg_dist(px, py, ax, ay, bx, by):
    """Afstand van een punt tot een lijnstuk."""
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_stroke(x, y, points, half):
    """Zit het punt op een lijn door de gegeven punten?"""
    return any(
        seg_dist(x, y, *points[i], *points[i + 1]) <= half
        for i in range(len(points) - 1)
    )


def round_rect(x, y, x0, y0, x1, y1, radius):
    """Zit het punt in een rechthoek met ronde hoeken?"""
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def arc_round(x, y, cx, cy, radius, half, theta, span):
    """Boog rond hoek theta (graden), met ronde uiteinden."""
    distance = math.hypot(x - cx, y - cy)
    angle = math.degrees(math.atan2(y - cy, x - cx))
    diff = abs(((angle - theta + 180) % 360) - 180)
    if abs(distance - radius) <= half and diff <= span:
        return True
    for sign in (-1, 1):
        ex = cx + radius * math.cos(math.radians(theta + sign * span))
        ey = cy + radius * math.sin(math.radians(theta + sign * span))
        if math.hypot(x - ex, y - ey) <= half:
            return True
    return False


def sample_lijn(x, y):
    """Witte lijnlamp met signaalbogen op groenblauw."""
    color = TEAL
    cx, cy, r, half = 256, 232, 94, 9
    for radius in (130, 166):
        for theta in (0, 180):
            if arc_round(x, y, cx, cy, radius, half, theta, 36):
                color = WHITE
    distance = math.hypot(x - cx, y - cy)
    angle = math.degrees(math.atan2(y - cy, x - cx))
    if abs(distance - r) <= half and (angle <= 52 or angle >= 128):
        color = WHITE
    for ang in (52, 128):
        ex = cx + r * math.cos(math.radians(ang))
        ey = cy + r * math.sin(math.radians(ang))
        if math.hypot(x - ex, y - ey) <= half:
            color = WHITE
    ny = cy + r * math.sin(math.radians(52))
    lx = cx - r * math.cos(math.radians(52))
    rx = cx + r * math.cos(math.radians(52))
    if seg_stroke(x, y, [(lx, ny), (cx - 46, ny + 52), (cx + 46, ny + 52), (rx, ny)], half):
        color = WHITE
    if seg_stroke(x, y, [(cx - 32, ny + 88), (cx + 32, ny + 88)], half):
        color = WHITE
    return color


def sample_huis(x, y):
    """Wit huis met gele lamp en signaalbogen op groenblauw."""
    color = TEAL
    house = [(256, 178), (410, 296), (410, 446), (102, 446), (102, 296)]
    for radius in (50, 88):
        distance = math.hypot(x - 256, y - 168)
        angle = math.degrees(math.atan2(y - 168, x - 256))
        if abs(distance - radius) <= 8 and -145 <= angle <= -35:
            color = WHITE
    if seg_stroke(x, y, house + [house[0]], 13):
        color = WHITE
    bx, by, br = 256, 322, 50
    if (x - bx) ** 2 + (y - by) ** 2 <= br * br:
        color = GLOW
    if bx - 26 <= x <= bx + 26 and by + 40 <= y <= by + 62:
        color = GLOW if y < by + 52 else WHITE
    if round_rect(x, y, bx - 32, by + 64, bx + 32, by + 76, 6):
        color = WHITE
    if round_rect(x, y, bx - 20, by + 82, bx + 20, by + 94, 6):
        color = WHITE
    return color


STYLES = {"lijn": sample_lijn, "huis": sample_huis}


def render(style):
    """Teken het icoon als rijen RGBA-pixels, met zachte randen."""
    draw = STYLES[style]
    rows = []
    for j in range(SIZE):
        row = []
        for i in range(SIZE):
            r = g = b = a = 0
            for sj in range(SUPERSAMPLE):
                for si in range(SUPERSAMPLE):
                    x = i + (si + 0.5) / SUPERSAMPLE
                    y = j + (sj + 0.5) / SUPERSAMPLE
                    if round_rect(x, y, 0, 0, SIZE, SIZE, 112):
                        pr, pg, pb = draw(x, y)
                        r += pr
                        g += pg
                        b += pb
                        a += 1
            total = SUPERSAMPLE * SUPERSAMPLE
            if a:
                row.append((round(r / a), round(g / a), round(b / a), round(255 * a / total)))
            else:
                row.append((0, 0, 0, 0))
        rows.append(row)
    return rows


def downscale(rows):
    """Maak de helft zo groot, met gemiddelde kleuren."""
    out = []
    for j in range(0, len(rows), 2):
        row = []
        for i in range(0, len(rows[j]), 2):
            px = [rows[j][i], rows[j][i + 1], rows[j + 1][i], rows[j + 1][i + 1]]
            alpha = sum(p[3] for p in px)
            if alpha:
                color = tuple(round(sum(p[c] * p[3] for p in px) / alpha) for c in range(3))
                row.append((*color, round(alpha / 4)))
            else:
                row.append((0, 0, 0, 0))
        out.append(row)
    return out


def png_bytes(rows):
    """Zet pixelrijen om naar een PNG-bestand."""
    size = len(rows)
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *px) for px in row) for row in rows
    )

    def chunk(tag, data):
        body = struct.pack(">I", len(data)) + tag + data
        return body + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in STYLES:
        sys.exit(f"Gebruik: python {sys.argv[0]} {'|'.join(STYLES)} <doelmap>")
    style, target = sys.argv[1], Path(sys.argv[2])
    target.mkdir(parents=True, exist_ok=True)
    rows = render(style)
    (target / "icon@2x.png").write_bytes(png_bytes(rows))
    (target / "icon.png").write_bytes(png_bytes(downscale(rows)))
    print(f"Icoon '{style}' geschreven naar {target}")


if __name__ == "__main__":
    main()
