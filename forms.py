"""Form fields beyond plain text: check boxes, choices, radio groups; fill and flatten."""
import pymupdf as fitz

FIELD_TYPES = {
    'Metin': fitz.PDF_WIDGET_TYPE_TEXT,
    'Onay kutusu': fitz.PDF_WIDGET_TYPE_CHECKBOX,
    'Açılır liste': fitz.PDF_WIDGET_TYPE_COMBOBOX,
    'Liste': fitz.PDF_WIDGET_TYPE_LISTBOX,
    'Radyo düğmesi': fitz.PDF_WIDGET_TYPE_RADIOBUTTON,
}
CHOICE_TYPES = (fitz.PDF_WIDGET_TYPE_COMBOBOX, fitz.PDF_WIDGET_TYPE_LISTBOX)


def _existing(doc):
    return {w.field_name: w.field_type for p in doc for w in (p.widgets() or [])}


def add_field(page, rect, kind, name, *, options=None, value=None, font_size=11):
    name = name.strip()
    field_type = FIELD_TYPES[kind]
    if not name:
        raise ValueError('Alan adı boş olamaz.')
    existing = _existing(page.parent)
    # Radio buttons share one name per group; every other name must be unique.
    if name in existing and not (field_type == existing[name] == fitz.PDF_WIDGET_TYPE_RADIOBUTTON):
        raise ValueError('Bu alan adı zaten kullanılıyor.')
    widget = fitz.Widget()
    widget.field_name = name
    widget.field_type = field_type
    widget.rect = fitz.Rect(rect)
    widget.text_fontsize = font_size
    widget.border_color = (0.45, 0.4, 0.8)
    widget.border_width = 1
    if field_type in CHOICE_TYPES:
        options = [o.strip() for o in (options or []) if o.strip()]
        if not options:
            raise ValueError('Liste alanı için en az bir seçenek girin.')
        widget.choice_values = options
        widget.field_value = options[0] if field_type == fitz.PDF_WIDGET_TYPE_COMBOBOX else ''
    elif field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
        widget.button_caption = value or name
        widget.field_value = False
    elif field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        widget.field_value = False
    else:
        widget.field_value = value or ''
    page.add_widget(widget)


def fill_field(page, xref, value):
    widget = page.load_widget(xref)
    if widget.field_type in CHOICE_TYPES and value not in (widget.choice_values or []):
        raise ValueError('Seçilen değer bu listenin seçenekleri arasında değil.')
    if widget.field_type in (fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.PDF_WIDGET_TYPE_RADIOBUTTON):
        value = widget.on_state() if value else 'Off'
    widget.field_value = value
    widget.update()


def flatten_forms(doc):
    """Turn form fields into static page content; values can no longer be edited."""
    doc.bake(annots=False, widgets=True)
