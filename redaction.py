"""Find personal data by pattern (with checksums) and redact it permanently."""
import re
import pymupdf as fitz
from engine import erase

PATTERNS = {
    'TCKN': re.compile(r'(?<!\d)[1-9]\d{10}(?!\d)'),
    'IBAN': re.compile(r'\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b'),
    'E-posta': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b'),
    'Telefon': re.compile(r'(?<![\d+])(?:\+90[ -]?|0)?\(?5\d{2}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?!\d)'),
}
KINDS = tuple(PATTERNS)


def valid_tckn(value):
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 11 or digits[0] == 0:
        return False
    d10 = (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10
    return digits[9] == d10 and digits[10] == sum(digits[:10]) % 10


def valid_iban(value):
    compact = value.replace(' ', '').upper()
    if not 15 <= len(compact) <= 34 or (compact.startswith('TR') and len(compact) != 26):
        return False
    rearranged = compact[4:] + compact[:4]
    return int(''.join(str(int(c, 36)) for c in rearranged)) % 97 == 1


CHECKS = {'TCKN': valid_tckn, 'IBAN': valid_iban}


def find_sensitive(doc, kinds=KINDS):
    """Return [{'page', 'rect', 'kind', 'text'}]; each occurrence located on its page."""
    hits = []
    for page in doc:
        # Joining lines lets values split across a line break still be found.
        text = page.get_text('text')
        seen = set()
        for kind in kinds:
            for match in PATTERNS[kind].finditer(text):
                value = match.group(0).strip()
                check = CHECKS.get(kind)
                if (check and not check(value)) or (kind, value) in seen:
                    continue
                seen.add((kind, value))
                for rect in page.search_for(value):
                    hits.append(dict(page=page.number, rect=rect, kind=kind, text=value))
    return hits


def redact_hits(doc, hits):
    for hit in hits:
        page = doc[hit['page']]
        # Search coordinates are unrotated page space, as erase() expects.
        erase(page, fitz.Rect(hit['rect']))
