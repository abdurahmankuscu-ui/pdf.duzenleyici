import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import pymupdf as fitz
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
from app import Window


@pytest.fixture
def window(monkeypatch):
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: (_ for _ in ()).throw(AssertionError(str(a))))
    app = QApplication.instance() or QApplication([])
    w = Window()
    w.show()
    w.new()
    yield w
    w.editor.dirty = False
    w.close()


def drag(window, points):
    viewport = window.canvas.viewport()
    positions = [window.canvas.mapFromScene(x, y) for x, y in points]
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=positions[0])
    for pos in positions[1:]:
        QTest.mouseMove(viewport, pos)
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=positions[-1])


def test_freehand_line_arrow_circle(window):
    QApplication.processEvents()
    window.set_mode('Serbest çizim')
    drag(window, [(100, 100), (140, 130), (180, 110), (220, 160)])
    window.set_mode('Ok')
    drag(window, [(100, 300), (300, 350)])
    window.set_mode('Daire')
    drag(window, [(300, 400), (420, 480)])
    page = window.editor.doc[0]
    kinds = [a.type[1] for a in page.annots()]
    assert kinds == ['Ink', 'Line', 'Circle']
    arrow = list(page.annots())[1]
    f = window.canvas.factor
    assert abs(arrow.vertices[0][0] - 100 / f) < 1 and abs(arrow.vertices[1][0] - 300 / f) < 1
    window.undo()
    assert len(list(window.editor.doc[0].annots())) == 2


def test_link_tool_rejects_unsafe_target(window, monkeypatch):
    values = iter([('https://example.com', True), ('javascript:alert(1)', True)])
    monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **k: next(values))
    errors = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: errors.append(a[2]))
    window.set_mode('Bağlantı ekle')
    window.edit_selection(fitz.Rect(50, 50, 150, 70))
    window.edit_selection(fitz.Rect(50, 90, 150, 110))
    assert [l['uri'] for l in window.editor.doc[0].get_links()] == ['https://example.com']
    assert errors and 'izin' in errors[0]


def test_form_field_types_fill_and_flatten(window, monkeypatch):
    answers = iter([('Açılır liste', True), ('Onay kutusu', True)])
    monkeypatch.setattr(QInputDialog, 'getItem', lambda *a, **k: next(answers))
    texts = iter([('sehir', True), ('Ankara, İzmir', True), ('kabul', True)])
    monkeypatch.setattr(QInputDialog, 'getText', lambda *a, **k: next(texts))
    window.set_mode('Form alanı')
    window.edit_selection(fitz.Rect(50, 50, 250, 70))
    window.edit_selection(fitz.Rect(50, 100, 70, 120))
    widgets = {w.field_name: w.field_type_string for w in window.editor.doc[0].widgets()}
    assert widgets == {'sehir': 'ComboBox', 'kabul': 'CheckBox'}
    fills = iter([('1: sehir (Açılır liste)', True), ('İzmir', True)])
    monkeypatch.setattr(QInputDialog, 'getItem', lambda *a, **k: next(fills))
    window.form()
    assert {w.field_name: w.field_value for w in window.editor.doc[0].widgets()}['sehir'] == 'İzmir'
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
    window.flatten_document_forms()
    assert not list(window.editor.doc[0].widgets())


def test_bookmark_dialog_applies_entries(window, monkeypatch):
    import editing_ui
    window.blank()
    def accept(dialog):
        dialog.add_row(1, 'Giriş', 1)
        dialog.add_row(2, 'Alt başlık', 2)
        return True
    monkeypatch.setattr(editing_ui.BookmarkDialog, 'exec', accept)
    window.edit_bookmarks()
    assert window.editor.doc.get_toc() == [[1, 'Giriş', 1], [2, 'Alt başlık', 2]]


def test_comments_panel_lists_edits_and_navigates(window, monkeypatch):
    window.blank()
    window.change(lambda d: d[1].add_text_annot((50, 50), 'İkinci sayfa notu'))
    window.toggle_comments(True)
    assert window.comments_list.count() == 1
    window.comments_list.setCurrentRow(0)
    window.goto_comment()
    assert window.page == 1
    monkeypatch.setattr(QInputDialog, 'getMultiLineText', lambda *a, **k: ('Düzeltildi', True))
    window.edit_comment()
    assert window.comments_list.item(0).text().endswith('Düzeltildi')
    window.delete_comment()
    assert window.comments_list.count() == 0


def test_thumbnail_multi_select_and_reorder(window):
    for _ in range(2):
        window.blank()
    for i in range(3):
        window.change(lambda d, i=i: d[i].insert_text((50, 50), f'P{i+1}'))
    window.thumbs.item(0).setSelected(True)
    window.thumbs.item(2).setSelected(True)
    assert window.selected_pages() == [0, 2]
    window.rotate()
    assert [p.rotation for p in window.editor.doc] == [90, 0, 90]
    # Simulate a drag-and-drop move of the last page to the front.
    item = window.thumbs.takeItem(2)
    window.thumbs.insertItem(0, item)
    window.pages_reordered()
    assert [p.get_text().strip() for p in window.editor.doc] == ['P3', 'P1', 'P2']
    window.undo()
    assert [p.get_text().strip() for p in window.editor.doc] == ['P1', 'P2', 'P3']
