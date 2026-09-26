import pymupdf as fitz
import pytest
from engine import Editor, add_text, replacement_style, replace_text


def test_two_line_replacement_can_enlarge_area_without_erasing_neighbor():
    editor=Editor();editor.new()
    p=editor.doc[0]
    p.insert_text((50,90),'Original',fontsize=9)
    p.insert_text((50,106),'Keep neighbour',fontsize=9)
    rect=p.search_for('Original')[0]
    before=p.get_text()
    with pytest.raises(ValueError):
        editor.change(lambda d:replace_text(d[0],rect,'Sayın\nHAMDİ DOKGÖZ',size=6))
    assert editor.doc[0].get_text()==before
    enlarged=fitz.Rect(rect.x0,rect.y0,rect.x0+130,rect.y0+36)
    editor.change(lambda d:replace_text(d[0],rect,'Sayın\nHAMDİ DOKGÖZ',size=9,output_rect=enlarged))
    text=editor.doc[0].get_text()
    assert 'HAMDİ DOKGÖZ' in text and 'Keep neighbour' in text and 'Original' not in text
    editor.undo();assert editor.doc[0].get_text()==before
    editor.doc.close()


def test_area_controls_retry_without_losing_draft():
    from PySide6.QtWidgets import QApplication
    from text_dialog import ReplaceTextDialog
    app=QApplication.instance() or QApplication([])
    editor=Editor();editor.new();p=editor.doc[0]
    p.insert_text((50,90),'Original',fontsize=9)
    rect=p.search_for('Original')[0]
    def apply(value,size,auto):
        used=[]
        editor.change(lambda d:used.append(replace_text(d[0],rect,value,size=size,auto_fit=auto,output_rect=dialog.output_rect())))
        return used[0]
    dialog=ReplaceTextDialog(None,'Original',9,apply)
    dialog.configure_area(rect,p.rect)
    dialog.text.setPlainText('Sayın\nHAMDİ DOKGÖZ')
    dialog.apply()
    assert dialog.result()==0 and dialog.text.toPlainText()=='Sayın\nHAMDİ DOKGÖZ'
    dialog.area_width.setValue(50);dialog.area_height.setValue(15)
    dialog.apply()
    assert dialog.result()==1
    assert 'HAMDİ DOKGÖZ' in editor.doc[0].get_text()
    editor.doc.close()


def test_embedded_arial_preserved():
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_font(fontname='original', fontfile='C:/Windows/Fonts/arial.ttf')
        page.insert_text((50,90), 'Original', fontname='original', fontsize=12)
        rect = page.search_for('Original')[0]+(-1,-2,20,2)
        style = replacement_style(page, rect)
        assert style['font_data']
        replace_text(page, rect, 'Updated')
        span = page.get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
        assert span['font'] == style['font_name']


def test_canvas_drag_moves_selected_text(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt, QPointF
    from PySide6.QtTest import QTest
    from app import Window
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.new()
    window.editor.doc[0].insert_text((50,90), 'Move me', fontsize=12)
    window.render()
    window.show()
    app.processEvents()
    rect = window.editor.doc[0].search_for('Move me')[0]+(-2,-2,2,2)
    window.set_mode('Metni taşı')
    window.edit_selection(rect)
    canvas = window.canvas
    start = canvas.mapFromScene(canvas.move_region.center())
    end = canvas.mapFromScene(canvas.move_region.center()+QPointF(100,80))
    warnings = []
    monkeypatch.setattr(QMessageBox,'warning',lambda *args: warnings.append(args))
    QTest.mousePress(canvas.viewport(),Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(canvas.viewport(),end)
    QTest.mouseRelease(canvas.viewport(),Qt.MouseButton.LeftButton,pos=end)
    assert not warnings
    assert window.editor.doc[0].search_for('Move me')[0].x0 > 110
    window.editor.dirty = False
    window.close()


@pytest.mark.parametrize('rotation', [0,90,180,270])
def test_move_preserves_font_color_background_and_undo(rotation):
    from engine import move_text
    editor = Editor()
    editor.new()
    page = editor.doc[0]
    page.insert_text((50,90), 'Original', fontsize=12, fontname='hebo', color=(1,0,0))
    page.insert_text((50,150), 'Keep', fontsize=12)
    page.draw_rect(fitz.Rect(30,40,300,250),fill=(0.8,0.9,1))
    rect = page.search_for('Original')[0]+(-1,-1,1,1)
    page.set_rotation(rotation)
    before = page.get_text()
    editor.change(lambda doc: move_text(doc[0],rect,rect+(120,80,120,80)))
    page = editor.doc[0]
    assert page.get_text().count('Original') == 1
    assert page.search_for('Original')[0].x0 == pytest.approx(170, abs=0.01)
    assert 'Keep' in page.get_text()
    assert len(page.get_drawings()) == 1
    spans = [s for b in page.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
    moved = next(s for s in spans if s['text']=='Original')
    assert moved['font']=='Helvetica-Bold' and moved['color']==0xff0000
    editor.undo()
    assert editor.doc[0].get_text()==before
    editor.doc.close()


def letter_page(doc):
    page = doc.new_page()
    page.insert_text((85, 120), '11.08.2026', fontsize=10, color=(0, 0, 0))
    page.insert_text((85, 160), 'Keep this neighbouring line.', fontsize=10)
    return page, page.search_for('11.08.2026')[0]


def test_tight_date_uses_original_size_instead_of_toolbar_default(tmp_path):
    with fitz.open() as doc:
        page, rect = letter_page(doc)
        with pytest.raises(ValueError):
            add_text(page, rect, '18.09.2026', size=16)
        assert replacement_style(page, rect)['size'] == pytest.approx(10)
        used = replace_text(page, rect, '18.09.2026')
        assert 6 <= used <= 10.01
        assert '18.09.2026' in page.get_text()
        assert '11.08.2026' not in page.get_text()
        assert 'Keep this neighbouring line.' in page.get_text()
        page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(tmp_path / 'date-after.png')


def test_longer_turkish_text_fits_without_crossing_selection(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 90), 'Office closed today', fontsize=11)
        rect = fitz.Rect(48, 76, 180, 100)
        used = replace_text(page, rect, 'İstanbul ofisi bugün kapalıdır.')
        assert 6 <= used <= 11
        assert 'kapalıdır.' in page.get_text()
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    box = fitz.Rect(span['bbox'])
                    assert rect.contains(box)
        page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(tmp_path / 'turkish-after.png')


def test_failed_replacement_leaves_original_and_can_retry_and_undo():
    editor = Editor()
    editor.new()
    page = editor.doc[0]
    page.insert_text((50, 90), 'Original', fontsize=10)
    rect = page.search_for('Original')[0]
    before = page.get_text()
    with pytest.raises(ValueError):
        editor.change(lambda doc: replace_text(doc[0], rect, 'This will not fit. ' * 80))
    assert editor.doc[0].get_text() == before
    assert not list(editor.doc[0].annots() or [])
    editor.change(lambda doc: replace_text(doc[0], rect, 'Updated'))
    assert 'Updated' in editor.doc[0].get_text()
    editor.undo()
    assert editor.doc[0].get_text() == before
    editor.doc.close()


def test_replacement_preserves_image_and_colored_background():
    from PIL import Image
    import io
    stream = io.BytesIO()
    Image.new('RGB', (100, 100), '#ccddee').save(stream, format='PNG')
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_image(fitz.Rect(30, 30, 220, 200), stream=stream.getvalue())
        page.draw_rect(fitz.Rect(35, 35, 215, 195), color=(1, 0, 0))
        page.insert_text((50, 90), 'Original', fontsize=10)
        rect = page.search_for('Original')[0]
        image_before = doc.extract_image(page.get_images()[0][0])['image']
        replace_text(page, rect, 'Changed')
        assert doc.extract_image(page.get_images()[0][0])['image'] == image_before
        assert len(page.get_drawings()) == 1
        assert 'Changed' in page.get_text()


def test_dialog_retains_draft_on_failure(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from text_dialog import ReplaceTextDialog
    app = QApplication.instance() or QApplication([])
    tries = []
    def apply(text, size, fit):
        tries.append(text)
        if len(tries) == 1:
            raise ValueError('Metin sığmıyor')
        return 9.5
    dialog = ReplaceTextDialog(None, 'Original', 10, apply)
    dialog.text.setPlainText('Keep my draft')
    dialog.apply()
    assert dialog.text.toPlainText() == 'Keep my draft'
    assert dialog.result() == 0
    assert dialog.error.text() == 'Metin sığmıyor'
    dialog.apply()
    assert dialog.result() == 1
    assert dialog.used_size == 9.5


def test_ui_replacement_route_ignores_16pt_toolbar(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app import Window
    from text_dialog import ReplaceTextDialog
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.new()
    window.editor.doc[0].insert_text((50, 90), '11.08.2026', fontsize=10)
    rect = window.editor.doc[0].search_for('11.08.2026')[0]
    assert window.size.value() == 16
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    def edit(dialog):
        assert dialog.size.value() == 10
        dialog.text.setPlainText('18.09.2026')
        dialog.apply()
        return dialog.result()
    monkeypatch.setattr(ReplaceTextDialog, 'exec', edit)
    window.set_mode('Metni değiştir')
    window.edit_selection(rect)
    assert not warnings
    assert '18.09.2026' in window.editor.doc[0].get_text()
    window.editor.dirty = False
    window.close()
