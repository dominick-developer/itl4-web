from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('static', exist_ok=True)

def make_logo(size, path, show_subtitle=True):
    img = Image.new('RGB', (size, size), '#0B1F33')
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        r = int(11 + (30 - 11) * t)
        g = int(31 + (64 - 31) * t)
        b = int(51 + (175 - 51) * t)
        d.line([(0, y), (size, y)], fill=(r, g, b))
    dot_r = max(3, int(size * 0.028))
    off = int(size * 0.245)
    for cx, cy in [(off, off), (size-off, off), (off, size-off), (size-off, size-off)]:
        d.ellipse([cx-dot_r, cy-dot_r, cx+dot_r, cy+dot_r], fill='#F47721')
    lw = max(1, int(size * 0.008))
    for x1, y1, x2, y2 in [(off, off, size-off, off),(off, size-off, size-off, size-off),(off, off, off, size-off),(size-off, off, size-off, size-off)]:
        d.line([(x1, y1), (x2, y2)], fill='#F47721', width=lw)
    def try_font(names, size_):
        for n in names:
            try: return ImageFont.truetype(n, size_)
            except Exception: continue
        return ImageFont.load_default()
    f_big = try_font(['arialbd.ttf','Arial Bold.ttf','arial.ttf'], int(size * 0.34))
    f_med = try_font(['arialbd.ttf','arial.ttf'], int(size * 0.095))
    f_sm  = try_font(['arial.ttf'], int(size * 0.055))
    d.text((size/2, size*0.50), 'IT', fill='#F47721', anchor='mm', font=f_big)
    if show_subtitle:
        d.text((size/2, size*0.665), 'LEVEL 4', fill='white', anchor='mm', font=f_med)
        d.text((size/2, size*0.755), 'CONNECT', fill='#94a3b8', anchor='mm', font=f_sm)
    img.save(path, 'PNG', optimize=True)
    print(f'OK  {path}  ({size}x{size})')

make_logo(512, 'static/logo.png', True)
make_logo(192, 'static/icon-192.png', True)
make_logo(512, 'static/icon-512.png', True)
print('\nTayari! Picha 3 zimeundwa kwenye static/')
