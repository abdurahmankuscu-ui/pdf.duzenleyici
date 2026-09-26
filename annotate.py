"""Drawing annotations and the comment list shown in the comments panel."""
import pymupdf as fitz

SHAPES = ('Çizgi', 'Ok', 'Daire')
TYPE_NAMES = {'Text': 'Not', 'FreeText': 'Metin kutusu', 'Highlight': 'Vurgu', 'Underline': 'Altı çizili',
              'StrikeOut': 'Üstü çizili', 'Squiggly': 'Dalgalı çizgi'}
COMMENT_TYPES = {fitz.PDF_ANNOT_TEXT, fitz.PDF_ANNOT_FREE_TEXT, fitz.PDF_ANNOT_HIGHLIGHT,
                 fitz.PDF_ANNOT_UNDERLINE, fitz.PDF_ANNOT_STRIKE_OUT, fitz.PDF_ANNOT_SQUIGGLY}


def add_ink(page, strokes, color=(0.09, 0.13, 0.2), width=2):
    strokes = [[tuple(map(float, p)) for p in stroke] for stroke in strokes if len(stroke) >= 2]
    if not strokes:
        raise ValueError('Çizim için sayfa üzerinde fareyi basılı tutarak sürükleyin.')
    annot = page.add_ink_annot(strokes)
    annot.set_colors(stroke=color)
    annot.set_border(width=width)
    annot.update()
    return annot


def add_shape(page, kind, start, end, color=(0.09, 0.13, 0.2), width=2):
    start, end = fitz.Point(start), fitz.Point(end)
    if abs(start - end) < 2:
        raise ValueError('Şekil çok küçük. Sayfa üzerinde sürükleyin.')
    if kind == 'Daire':
        annot = page.add_circle_annot(fitz.Rect(start, end).normalize())
    elif kind in ('Çizgi', 'Ok'):
        annot = page.add_line_annot(start, end)
        if kind == 'Ok':
            annot.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
    else:
        raise ValueError(f'Bilinmeyen şekil: {kind}')
    annot.set_colors(stroke=color)
    annot.set_border(width=width)
    annot.update()
    return annot


def list_comments(doc):
    comments = []
    for page in doc:
        for annot in page.annots() or []:
            content = annot.info.get('content', '')
            if annot.type[0] in COMMENT_TYPES and (content or annot.type[0] == fitz.PDF_ANNOT_TEXT):
                comments.append(dict(page=page.number, xref=annot.xref, type=TYPE_NAMES.get(annot.type[1], annot.type[1]),
                                     author=annot.info.get('title', ''), content=content,
                                     rect=fitz.Rect(annot.rect)))
    return comments


def set_comment(doc, page, xref, content):
    # Keep the page alive: an annotation of a collected page is unbound.
    page = doc[page]
    annot = page.load_annot(xref)
    annot.set_info(content=content)
    annot.update()


def delete_comment(doc, page, xref):
    page = doc[page]
    page.delete_annot(page.load_annot(xref))
