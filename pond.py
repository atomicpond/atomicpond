"""Render rain on a pond as a looping animated ASCII SVG, different each day.

The pond is a height field h(x, y, t) over a grid of characters. Drops land at
places and times picked from the date, so every day has its own pond. Frames
are stacked into a vertical film strip and the SVG scrolls through them with
a stepped CSS animation, so the result works anywhere an <img> does (GitHub
included): no JavaScript, no external fonts.

    python3 pond.py [OUT_DIR] [--date YYYY-MM-DD]
"""

import argparse
import datetime
import math
import random
from html import escape
from pathlib import Path

COLS, ROWS = 96, 22
SECONDS, FPS = 9.0, 10

# A monospace cell is about half as wide as it is tall, so horizontal
# distances count half when measuring how far a point is from a drop.
ASPECT = 0.5

FONT_SIZE = 14
CHAR_W = FONT_SIZE * 0.6
LINE_H = CHAR_W / ASPECT

FONT = 'ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace'
COLORS = {"light": "#59636e", "dark": "#9198a1"}

# Calm water is left blank; crests draw the rings, troughs faint dots.
CRESTS = ".:-=+*#%"
TROUGHS = "··.."


def rain(day):
    """Drops as (x, y, seconds into the loop), picked from the date."""
    rng = random.Random(day.isoformat())
    return [
        (rng.uniform(4, COLS - 4), rng.uniform(2, ROWS - 2), rng.uniform(0, SECONDS))
        for _ in range(rng.randint(7, 11))
    ]


def pond(drops, speed=9.0, k=1.4, width=4.0, fade=2.2):
    """Height of the water: each drop sends out one fading ring per loop.

    Ages wrap around the loop, so a ring still fading at the end carries on
    at the start and the animation loops without a jump.
    """

    def h(x, y, t):
        total = 0.0
        for dx, dy, when in drops:
            age = (t * SECONDS - when) % SECONDS
            front = speed * age
            r = math.hypot((x - dx) * ASPECT, y - dy)
            behind = front - r
            if behind < -width or behind > 3 * width:
                continue
            envelope = math.exp(-((behind - width) / (1.4 * width)) ** 2)
            strength = math.exp(-age / fade) / math.sqrt(1 + 0.25 * front)
            total += strength * envelope * math.cos(k * behind)
        return total

    return h


def shade(v, calm=0.06):
    if abs(v) < calm:
        return " "
    if v > 0:
        return CRESTS[min(len(CRESTS) - 1, int((v - calm) * len(CRESTS) * 1.6))]
    return TROUGHS[min(len(TROUGHS) - 1, int((-v - calm) * len(TROUGHS) * 2))]


def frame(h, t):
    return [
        "".join(shade(h(x, y, t)) for x in range(COLS)).rstrip()
        for y in range(ROWS)
    ]


def svg(frames, color):
    width = COLS * CHAR_W
    height = ROWS * LINE_H
    n = len(frames)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Rain on a pond, in ASCII">',
        "<style>",
        f"text{{font-family:{FONT};font-size:{FONT_SIZE}px;fill:{color};white-space:pre}}",
        f"#s{{animation:roll {SECONDS}s steps({n}) infinite}}",
        f"@keyframes roll{{to{{transform:translateY(-{n * height:.1f}px)}}}}",
        "@media (prefers-reduced-motion:reduce){#s{animation:none}}",
        "</style>",
        '<g id="s">',
    ]
    for i, lines in enumerate(frames):
        top = i * height
        for j, line in enumerate(lines):
            if not line:
                continue
            y = top + (j + 0.8) * LINE_H
            out.append(
                f'<text x="0" y="{y:.1f}" xml:space="preserve" textLength="{len(line) * CHAR_W:.1f}" '
                f'lengthAdjust="spacing">{escape(line, quote=False)}</text>'
            )
    out += ["</g>", "</svg>"]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", nargs="?", default="dist")
    parser.add_argument("--date", type=datetime.date.fromisoformat,
                        default=datetime.datetime.now(datetime.timezone.utc).date())
    args = parser.parse_args()

    h = pond(rain(args.date))
    n = round(SECONDS * FPS)
    frames = [frame(h, i / n) for i in range(n)]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for theme, color in COLORS.items():
        (out_dir / f"pond-{theme}.svg").write_text(svg(frames, color))
    print(f"{args.date}: {len(frames)} frames written to {out_dir}/")


if __name__ == "__main__":
    main()
