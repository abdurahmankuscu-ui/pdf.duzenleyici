import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import pymupdf as fitz
import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from app import Window
from thumbnails import RENDERED_ROLE


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: (_ for _ in ()).throw(AssertionError(str(a))))
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'uzun.pdf'
    with fitz.open() as doc:
        for i in range(30):
            doc.new_page().insert_text((60, 90), f'Sayfa {i+1}', fontsize=28)
        doc.save(path)
    w = Window()
    w.resize(1380, 860)
    w.show()
    w.open(str(path))
    QApplication.processEvents()
    yield w
    w.editor.dirty = False
    w.close()


def image(window, row):
    item = window.thumbs.item(row)
    return item.icon().pixmap(window.thumbs.iconSize()).toImage()


def test_only_visible_pages_render_until_scrolled(window):
    window.update_visible_thumbnails()
    assert window.thumbs.item(0).data(RENDERED_ROLE)
    assert not window.thumbs.item(29).data(RENDERED_ROLE)
    window.thumbs.scrollToBottom()
    window.update_visible_thumbnails()
    assert window.thumbs.item(29).data(RENDERED_ROLE)


def test_every_item_has_uniform_size_before_rendering(window):
    sizes = {window.thumbs.visualItemRect(window.thumbs.item(i)).size().toTuple() for i in (0, 15, 29)}
    assert len(sizes) == 1


def test_edit_refreshes_page_preview(window):
    window.update_visible_thumbnails()
    before = image(window, 0)
    window.change(lambda d: d[0].draw_rect(fitz.Rect(0, 0, 600, 400), color=(0, 0, 0), fill=(0, 0, 0)))
    window.update_visible_thumbnails()
    assert window.thumbs.item(0).data(RENDERED_ROLE)
    assert image(window, 0) != before


def test_selected_preview_is_not_tinted(window):
    window.update_visible_thumbnails()
    icon = window.thumbs.item(0).icon()
    size = window.thumbs.iconSize()
    assert icon.pixmap(size, QIcon.Mode.Selected).toImage() == icon.pixmap(size, QIcon.Mode.Normal).toImage()


def test_wider_panel_gives_larger_previews(window):
    small = window.thumbs.iconSize().width()
    window.set_pages_panel_width(460)
    QApplication.processEvents()
    assert window.thumbs.iconSize().width() > small + 150
    window.update_visible_thumbnails()
    assert window.thumbs.item(0).data(RENDERED_ROLE)
    assert window.session.preference('pages_panel_width') == 460
