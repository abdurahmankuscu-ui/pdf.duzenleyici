"""Headers, footers, page numbers and Bates numbering on visible page positions."""
import datetime
import html
import pymupdf as fitz

POSITIONS = ('Üst sol', 'Üst orta', 'Üst sağ', 'Alt sol', 'Alt orta', 'Alt sağ')
PLACEHOLDERS = '{n} sayfa no · {toplam} sayfa sayısı · {bates} Bates no · {tarih} bugünün tarihi'


def render_template(template, **values):
    if not template.strip():
        raise ValueError('Damga metni boş olamaz.')
    try:
        return template.format_map(values)
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError(f'Şablon hatalı ({exc}). Kullanılabilir alanlar: {PLACEHOLDERS}') from exc


def _visible_box(page, position, size, margin):
    width, height = page.rect.width, page.rect.height
    box_height = size * 2.2
    y0 = margin if position.startswith('Üst') else height - margin - box_height
    return fitz.Rect(margin, y0, width - margin, y0 + box_height)


def stamp_pages(doc, template, position, *, size=10, start=1, pages=None, bates_prefix='',
                bates_digits=6, color='#172033', margin=24):
    if position not in POSITIONS:
        raise ValueError(f'Konum şunlardan biri olmalı: {", ".join(POSITIONS)}')
    if not 4 <= size <= 72:
        raise ValueError('Yazı boyutu 4 ile 72 arasında olmalı.')
    indices = range(len(doc)) if pages is None else pages
    today = datetime.date.today().strftime('%d.%m.%Y')
    align = {'sol': 'left', 'orta': 'center', 'sağ': 'right'}[position.split()[1]]
    # Validate once before touching any page.
    render_template(template, n=start, toplam=len(doc), bates=f'{bates_prefix}{start:0{bates_digits}d}', tarih=today)
    for offset, index in enumerate(indices):
        page = doc[index]
        number = start + offset
        text = render_template(template, n=number, toplam=len(doc),
                               bates=f'{bates_prefix}{number:0{bates_digits}d}', tarih=today)
        # Position in what the reader sees, then map into unrotated page space.
        box = _visible_box(page, position, size, margin) * page.derotation_matrix
        spare, _ = page.insert_htmlbox(
            box, f'<div style="text-align:{align}">{html.escape(text)}</div>',
            css=f'* {{font-family:sans-serif;font-size:{size}pt;color:{color};}}',
            rotate=page.rotation)
        if spare < 0:
            raise ValueError(f'Sayfa {index+1}: damga metni sayfa genişliğine sığmıyor. Metni kısaltın veya boyutu küçültün.')
