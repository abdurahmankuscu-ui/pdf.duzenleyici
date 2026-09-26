import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
import pymupdf as fitz
from app import Window
from engine import add_text


def test_ui_page_operations_and_rectangle(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    def fail(*args):
        raise AssertionError(str(args))
    monkeypatch.setattr(QMessageBox, 'warning', fail)
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.show()
    window.new()
    window.blank()
    assert len(window.editor.doc) == 2
    window.rotate()
    assert window.editor.doc[0].rotation == 90
    window.undo()
    assert window.editor.doc[0].rotation == 0
    window.set_mode('Dikdörtgen')
    app.processEvents()
    start = window.canvas.mapFromScene(100, 100)
    end = window.canvas.mapFromScene(250, 170)
    QTest.mousePress(window.canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(window.canvas.viewport(), end)
    QTest.mouseRelease(window.canvas.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert len(window.editor.doc[0].get_drawings()) == 1
    window.change(lambda d: add_text(d[0], fitz.Rect(50, 160, 500, 260), 'PDF Stüdyo\nTürkçe belge düzenleme', 20))
    window.search.setText('Türkçe')
    window.find()
    assert 'eşleşme' in window.statusBar().currentMessage()
    window.grab().save(str(tmp_path / 'ui.png'))
    window.editor.dirty = False
    window.close()


def test_background_result_delivery():
    app = QApplication.instance() or QApplication([])
    window = Window()
    results = []
    window.background('Test', lambda: 'complete', results.append)
    assert results == ['complete']
    window.close()


def test_ui_security_actions(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox, QFileDialog
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: (_ for _ in ()).throw(AssertionError(str(a))))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.new()
    window.editor.doc.set_metadata({'title': 'Gizli başlık'})
    window.sanitize_document()
    assert not window.editor.doc.metadata['title']
    protected = tmp_path / 'korumali.pdf'
    window.editor.save(protected, 'secret')
    window.editor.open(protected, 'secret')
    plain = tmp_path / 'parolasiz.pdf'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(plain), ''))
    window.save_without_password()
    with fitz.open(plain) as doc:
        assert not doc.needs_pass
    with fitz.open(protected) as doc:
        assert doc.needs_pass
    window.editor.dirty = False
    window.close()


def test_ui_auto_redaction_preview(monkeypatch):
    import security_ui
    from test_security import sample_doc, valid_tckn
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.editor.new()
    window.editor.doc.insert_pdf(sample_doc())
    window.refresh()
    seen = {}
    def accept(dialog):
        seen['items'] = dialog.list.count()
        # Untick the e-mail hit: the user may keep some findings.
        for i in range(dialog.list.count()):
            if dialog.list.item(i).data(256)['kind'] == 'E-posta':
                dialog.list.item(i).setCheckState(Qt.CheckState.Unchecked)
        return True
    monkeypatch.setattr(security_ui.RedactionDialog, 'exec', accept)
    window.auto_redact()
    assert seen['items'] >= 4
    text = ''.join(p.get_text() for p in window.editor.doc)
    assert valid_tckn() not in text and 'deniz.yilmaz@example.com' in text
    window.undo()
    assert valid_tckn() in ''.join(p.get_text() for p in window.editor.doc)
    window.editor.dirty = False
    window.close()


def test_ui_digital_sign_and_verify(tmp_path, monkeypatch):
    import security_ui
    from test_security import make_pfx
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    pfx = make_pfx(tmp_path)
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.new()
    output = tmp_path / 'imzali.pdf'
    monkeypatch.setattr(security_ui.SignDialog, 'exec', lambda self: True)
    monkeypatch.setattr(security_ui.SignDialog, 'values',
                        lambda self: dict(pfx=str(pfx), pfx_password='sifre', reason='Onay', location='Ankara'))
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: (str(output), ''))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.No)
    window.digital_sign(0, fitz.Rect(300, 700, 500, 760))
    from signing import verify_signatures
    assert verify_signatures(output.read_bytes())[0]['intact']
    reports = []
    monkeypatch.setattr(window, 'result_text', lambda title, text: reports.append(text))
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **k: (str(output), ''))
    window.verify_document_signatures()
    assert 'GEÇERLİ' in reports[0]
    window.editor.dirty = False
    window.close()


def test_ui_saving_signed_pdf_asks_first(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.new()
    path = tmp_path / 'a.pdf'
    window.editor.save(path)
    window.editor.signed = True
    asked = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No)
    before = path.read_bytes()
    assert window.save() is False
    assert asked and 'imza' in asked[0].lower() and path.read_bytes() == before
    window.editor.dirty = False
    window.close()
