# -*- coding: utf-8 -*-
"""Genera el icono del programa (winstyler.ico) y el logo de la ventana (logo.png)
con el mismo dibujo: módulo oscuro con relieve, tres puntos de color y una barra."""
import os
from PIL import Image, ImageDraw, ImageFilter

S = 1024
PURPLE, MINT, CORAL = (123, 108, 246), (78, 240, 200), (255, 95, 109)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def build():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # sombra inferior derecha
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((90, 110, S - 40, S - 30), 230, fill=(0, 0, 0, 190))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30)))
    # cuerpo con degradado (relieve suave)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        gd.line((0, y, S, y), fill=lerp((48, 53, 74, 255), (24, 27, 38, 255), y / S))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((60, 60, S - 70, S - 70), 230, fill=255)
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    body.paste(grad, (0, 0), mask)
    img.alpha_composite(body)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 60, S - 70, S - 70), 230, outline=(72, 78, 104, 255), width=8)
    # tres puntos con brillo
    cy, r, gap = 400, 82, 236
    cx0 = (S - 10) // 2 - gap
    for i, col in enumerate((PURPLE, MINT, CORAL)):
        cx = cx0 + i * gap
        glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((cx - r - 40, cy - r - 40, cx + r + 40, cy + r + 40), fill=col + (140,))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(34)))
        d = ImageDraw.Draw(img)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,))
        d.ellipse((cx - r * 0.55, cy - r * 0.7, cx + r * 0.25, cy - r * 0.15), fill=(255, 255, 255, 70))
    # barra (línea) debajo
    d.rounded_rectangle((250, 640, S - 260, 692), 26, fill=(70, 76, 102, 255))
    return img


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    big = build()
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(here, "winstyler.ico"), sizes=sizes)
    big.resize((48, 48), Image.LANCZOS).save(os.path.join(here, "logo.png"))
    print("ok")


if __name__ == "__main__":
    main()
