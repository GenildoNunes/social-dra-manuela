"""Gera marca/logo.png e marca/simbolo.png (fundo transparente) a partir do logo sobre fundo branco.

Uso:  python scripts/preparar_marca.py caminho/do/logo.jpg
A cor final do logo é aplicada no template (CSS mask), então aqui só importa o formato.
"""
import sys
from pathlib import Path

from PIL import Image

MARCA = Path(__file__).resolve().parent.parent / "marca"


def recortar(img):
    return img.crop(img.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox())


def main(origem):
    logo = Image.open(origem).convert("RGB")
    # Quanto mais longe do branco, mais opaco.
    alfa = logo.convert("L").point(lambda v: max(0, min(255, int((255 - v) * 2.2))))
    rgba = Image.new("RGBA", logo.size, (0, 0, 0, 255))
    rgba.putalpha(alfa)
    completo = recortar(rgba)
    completo.save(MARCA / "logo.png")

    # Símbolo = o coração à esquerda, até a primeira coluna vazia.
    a = completo.getchannel("A")
    cw, ch = completo.size
    corte = next((x for x in range(int(cw * 0.15), int(cw * 0.5))
                  if a.crop((x, 0, x + 1, ch)).getextrema()[1] < 40), int(cw * 0.3))
    recortar(completo.crop((0, 0, corte, ch))).save(MARCA / "simbolo.png")
    print("ok", completo.size)


if __name__ == "__main__":
    main(sys.argv[1])
