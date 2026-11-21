"""Home page backdrop: the combat still of the link-preview card, as a dim amber/black feed.

    python tools/homebg.py

Needs Pillow. Writes assets/img/home-bg.webp (desktop) and home-bg-s.webp (phones); the output is committed.
The crop leaves out the Conflict PvE badge. The page fades its left edge and draws the HUD
(track box on the lead helicopter, reticle on the far tank) in CSS, at percentages of this crop.
"""
import os
import random

from PIL import Image, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROP = (612, 0, 960, 540)  # right of the badge: helicopters, impact, tank


def feed(height):
    src = Image.open(os.path.join(ROOT, "assets", "img", "mods", "conflict-pve.webp")).convert("RGB").crop(CROP)
    w = round(height * src.width / src.height)
    img = src.resize((w, height), Image.LANCZOS).filter(ImageFilter.GaussianBlur(height / 900))
    lum = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    duo = ImageOps.colorize(lum, black=(4, 6, 8), mid=(96, 60, 14), white=(255, 196, 92), midpoint=150)
    duo = Image.blend(duo, img, 0.18)  # a little of the real fire colour
    # sensor grain, seeded so the file only changes when this script does
    rnd = random.Random(1944)
    noise = Image.new("L", (w, height))
    noise.putdata([rnd.randint(0, 255) for _ in range(w * height)])
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    duo = Image.blend(duo, Image.merge("RGB", (noise, noise, noise)), 0.07)
    return duo


def main():
    for name, h in (("home-bg.webp", 1080), ("home-bg-s.webp", 720)):
        out = os.path.join(ROOT, "assets", "img", name)
        feed(h).save(out, "WEBP", quality=62, method=6)
        print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
