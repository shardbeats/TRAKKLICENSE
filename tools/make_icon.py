#!/usr/bin/env python3
"""Generate icon.ico (+ icon.png preview) with Pillow. No external assets.

Design: dark rounded square (app theme #141414) + gold (#f5a623) beamed
eighth-notes (beat) over a thin gold seal ring (license). Bold shapes only
so it reads at 16px. Run: python tools/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SIZE = 256
BG = (20, 20, 20, 255)
GOLD = (245, 166, 35, 255)


def draw_icon(size: int = SIZE) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256  # scale factor

    # dark rounded square
    d.rounded_rectangle([4 * s, 4 * s, 252 * s, 252 * s], radius=52 * s, fill=BG)
    # thin gold inner ring
    d.rounded_rectangle([14 * s, 14 * s, 242 * s, 242 * s], radius=44 * s,
                        outline=GOLD, width=max(1, int(5 * s)))

    # beamed eighth-note pair (heads + stems + beam)
    def note(cx, cy, r):
        d.ellipse([cx - r, cy - r * 0.75, cx + r, cy + r * 0.75], fill=GOLD)

    r = 26 * s
    # left note (lower) + right note (higher)
    note(88 * s, 176 * s, r)
    note(168 * s, 156 * s, r)
    stem_w = 11 * s
    d.rectangle([104 * s, 62 * s, 104 * s + stem_w, 172 * s], fill=GOLD)
    d.rectangle([184 * s, 42 * s, 184 * s + stem_w, 152 * s], fill=GOLD)
    # beam connecting stem tops (slanted)
    d.polygon([(104 * s, 62 * s), (195 * s, 42 * s),
               (195 * s, 66 * s), (104 * s, 86 * s)], fill=GOLD)
    return img


def main() -> int:
    img = draw_icon()
    img.save(ROOT / "icon.png")
    img.save(ROOT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32),
                                       (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"OK: icon.ico + icon.png ({ROOT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
