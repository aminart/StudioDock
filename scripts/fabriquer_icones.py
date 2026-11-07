"""Fabrique <nom>.ico (Windows) et <nom>.icns (Mac) à partir de resources/icons/<nom>.svg et <nom>-petit.svg.

Usage : python scripts/fabriquer_icones.py resources/icons resources studiodock
Demande rsvg-convert (librsvg) et Pillow."""
import io, subprocess, sys, pathlib
from PIL import Image, ImageFilter
icons = pathlib.Path(sys.argv[1]); dest = pathlib.Path(sys.argv[2]); nom = sys.argv[3]

def rendu(svg, taille):
    png = subprocess.run(['rsvg-convert', '-w', str(taille), '-h', str(taille), str(svg)],
                         check=True, capture_output=True).stdout
    return Image.open(io.BytesIO(png)).convert('RGBA')

def source(taille):
    return icons / (f'{nom}-petit.svg' if taille <= 48 else f'{nom}.svg')

# Windows : l'icône remplit le carré
ico = [rendu(source(t), t) for t in (16, 24, 32, 48, 64, 128, 256)]
ico[-1].save(dest / f'{nom}.ico', format='ICO', sizes=[i.size for i in ico], append_images=ico[:-1])

# Mac : grille Apple, la tuile occupe ~80 % du canevas avec une ombre portée
def mac(t):
    canevas = Image.new('RGBA', (t, t), (0, 0, 0, 0))
    cote = round(t * 824 / 1024); marge = (t - cote) // 2
    tuile = rendu(source(t), cote)
    if t >= 64:
        ombre = Image.new('RGBA', (t, t), (0, 0, 0, 0))
        masque = tuile.split()[3].point(lambda a: a * 0.35)
        ombre.paste((0, 0, 0, 255), (marge, marge + max(1, t // 100)), masque)
        canevas = Image.alpha_composite(canevas, ombre.filter(ImageFilter.GaussianBlur(max(1, t / 90))))
    calque = Image.new('RGBA', (t, t), (0, 0, 0, 0)); calque.paste(tuile, (marge, marge))
    return Image.alpha_composite(canevas, calque)

tailles = (16, 32, 64, 128, 256, 512, 1024)
images = [mac(t) for t in tailles]
images[-1].save(dest / f'{nom}.icns', format='ICNS', append_images=images[:-1])
print('ok')
