#!/usr/bin/env python3
"""Draw the make.fun news-image entry for Thursday 19 November 2026.

One self-contained program: it paints a 1024x1024 PNG with the Python
Imaging Library only (standard library + Pillow), using fixed coordinates
and fixed colours, so every run produces byte-identical output. No network,
no clock, no randomness.

Layout, top to bottom:
  * a navy masthead naming the day: THURSDAY 19 NOVEMBER 2026
  * a dusk-sky hero scene, drawn by hand: a globe, a city skyline, a
    rocket on its way out (Voyager), and a rising market line (the IPO)
  * four numbered stories, each a short headline plus one factual subline

Run it:  python3 main.py
It writes entry.png next to this file and also copies it to
$MAKEFUN_OUTPUT_DIR (or /output when that variable is unset).
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1024
HEIGHT = 1024
MAX_BYTES = 1_048_576

HERE = Path(__file__).resolve().parent
ENTRY_NAME = "entry.png"

# ---------------------------------------------------------------- fonts ---

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
BOLD_PATH = FONT_DIR / "DejaVuSans-Bold.ttf"
REGULAR_PATH = FONT_DIR / "DejaVuSans.ttf"


def bold(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BOLD_PATH), size)


def regular(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(REGULAR_PATH), size)


def text_width(draw: ImageDraw.ImageDraw, text: str,
               font: ImageFont.FreeTypeFont) -> int:
    left, _top, right, _bottom = draw.textbbox((0, 0), text, font=font)
    return right - left


def wrap(draw: ImageDraw.ImageDraw, text: str,
         font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Greedy word wrap; returns at most the lines that fit."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if text_width(draw, trial, font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ------------------------------------------------------------- palette ----

NAVY = (15, 30, 58)          # masthead
NAVY_DEEP = (10, 20, 40)
GOLD = (212, 175, 105)
CREAM = (248, 246, 239)      # story band
INK = (20, 38, 63)           # headline text
GREY = (74, 85, 104)         # subline text
HAIRLINE = (214, 210, 198)

# One accent per story: summit, markets, games, space.
ACCENTS = [(31, 78, 121), (14, 124, 107), (107, 63, 160), (194, 94, 30)]

STORIES = [
    (
        "Trump, Xi and Putin hold first trilateral summit",
        "APEC Shenzhen \u2014 nuclear arms, Ukraine and Iran on the agenda",
        "SUMMIT",
    ),
    (
        "Anthropic prices record $81.3bn IPO at $83 a share",
        "Biggest IPO ever; shares debut on Nasdaq today as ANT, ~$1.5tn value",
        "MARKETS",
    ),
    (
        "Grand Theft Auto VI rolls out worldwide after 13 years",
        "Vice City opens to rave reviews \u2014 Metacritic 99",
        "GAMES",
    ),
    (
        "NASA confirms Voyager 1 is one light-day from Earth",
        "Farthest human-made object, 49 years after launch",
        "SPACE",
    ),
]


# ------------------------------------------------------------ sky & sea ---

def vertical_gradient(size: tuple[int, int],
                      stops: list[tuple[float, tuple[int, int, int]]]
                      ) -> Image.Image:
    """A smooth vertical gradient through the given (position, colour) stops."""
    width, height = size
    base = Image.new("RGB", (1, height))
    px = base.load()
    for y in range(height):
        pos = y / max(height - 1, 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= pos <= p1:
                span = max(p1 - p0, 1e-9)
                mix = (pos - p0) / span
                px[0, y] = tuple(
                    round(c0[k] + (c1[k] - c0[k]) * mix) for k in range(3)
                )
                break
        else:
            px[0, y] = stops[-1][1]
    return base.resize((width, height))


def draw_stars(draw: ImageDraw.ImageDraw,
               points: list[tuple[int, int, int]]) -> None:
    """Fixed stars: (x, y, radius) triples, four-point sparkle each."""
    for x, y, r in points:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
        draw.line([x - r * 2, y, x + r * 2, y], fill=(255, 255, 255), width=1)
        draw.line([x, y - r * 2, x, y + r * 2], fill=(255, 255, 255), width=1)


def draw_globe(canvas: Image.Image, centre: tuple[int, int],
               radius: int) -> None:
    """A stylised Earth: blue disc, green land blobs, pale graticule."""
    globe = Image.new("RGBA", (radius * 2 + 8, radius * 2 + 8), (0, 0, 0, 0))
    g = ImageDraw.Draw(globe)
    cx = cy = radius + 4
    # Ocean: concentric discs, deep at the rim, lighter toward the light.
    for r in range(radius, 0, -6):
        shade = 0.55 + 0.45 * (1 - r / radius)
        blue = (
            round(28 + 70 * shade),
            round(88 + 70 * shade),
            round(138 + 60 * shade),
        )
        g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=blue + (255,))
    # Landmasses: simple rounded blobs, placed to suggest continents.
    land = (86, 158, 94)
    blobs = [
        (cx - 88, cy - 62, cx - 28, cy - 6),
        (cx - 52, cy - 84, cx + 6, cy - 34),
        (cx + 18, cy - 58, cx + 82, cy + 2),
        (cx - 78, cy + 18, cx - 8, cy + 66),
        (cx + 12, cy + 28, cx + 66, cy + 78),
        (cx + 58, cy - 88, cx + 96, cy - 52),
    ]
    for box in blobs:
        g.ellipse(box, fill=land + (255,))
    g.polygon(
        [(cx - 40, cy - 30), (cx + 10, cy - 44), (cx + 34, cy - 8),
         (cx - 6, cy + 6)],
        fill=land + (255,),
    )
    # Graticule: two meridians and two parallels, clipped to the disc.
    pale = (190, 220, 240, 110)
    for dx in (-52, 0, 52):
        g.arc([cx + dx - 66, cy - radius, cx + dx + 66, cy + radius],
              start=250, end=290, fill=pale, width=2)
    for dy in (-48, 44):
        g.arc([cx - radius, cy + dy - 70, cx + radius, cy + dy + 70],
              start=200, end=340, fill=pale, width=2)
    # Terminator: a soft dark crescent on the lower right, blended over
    # the ocean on its own layer, then clipped to the disc so nothing
    # spills past the globe's rim.
    term = Image.new("RGBA", globe.size, (0, 0, 0, 0))
    term_draw = ImageDraw.Draw(term)
    term_draw.ellipse([cx + radius // 3, cy - radius, cx + radius * 2,
                       cy + radius], fill=(8, 18, 38, 70))
    globe = Image.alpha_composite(globe, term)
    clip = Image.new("L", globe.size, 0)
    clip_draw = ImageDraw.Draw(clip)
    clip_draw.ellipse([4, 4, radius * 2 + 4, radius * 2 + 4], fill=255)
    globe.putalpha(clip)
    # Rim light and outline (rebind the draw handle: alpha_composite
    # returned a new image above).
    g = ImageDraw.Draw(globe)
    g.ellipse([4, 4, radius * 2 + 4, radius * 2 + 4],
              outline=(220, 235, 245, 255), width=3)
    # Paste using the globe layer's own alpha channel as the mask, so the
    # semi-transparent terminator and graticule blend instead of stamping
    # in solid. (Passing the separate L mask would ignore that alpha.)
    canvas.paste(globe, (centre[0] - radius - 4, centre[1] - radius - 4),
                 globe)


def draw_skyline(draw: ImageDraw.ImageDraw, base_y: int,
                 heights: list[int], widths: list[int]) -> None:
    """A dark city silhouette with a few lit windows, left to right."""
    x = 0
    for height, width in zip(heights, widths):
        top = base_y - height
        draw.rectangle([x, top, x + width, base_y], fill=NAVY_DEEP)
        # A lit window or two on the taller towers, fixed positions.
        if height > 52:
            draw.rectangle([x + width // 3, top + 12, x + width // 3 + 5,
                            top + 17], fill=(255, 214, 120))
        if height > 76:
            draw.rectangle([x + width // 2 + 4, top + 30,
                            x + width // 2 + 9, top + 35],
                           fill=(255, 214, 120))
        x += width
    # A slim antenna on the tallest tower (the 108px tower at x 186-240,
    # whose top sits at base_y - 108).
    draw.line([213, base_y - 108, 213, base_y - 128],
              fill=NAVY_DEEP, width=3)
    draw.ellipse([210, base_y - 132, 216, base_y - 126],
                 fill=(255, 90, 80))


def draw_rocket(draw: ImageDraw.ImageDraw, tip: tuple[int, int]) -> None:
    """A small white rocket climbing to the upper right, with a dotted path."""
    x, y = tip
    # Dotted flight path curving in from the lower left.
    for i, (px, py) in enumerate([(x - 190, y + 150), (x - 150, y + 118),
                                  (x - 112, y + 88), (x - 76, y + 60),
                                  (x - 44, y + 34), (x - 18, y + 12)]):
        r = 3 if i % 2 == 0 else 2
        draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255))
    # Body: nose cone, fuselage, fins, window, flame.
    draw.polygon([(x, y), (x - 16, y + 26), (x + 16, y + 26)],
                 fill=(214, 72, 60))
    draw.polygon([(x - 16, y + 26), (x + 16, y + 26), (x + 13, y + 72),
                  (x - 13, y + 72)], fill=(245, 245, 240))
    draw.polygon([(x - 13, y + 52), (x - 30, y + 82), (x - 13, y + 76)],
                 fill=(214, 72, 60))
    draw.polygon([(x + 13, y + 52), (x + 30, y + 82), (x + 13, y + 76)],
                 fill=(214, 72, 60))
    draw.ellipse([x - 7, y + 36, x + 7, y + 50], fill=(120, 190, 230))
    draw.ellipse([x - 4, y + 39, x + 4, y + 47], fill=(210, 240, 250))
    draw.polygon([(x - 9, y + 72), (x + 9, y + 72), (x, y + 98)],
                 fill=(255, 176, 66))
    draw.polygon([(x - 5, y + 72), (x + 5, y + 72), (x, y + 88)],
                 fill=(255, 230, 140))


def draw_rising_line(draw: ImageDraw.ImageDraw,
                     points: list[tuple[int, int]]) -> None:
    """A gold market line climbing to the right, with dots at each step."""
    draw.line(points, fill=GOLD, width=4, joint="curve")
    for px, py in points:
        draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=GOLD)
        draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 255, 255))
    # Arrowhead on the last point.
    lx, ly = points[-1]
    draw.polygon([(lx, ly - 14), (lx + 16, ly + 2), (lx - 2, ly + 2)],
                 fill=GOLD)


# -------------------------------------------------------------- the image ---

def build_image() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), CREAM)
    draw = ImageDraw.Draw(img)

    # --- masthead ------------------------------------------------------
    draw.rectangle([0, 0, WIDTH, 118], fill=NAVY)
    kicker = regular(24)
    kicker_text = "W O R L D   N E W S   I N   O N E   I M A G E"
    kw = text_width(draw, kicker_text, kicker)
    draw.text(((WIDTH - kw) / 2, 16), kicker_text, font=kicker, fill=GOLD)
    date_font = bold(46)
    date_text = "THURSDAY 19 NOVEMBER 2026"
    dw = text_width(draw, date_text, date_font)
    draw.text(((WIDTH - dw) / 2, 52), date_text, font=date_font,
              fill=(255, 255, 255))
    draw.rectangle([0, 116, WIDTH, 118], fill=GOLD)

    # --- hero scene ----------------------------------------------------
    hero_top, hero_bottom = 118, 520
    sky = vertical_gradient(
        (WIDTH, hero_bottom - hero_top),
        [(0.0, (16, 32, 64)), (0.55, (38, 74, 110)), (1.0, (196, 128, 84))],
    )
    img.paste(sky, (0, hero_top))
    draw = ImageDraw.Draw(img)
    draw_stars(draw, [
        (880, 150, 3), (940, 200, 2), (820, 230, 2), (700, 160, 2),
        (120, 180, 2), (60, 260, 3), (210, 150, 2), (990, 320, 2),
        (760, 300, 2), (160, 330, 2),
    ])
    draw_globe(img, (330, 318), 118)
    draw = ImageDraw.Draw(img)
    draw_rocket(draw, (880, 190))
    # Skyline along the foot of the hero, then the market line over it so
    # the gold climb stays visible above the rooftops.
    draw_skyline(draw, hero_bottom, [64, 92, 58, 108, 74, 48, 96, 66, 84, 54,
                                     100, 62, 78, 46, 88, 58, 70],
                 [62, 58, 66, 54, 60, 64, 58, 62, 56, 66, 58, 62, 56, 64, 58,
                  62, 60])
    draw_rising_line(draw, [(660, 448), (730, 420), (800, 430),
                            (870, 392), (940, 366)])
    draw.rectangle([0, hero_bottom - 2, WIDTH, hero_bottom], fill=GOLD)

    # --- the four stories ----------------------------------------------
    row_top = hero_bottom
    row_height = (HEIGHT - hero_bottom) // 4
    for index, (headline, subline, _tag) in enumerate(STORIES):
        top = row_top + index * row_height
        accent = ACCENTS[index]
        # Number chip.
        chip = (36, top + 34, 92, top + 90)
        draw.rounded_rectangle(chip, radius=10, fill=accent)
        number = bold(34)
        digit = str(index + 1)
        nw = text_width(draw, digit, number)
        draw.text((chip[0] + (56 - nw) / 2, chip[1] + 8), digit,
                  font=number, fill=(255, 255, 255))
        # Headline, one line when it fits, two short lines when it does not.
        text_x = 112
        max_w = WIDTH - text_x - 36
        head_font = bold(30)
        lines = wrap(draw, headline, head_font, max_w)
        if len(lines) > 2:
            lines = lines[:2]
        if len(lines) == 2:
            head_font = bold(26)
            lines = wrap(draw, headline, head_font, max_w)[:2]
            line_h = 32
            y = top + 22
        else:
            line_h = 36
            y = top + 26
        for line in lines:
            draw.text((text_x, y), line, font=head_font, fill=INK)
            y += line_h
        sub_font = regular(23)
        sub_lines = wrap(draw, subline, sub_font, max_w)
        draw.text((text_x, y + 4), sub_lines[0], font=sub_font, fill=GREY)
        if index < 3:
            sep_y = top + row_height
            draw.line([36, sep_y, WIDTH - 36, sep_y], fill=HAIRLINE, width=1)
    return img


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    image = build_image()
    if image.size != (WIDTH, HEIGHT):
        print(f"FAIL: image is {image.size}, expected {(WIDTH, HEIGHT)}",
              file=sys.stderr)
        return 1

    local_path = HERE / ENTRY_NAME
    image.save(local_path, format="PNG")
    size = local_path.stat().st_size
    if size > MAX_BYTES:
        print(f"FAIL: entry.png is {size} bytes, over the {MAX_BYTES} limit",
              file=sys.stderr)
        return 1

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ENTRY_NAME
    if out_path.resolve() != local_path.resolve():
        shutil.copyfile(local_path, out_path)

    print(f"entry.png: {size} bytes, {WIDTH}x{HEIGHT}, "
          f"sha256 {sha256_file(local_path)}")
    print(f"wrote {local_path} and {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
