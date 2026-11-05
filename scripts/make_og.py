#!/usr/bin/env python3
"""Draw the social share image. usage: uv run --no-project --with pillow python scripts/make_og.py"""
from PIL import Image, ImageDraw, ImageFont

W, H, PAPER, INK, SOFT, POS, NEU, NEG = 1200, 630, "#E8EBE4", "#1A2220", "#55605A", "#F26A00", "#8D968E", "#2340B8"
FONT = "/System/Library/Fonts/HelveticaNeue.ttc"
im = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(im)
d.rectangle([0, 0, W, 14], fill=INK)
d.text((80, 96), "HackerBuys", font=ImageFont.truetype(FONT, 104, index=1), fill=INK)
d.text((84, 232), "The stuff Hacker News", font=ImageFont.truetype(FONT, 56), fill=SOFT)
d.text((84, 298), "actually recommends.", font=ImageFont.truetype(FONT, 56), fill=SOFT)
x = 84
for color, n in ((POS, 62), (NEU, 10), (NEG, 8)):
    for _ in range(n):
        d.rectangle([x, 410, x + 7, 488], fill=color)
        x += 13
d.text((84, 524), "Physical products, ranked by the commenters who own them", font=ImageFont.truetype(FONT, 32), fill=SOFT)
im.save("site/og.png", optimize=True)
