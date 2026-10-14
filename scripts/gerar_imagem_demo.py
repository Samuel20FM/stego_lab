"""Gera uma imagem de teste (paisagem sintética) para a demonstração.

Uso:  python scripts/gerar_imagem_demo.py   ->  assets/demo_paisagem.png
Não contém dados pessoais e não depende da Internet.
"""

from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 960, 600
OUT = Path(__file__).resolve().parent.parent / "assets" / "demo_paisagem.png"


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def main() -> None:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):  # céu em degradê
        draw.line([(0, y), (W, y)], fill=lerp((14, 30, 72), (250, 160, 90), y / H))
    draw.ellipse((620, 250, 760, 390), fill=(255, 214, 140))  # sol

    rng = random.Random(2026)
    layers = [((40, 52, 92), 360), ((28, 38, 70), 420), ((16, 24, 46), 480)]
    for colour, base in layers:  # montanhas
        pts, x = [(0, H)], 0
        while x <= W:
            pts.append((x, base - rng.randint(0, 120)))
            x += rng.randint(60, 140)
        pts += [(W, base), (W, H)]
        draw.polygon(pts, fill=colour)

    for _ in range(140):  # estrelas
        x, y = rng.randrange(W), rng.randrange(200)
        draw.point((x, y), fill=(230, 235, 255))

    img = img.filter(ImageFilter.SMOOTH)
    # ruído ligeiro para parecer uma fotografia
    px = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            n = rng.randint(-4, 4)
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    img.save(OUT)
    print(f"Imagem criada: {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
