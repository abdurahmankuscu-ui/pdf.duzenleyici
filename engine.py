"""PDF operations; documents stay in memory until an atomic save."""
from pathlib import Path
import os
import tempfile
import html
import struct
import pymupdf as fitz


def page_range(value, count):
    result = []
    for part in value.split(','):
        bounds = part.strip().split('-')
        if len(bounds) == 1:
            numbers = [int(bounds[0])]
        elif len(bounds) == 2:
            a, b = map(int, bounds)
            if a > b:
                raise ValueError('Aralık başlangıcı bitişten büyük olamaz.')
            numbers = range(a, b + 1)
        else:
            raise ValueError('Örnek sayfa aralığı: 1-3,5')
        for n in numbers:
            if not 1 <= n <= count:
                raise ValueError(f'Sayfa 1 ile {count} arasında olmalı.')
            if n - 1 not in result:
                result.append(n - 1)
    if not result:
        raise ValueError('En az bir sayfa seçin.')
    return result


class Editor:
    def __init__(self):
        self.doc = None
        self.path = None
        self.undo_stack = []
        self.redo_stack = []
        self.dirty = False
        # Password of an opened protected PDF; saves keep it unless changed explicitly.
        self.password = None
        # Opened file carries digital signatures; a normal save invalidates them.
        self.signed = False

    def open(self, path, password=''):
        doc = fitz.open(path)
        # Read needs_pass only before authenticate(): reading it afterwards
        # makes PyMuPDF write undecryptable (empty) content in tobytes().
        protected = doc.needs_pass
        if protected and not doc.authenticate(password):
            doc.close()
            raise ValueError('PDF parolası gerekli veya hatalı.')
        if not doc.is_pdf or not len(doc):
            doc.close()
            raise ValueError('Geçerli, en az bir sayfalı bir PDF seçin.')
        signed = doc.get_sigflags() > 0
        # Detach from the source file so replacing it is safe on Windows.
        data = doc.tobytes()
        doc.close()
        self._replace(data)
        self.path = str(path)
        self.password = password if protected else None
        self.signed = signed
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.dirty = False

    def _replace(self, data):
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(stream=data, filetype='pdf')

    def new(self):
        if self.doc:
            self.doc.close()
        self.doc = fitz.open()
        self.doc.new_page()
        self.path = None
        self.password = None
        self.signed = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.dirty = True

    def change(self, operation):
        before = self.doc.tobytes()
        try:
            operation(self.doc)
        except Exception:
            self._replace(before)
            raise
        self.undo_stack.append(before)
        # Keep history bounded to roughly 128 MB (at least one undo).
        while len(self.undo_stack) > 1 and sum(map(len, self.undo_stack)) > 128 * 1024**2:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.dirty = True

    def undo(self, redo=False):
        source, dest = (self.redo_stack, self.undo_stack) if redo else (self.undo_stack, self.redo_stack)
        if source:
            dest.append(self.doc.tobytes())
            self._replace(source.pop())
            self.dirty = True

    def save(self, path, password=None):
        """password=None keeps the opened document's protection; '' removes it."""
        if password is None:
            password = self.password
        options = dict(garbage=4, deflate=True, use_objstms=1)
        if password:
            options.update(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)
        data = self.doc.tobytes(**options)
        atomic_write(path, data)
        self.path = str(path)
        self.password = password or None
        self.dirty = False
        return len(data)


def atomic_write(path, data):
    path = Path(path)
    fd, temp = tempfile.mkstemp(prefix='.pdfstudio-', suffix='.pdf', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        with fitz.open(temp) as check:
            if not check.is_pdf:
                raise ValueError('PDF doğrulanamadı.')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def add_text(page, rect, text, size=16, color='#172033', *, auto_fit=False,
             min_size=6, compact=False, family='sans-serif', bold=False, italic=False,
             font_data=None, font_name=None):
    if not 0 < size <= 120 or not 0 < min_size <= 120:
        raise ValueError('Geçersiz yazı boyutu.')
    css = f'* {{font-family:{family}; font-size:{size}pt; color:{color};}}'
    if compact:
        css += 'body,div {margin:0;padding:0;line-height:1.1;} div {padding-top:0.25em;padding-bottom:0.15em;}'
    css += f'div {{font-weight:{"bold" if bold else "normal"};font-style:{"italic" if italic else "normal"};}}'
    archive = None
    if font_data:
        font = fitz.Font(fontbuffer=font_data)
        if all(font.has_glyph(ord(c)) for c in text if not c.isspace()):
            archive = fitz.Archive()
            archive.add((font_data, 'original.ttf'))
            css += '@font-face {font-family:Original;src:url(original.ttf);} * {font-family:Original;}'
    spare, scale = page.insert_htmlbox(rect, '<div>' + html.escape(text).replace('\n', '<br>') + '</div>',
        css=css, archive=archive, scale_low=min(1, min_size / size) if auto_fit else 1)
    if spare < 0 or (auto_fit and size * scale + 0.001 < min(size, min_size)):
        detail = f' {min_size:g} puntoya kadar küçültüldüğünde de sığmıyor.' if auto_fit else ''
        raise ValueError('Metin seçilen alana sığmıyor.' + detail + ' Metni kısaltın, alanı büyütün veya yazı boyutunu azaltın.')
    return size * scale


def font_names(data):
    """Read TrueType/OpenType names, including the PDF span's PostScript name."""
    names = []
    try:
        count = struct.unpack_from('>H', data, 4)[0]
        for i in range(count):
            tag, _, offset, _ = struct.unpack_from('>4sIII', data, 12 + i * 16)
            if tag != b'name':
                continue
            _, records, strings = struct.unpack_from('>HHH', data, offset)
            for j in range(records):
                platform, _, _, name_id, length, start = struct.unpack_from('>HHHHHH', data, offset + 6 + j*12)
                if name_id in (1, 4, 6):
                    raw = data[offset+strings+start:offset+strings+start+length]
                    names.append(raw.decode('utf-16-be' if platform in (0, 3) else 'mac_roman'))
    except (struct.error, UnicodeError):
        pass
    return names


def replacement_style(page, rect):
    """Use the dominant intersecting text span, not the toolbar's new-text size."""
    rect = fitz.Rect(rect)
    spans = []
    for block in page.get_text('dict', flags=fitz.TEXTFLAGS_TEXT)['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                intersection = fitz.Rect(span['bbox']) & rect
                if not intersection.is_empty and span['text'].strip():
                    spans.append((intersection.get_area(), span))
    if not spans or not page.get_textbox(rect).strip():
        raise ValueError('Seçilen alanda düzenlenebilir metin bulunamadı. Yazının tamamını seçin; taranmış belgeyse önce OCR uygulayın.')
    span = max(spans, key=lambda entry: entry[0])[1]
    flags = span['flags']
    font_data = None
    wanted = span['font'].split('+')[-1].replace(' ', '').lower()
    for entry in page.get_fonts(full=True):
        data = page.parent.extract_font(entry[0])[3] or None
        names = [entry[3]] + (font_names(data) if data else [])
        if any(n.split('+')[-1].replace(' ', '').lower() == wanted for n in names):
            font_data = data
            if not font_data:
                try:
                    font_data = fitz.Font(fontname=entry[3]).buffer
                except Exception:
                    pass
            break
    return dict(size=max(6, min(120, float(span['size']))), color=f"#{span['color']:06x}",
                font_data=font_data, font_name=span['font'],
                family='monospace' if flags & 8 else ('serif' if flags & 4 else 'sans-serif'),
                bold=bool(flags & 16), italic=bool(flags & 2))


def replace_text(page, rect, text, *, size=None, auto_fit=True, style=None, output_rect=None):
    """Preflight layout before removing text; keep page graphics and images intact."""
    rect = fitz.Rect(rect)
    destination = fitz.Rect(output_rect) if output_rect is not None else rect
    if not (page.rect * page.derotation_matrix).contains(destination):
        raise ValueError('Yazı alanı sayfa sınırlarını aşıyor. Genişliği veya yüksekliği azaltın.')
    style = dict(style or replacement_style(page, rect))
    requested_size = style.pop('size') if size is None else size
    style.pop('size', None)
    if not text.strip():
        raise ValueError('Yeni metni yazın. Metni tamamen kaldırmak için İçeriği sil aracını kullanın.')
    # Lay out on an isolated page so failed edits never leave redactions behind.
    from text_layout import place_text
    with fitz.open() as trial:
        probe = trial.new_page(width=destination.width, height=destination.height)
        used_size = place_text(probe, probe.rect, text, requested_size, auto_fit, style)
    if any(a.type[0] == fitz.PDF_ANNOT_REDACT for a in (page.annots() or [])):
        raise ValueError('Sayfada bekleyen başka redaksiyon işaretleri var. Önce bunları sonuçlandırın.')
    page.add_redact_annot(rect, fill=False)
    page.apply_redactions(images=0, graphics=0, text=0)
    place_text(page, destination, text, requested_size, auto_fit, style)
    return used_size


def erase(page, rect):
    """Remove content in rect, including overlapping notes, links and form fields."""
    rect = fitz.Rect(rect)
    # Collect first: deleting while iterating invalidates PyMuPDF's iterators.
    widgets = [w for w in (page.widgets() or []) if w.rect.intersects(rect)]
    for widget in widgets:
        page.delete_widget(widget)
    annots = [a.xref for a in (page.annots() or []) if a.rect.intersects(rect)
              and a.type[0] != fitz.PDF_ANNOT_REDACT]
    for xref in annots:
        page.delete_annot(page.load_annot(xref))
    for link in [l for l in page.get_links() if fitz.Rect(l['from']).intersects(rect)]:
        page.delete_link(link)
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions(images=2, graphics=2, text=0)


def sanitize(doc):
    """Remove hidden document data. Hidden (OCR) text layers are kept searchable."""
    doc.scrub(attached_files=True, clean_pages=True, embedded_files=True, hidden_text=False,
              javascript=True, metadata=True, redactions=True, remove_links=False,
              reset_fields=False, reset_responses=False, thumbnails=True, xml_metadata=True)


def move_text(page, rect, destination):
    """Move original PDF text drawing commands, retaining embedded fonts exactly."""
    rect, destination = fitz.Rect(rect), fitz.Rect(destination)
    bounds = page.rect * page.derotation_matrix
    if not bounds.contains(destination):
        raise ValueError('Metni sayfa sınırları içinde bırakın.')
    if not page.get_textbox(rect).strip():
        raise ValueError('Taşınacak yazının tamamını seçin.')
    if any(a.type[0] == fitz.PDF_ANNOT_REDACT for a in (page.annots() or [])):
        raise ValueError('Önce bekleyen redaksiyonları sonuçlandırın.')
    with fitz.open() as source:
        source.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
        p = source[0]
        p.set_rotation(0)
        # Keep only text in this disposable copy; no background is moved.
        p.add_redact_annot(p.rect, fill=False)
        p.apply_redactions(images=1, graphics=2, text=1)
        # Remove text outside the clip so it cannot reappear in extraction.
        for area in (fitz.Rect(0,0,p.rect.width,rect.y0),
                     fitz.Rect(0,rect.y1,p.rect.width,p.rect.height),
                     fitz.Rect(0,rect.y0,rect.x0,rect.y1),
                     fitz.Rect(rect.x1,rect.y0,p.rect.width,rect.y1)):
            if not area.is_empty:
                p.add_redact_annot(area, fill=False)
        p.apply_redactions(images=0, graphics=0, text=0)
        page.add_redact_annot(rect, fill=False)
        page.apply_redactions(images=0, graphics=0, text=0)
        page.show_pdf_page(destination, source, 0, clip=rect)


def extract(doc, indices, path):
    with fitz.open() as out:
        for i in indices:
            out.insert_pdf(doc, from_page=i, to_page=i)
        atomic_write(path, out.tobytes(garbage=4, deflate=True))
