import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import pymupdf as fitz
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
from app import Window
from session import Session
from test_workflow import make_pdf


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: (_ for _ in ()).throw(AssertionError(str(a))))
    app = QApplication.instance() or QApplication([])
    w = Window()
    w.session = Session(tmp_path / 'appdata')
    yield w
    w.editor.dirty = False
    w.close()


def test_stamp_dialog_applies_header(window, monkeypatch):
    import workflow_ui
    window.new()
    window.blank()
    def accept(dialog):
        dialog.template.setText('Rapor · {n}/{toplam}')
        dialog.position.setCurrentText('Üst orta')
        return True
    monkeypatch.setattr(workflow_ui.StampDialog, 'exec', accept)
    window.stamp_dialog()
    assert 'Rapor · 2/2' in window.editor.doc[1].get_text()
    window.undo()
    assert 'Rapor' not in window.editor.doc[1].get_text()


def test_batch_dialog_runs_and_reports(window, tmp_path, monkeypatch):
    import workflow_ui
    source = tmp_path / 'girdi'
    source.mkdir()
    make_pdf(source / 'a.pdf')
    make_pdf(source / 'b.pdf')
    output = tmp_path / 'cikti'
    monkeypatch.setattr(workflow_ui.BatchDialog, 'exec', lambda self: True)
    monkeypatch.setattr(workflow_ui.BatchDialog, 'values', lambda self: dict(
        files=[source / 'a.pdf', source / 'b.pdf'], output=output, operation='Filigran', options=dict(text='TASLAK')))
    reports = []
    monkeypatch.setattr(window, 'result_text', lambda title, text: reports.append(text))
    window.batch_dialog()
    assert reports and reports[0].startswith('2 / 2')
    with fitz.open(output / 'b.pdf') as doc:
        assert 'TASLAK' in doc[0].get_text()


def test_recent_files_menu(window, tmp_path):
    path = make_pdf(tmp_path / 'son.pdf')
    window.open(str(path))
    assert window.session.recent() == [str(path.resolve())]
    window.rebuild_recent_menu()
    assert [a.text() for a in window.recent_menu.actions()][0].endswith('son.pdf')


def test_autosave_recovery_and_restore(window, tmp_path, monkeypatch):
    path = make_pdf(tmp_path / 'belge.pdf', pages=1)
    window.open(str(path))
    window.change(lambda d: d[0].insert_text((50, 300), 'Kurtarilacak'))
    window.autosave_recovery()
    assert len(window.session.recoveries()) == 1
    # Simulate a crash: a new window finds the recovery file and restores it.
    restored = Window()
    restored.session = window.session
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Yes)
    restored.check_recovery()
    assert 'Kurtarilacak' in restored.editor.doc[0].get_text()
    assert restored.editor.path == str(path) and restored.editor.dirty
    restored.save()
    assert window.session.recoveries() == []
    assert 'Kurtarilacak' in fitz.open(path)[0].get_text()
    restored.editor.dirty = False
    restored.close()


def test_declined_recovery_is_discarded(window, tmp_path, monkeypatch):
    window.new()
    window.change(lambda d: d[0].insert_text((50, 300), 'X'))
    window.autosave_recovery()
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.No)
    window.check_recovery()
    assert window.session.recoveries() == []
