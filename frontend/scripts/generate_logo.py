"""Generate the GlamTok logo assets (favicon.ico, logo192.png, logo512.png).

Design: deep-rose rounded tile (#B33E5D) with a cream (#FFF9F6) analytics
pulse line + glam sparkle glyph. The deep-rose tile reads clearly on both
light and dark browser tabs, matching the app's rose theme.

Run from the repo root:  python frontend/scripts/generate_logo.py
"""
import os

from PIL import Image, ImageDraw

TILE = "#B33E5D"    # deep rose (--accent-strong)
GLYPH = "#FFF9F6"   # warm cream (--bg)

# Glyph coordinates from the 24x24 SVG in Sidebar.js
PULSE = [(2.5, 12.5), (7.5, 12.5), (10, 5.5), (13.5, 19), (16, 12.5), (21.5, 12.5)]
SPARKLE = [
    (19.3, 1.6), (20, 4.7), (23.1, 5.4), (20, 6.1),
    (19.3, 9.2), (18.6, 6.1), (15.5, 5.4), (18.6, 4.7),
]


def draw_logo(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=TILE)

    s = size / 24.0
    pulse = [(x * s, y * s) for x, y in PULSE]
    sparkle = [(x * s, y * s) for x, y in SPARKLE]

    d.line(pulse, fill=GLYPH, width=max(2, int(size * 0.09)), joint="curve")
    d.polygon(sparkle, fill=GLYPH)
    return img


def main():
    public_dir = os.path.join(os.path.dirname(__file__), "..", "public")

    img48, img32, img16 = draw_logo(48), draw_logo(32), draw_logo(16)
    img48.save(
        os.path.join(public_dir, "favicon.ico"),
        format="ICO",
        sizes=[(48, 48), (32, 32), (16, 16)],
        append_images=[img32, img16],
    )
    draw_logo(192).save(os.path.join(public_dir, "logo192.png"))
    draw_logo(512).save(os.path.join(public_dir, "logo512.png"))
    print("Wrote favicon.ico, logo192.png, logo512.png to", public_dir)


if __name__ == "__main__":
    main()
