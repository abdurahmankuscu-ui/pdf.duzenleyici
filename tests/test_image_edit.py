import pymupdf as fitz
import pytest
from engine import Editor
from image_edit import selected_image, resize_image, image_placements


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_resize_only_selected_occurrence_and_undo(tmp_path,rotation):
    e=Editor();e.new();p=e.doc[0]
    pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,80,40));pix.clear_with(100)
    x=p.insert_image(fitz.Rect(20,30,180,110),stream=pix.tobytes('png'))
    p.insert_image(fitz.Rect(220,30,380,110),xref=x)
    p.insert_text((30,150),'Keep this text')
    p.set_rotation(rotation)
    placement=selected_image(p,fitz.Rect(60,60,60,60))
    dest=fitz.Rect(30,200,270,320)
    e.change(lambda d:resize_image(d[0],placement,dest))
    boxes=[i['bbox'] for i in e.doc[0].get_image_info()]
    assert fitz.Rect(boxes[0])==dest
    assert fitz.Rect(boxes[1])==fitz.Rect(220,30,380,110)
    assert 'Keep this text' in e.doc[0].get_text()
    e.save(tmp_path/'resized.pdf')
    with fitz.open(tmp_path/'resized.pdf') as check:
        assert fitz.Rect(check[0].get_image_info()[0]['bbox'])==dest
    e.undo()
    assert fitz.Rect(e.doc[0].get_image_info()[0]['bbox'])==fitz.Rect(20,30,180,110)
    e.doc.close()


def test_dialog_keeps_ratio_and_failed_values():
    from PySide6.QtWidgets import QApplication
    from image_edit import ImageSizeDialog
    app=QApplication.instance() or QApplication([])
    def reject(rect): raise ValueError('Sayfa dışı')
    d=ImageSizeDialog(None,fitz.Rect(0,0,200,100),reject)
    d.fields['width'].setValue(100)
    assert d.fields['height'].value()==50
    d.apply()
    assert d.result()==0 and d.error.text()=='Sayfa dışı'
    assert d.fields['width'].value()==100


def test_click_image_opens_resize_dialog(monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    from app import Window
    from image_edit import ImageSizeDialog
    app=QApplication.instance() or QApplication([])
    w=Window();w.new()
    pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,80,40));pix.clear_with(100)
    w.editor.doc[0].insert_image(fitz.Rect(50,50,210,130),stream=pix.tobytes('png'))
    w.refresh();w.show();w.set_mode('Resmi boyutlandır');app.processEvents()
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:warnings.append(args))
    def resize(dialog):
        dialog.fields['width'].setValue(28.22)
        dialog.apply()
        return dialog.result()
    monkeypatch.setattr(ImageSizeDialog,'exec',resize)
    at=w.canvas.mapFromScene(100*w.canvas.factor,90*w.canvas.factor)
    QTest.mouseClick(w.canvas.viewport(),Qt.MouseButton.LeftButton,pos=at)
    assert not warnings
    assert abs(fitz.Rect(w.editor.doc[0].get_image_info()[0]['bbox']).width-80)<0.1
    w.editor.dirty=False;w.close()
