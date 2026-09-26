import pymupdf as fitz
import pytest
from PySide6.QtCore import Qt,QPointF
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app import Window


@pytest.mark.parametrize('rotation,zoom',[(0,60),(0,150),(90,100),(270,80)])
def test_guide_targets_use_display_coordinates(rotation,zoom):
    app=QApplication.instance() or QApplication([])
    w=Window();w.new();p=w.editor.doc[0]
    p.insert_text((50,90),'Move',fontsize=12)
    p.insert_text((150,160),'Reference',fontsize=12)
    selected=p.search_for('Move')[0]+(-1,-1,1,1)
    reference=p.search_for('Reference')[0]
    p.set_rotation(rotation);w.zoom.setValue(zoom);w.render()
    w.set_mode('Metni taşı');w.edit_selection(selected*p.rotation_matrix)
    target=reference*p.rotation_matrix
    assert any(abs(x-target.x0*w.canvas.factor)<.01 for x in w.canvas.guide_targets[0])
    c=w.canvas
    dx=c.sceneRect().center().x()-c.alignment_region.center().x()
    c.update_guides(c.move_region.translated(dx,30))
    assert any(axis=='x' and matched and abs(v-c.sceneRect().center().x())<1 for axis,v,matched in c.guide_lines)
    assert not w.editor.doc[0].get_drawings()
    w.editor.dirty=False;w.close()


def test_drag_guides_disappear_on_escape_without_pdf_changes(tmp_path):
    app=QApplication.instance() or QApplication([])
    w=Window();w.new();w.editor.doc[0].insert_text((50,90),'Move',fontsize=12)
    rect=w.editor.doc[0].search_for('Move')[0]+(-2,-2,2,2)
    w.render();w.show();app.processEvents()
    w.set_mode('Metni taşı');w.edit_selection(rect)
    c=w.canvas
    start=c.mapFromScene(c.move_region.center())
    end=c.mapFromScene(c.move_region.center()+QPointF(70,50))
    before=w.editor.doc.tobytes(no_new_id=True)
    QTest.mousePress(c.viewport(),Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(c.viewport(),end)
    assert c.moving and len(c.guide_lines)>=6
    w.grab().save(str(tmp_path/'guides.png'))
    assert w.editor.doc.tobytes(no_new_id=True)==before
    QTest.keyClick(c,Qt.Key.Key_Escape)
    assert not c.moving and not c.guide_lines
    assert w.editor.doc.tobytes(no_new_id=True)==before
    w.editor.dirty=False;w.close()
