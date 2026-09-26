"""Bookmarks (table of contents) and links with a safe-target policy."""
from urllib.parse import urlparse
import pymupdf as fitz

# Links that launch programs, read local files or run scripts are refused.
SAFE_SCHEMES = {'http', 'https', 'mailto'}


def get_bookmarks(doc):
    return [(level, title, page) for level, title, page, *_ in doc.get_toc(simple=True)]


def set_bookmarks(doc, entries):
    previous = 0
    for level, title, page in entries:
        if not str(title).strip():
            raise ValueError('Yer imi başlığı boş olamaz.')
        if not 1 <= page <= len(doc):
            raise ValueError(f'“{title}” için sayfa 1 ile {len(doc)} arasında olmalı.')
        if level < 1 or level > previous + 1:
            raise ValueError(f'“{title}” düzeyi hatalı: ilk yer imi 1. düzeyde olmalı ve düzey bir adımda en fazla 1 artabilir.')
        previous = level
    doc.set_toc([[level, str(title).strip(), page] for level, title, page in entries])


def add_link(page, rect, target):
    rect = fitz.Rect(rect)
    if isinstance(target, int):
        if not 1 <= target <= len(page.parent):
            raise ValueError(f'Hedef sayfa 1 ile {len(page.parent)} arasında olmalı.')
        link = dict(kind=fitz.LINK_GOTO, page=target - 1, to=fitz.Point(0, 0), **{'from': rect})
    else:
        target = str(target).strip()
        if urlparse(target).scheme.lower() not in SAFE_SCHEMES:
            raise ValueError('Yalnızca http://, https:// ve mailto: bağlantılarına izin verilir.')
        link = dict(kind=fitz.LINK_URI, uri=target, **{'from': rect})
    page.insert_link(link)
