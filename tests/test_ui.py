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
