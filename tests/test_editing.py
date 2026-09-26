import pymupdf as fitz
import pytest


@pytest.fixture
def doc():
    d = fitz.open()
    for _ in range(3):
        d.new_page()
    yield d
    d.close()


def test_drawing_annotations(doc):
    from annotate import add_ink, add_shape
    page = doc[0]
    add_ink(page, [[(10, 10), (40, 30), (80, 20)]], color=(1, 0, 0), width=2)
    add_shape(page, 'Çizgi', (100, 100), (200, 150), color=(0, 0, 1))
    add_shape(page, 'Ok', (100, 200), (200, 250), color=(0, 0, 1))
    add_shape(page, 'Daire', (300, 300), (380, 360), color=(0, 0.5, 0))
    kinds = [a.type[1] for a in page.annots()]
    assert kinds == ['Ink', 'Line', 'Line', 'Circle']
    arrow = list(page.annots())[2]
    assert arrow.line_ends[1] != fitz.PDF_ANNOT_LE_NONE
    with pytest.raises(ValueError):
        add_ink(page, [[(1, 1)]])


def test_comments_list_edit_delete(doc):
    from annotate import list_comments, set_comment, delete_comment
    doc[0].add_text_annot((50, 50), 'İlk not')
    third = doc[2]
    highlight = third.add_highlight_annot(fitz.Rect(50, 100, 200, 120))
    highlight.set_info(content='Vurgu yorumu')
    highlight.update()
    doc[1].add_rect_annot(fitz.Rect(10, 10, 20, 20))  # no text: not a comment
    comments = list_comments(doc)
    assert [(c['page'], c['content']) for c in comments] == [(0, 'İlk not'), (2, 'Vurgu yorumu')]
    set_comment(doc, comments[0]['page'], comments[0]['xref'], 'Güncellendi')
    delete_comment(doc, comments[1]['page'], comments[1]['xref'])
    assert [c['content'] for c in list_comments(doc)] == ['Güncellendi']


def test_bookmarks_roundtrip_and_validation(doc):
    from outline import get_bookmarks, set_bookmarks
    set_bookmarks(doc, [(1, 'Giriş', 1), (2, 'Ayrıntı', 2), (1, 'Son', 3)])
    assert get_bookmarks(doc) == [(1, 'Giriş', 1), (2, 'Ayrıntı', 2), (1, 'Son', 3)]
    for bad in ([(2, 'Başsız', 1)], [(1, 'Sayfa yok', 9)], [(1, '', 1)], [(1, 'A', 1), (3, 'Atlama', 1)]):
        with pytest.raises(ValueError):
            set_bookmarks(doc, bad)
    assert len(get_bookmarks(doc)) == 3


def test_links_only_allow_safe_targets(doc):
    from outline import add_link
    rect = fitz.Rect(50, 50, 150, 70)
    add_link(doc[0], rect, 'https://example.com')
    add_link(doc[0], rect + (0, 40, 0, 40), 'mailto:bilgi@example.com')
    add_link(doc[0], rect + (0, 80, 0, 80), 3)
    links = doc[0].get_links()
    assert [l.get('uri') for l in links[:2]] == ['https://example.com', 'mailto:bilgi@example.com']
    assert links[2]['page'] == 2
    for target in ('javascript:alert(1)', 'file:///C:/Windows/system32/calc.exe', 'C:\\x.exe', 7, 0):
        with pytest.raises(ValueError):
            add_link(doc[0], rect, target)


def test_form_fields_and_flatten(doc, tmp_path):
    from forms import add_field, flatten_forms
    page = doc[0]
    add_field(page, fitz.Rect(50, 50, 70, 70), 'Onay kutusu', 'kabul')
    add_field(page, fitz.Rect(50, 100, 250, 120), 'Açılır liste', 'sehir', options=['Ankara', 'İzmir'])
    add_field(page, fitz.Rect(50, 150, 250, 210), 'Liste', 'renk', options=['Mavi', 'Yeşil'])
    add_field(page, fitz.Rect(50, 250, 70, 270), 'Radyo düğmesi', 'cinsiyet', value='a')
    add_field(page, fitz.Rect(90, 250, 110, 270), 'Radyo düğmesi', 'cinsiyet', value='b')
    with pytest.raises(ValueError):
        add_field(page, fitz.Rect(50, 300, 250, 320), 'Açılır liste', 'bos', options=[])
    with pytest.raises(ValueError):
        add_field(page, fitz.Rect(50, 300, 250, 320), 'Onay kutusu', 'kabul')
    path = tmp_path / 'form.pdf'
    doc.save(path)
    with fitz.open(path) as saved:
        types = sorted(w.field_type_string for w in saved[0].widgets())
        assert types == ['CheckBox', 'ComboBox', 'ListBox', 'RadioButton', 'RadioButton']
        flatten_forms(saved)
        assert not list(saved[0].widgets())
        assert saved[0].get_drawings() or saved[0].get_text()


def test_fill_any_field(doc):
    from forms import add_field, fill_field
    page = doc[0]
    add_field(page, fitz.Rect(50, 50, 70, 70), 'Onay kutusu', 'kabul')
    add_field(page, fitz.Rect(50, 100, 250, 120), 'Açılır liste', 'sehir', options=['Ankara', 'İzmir'])
    fields = {w.field_name: w.xref for w in page.widgets()}
    fill_field(page, fields['kabul'], True)
    fill_field(page, fields['sehir'], 'İzmir')
    with pytest.raises(ValueError):
        fill_field(page, fields['sehir'], 'Bursa')
    values = {w.field_name: w.field_value for w in page.widgets()}
    assert values['sehir'] == 'İzmir' and values['kabul'] not in (False, 'Off', '')


def test_page_order_operations(doc):
    from pages import reorder, rotate_pages
    for i, page in enumerate(doc):
        page.insert_text((50, 50), f'P{i+1}')
    reorder(doc, [2, 0, 1])
    assert [p.get_text().strip() for p in doc] == ['P3', 'P1', 'P2']
    with pytest.raises(ValueError):
        reorder(doc, [0, 0, 1])
    rotate_pages(doc, [0, 2])
    assert [p.rotation for p in doc] == [90, 0, 90]
