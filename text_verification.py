"""Exercise the packaged application with actual modal dialogs on synthetic PDFs."""
import json
from pathlib import Path
import pymupdf as fitz
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from text_dialog import ReplaceTextDialog


def verify_text(window, output):
    errors = []
    original_warning = QMessageBox.warning
    QMessageBox.warning = lambda *args: errors.append(str(args[2]))
    def fill_dialog(value):
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, ReplaceTextDialog):
            errors.append('Wrong dialog')
            if dialog:
                dialog.reject()
            return
        dialog.text.setPlainText(value)
        dialog.apply()
        if not dialog.result():
            errors.append(dialog.error.text())
            dialog.reject()
    try:
        window.new()
        page = window.editor.doc[0]
        page.insert_font(fontname='sample', fontfile='C:/Windows/Fonts/arial.ttf')
        page.insert_text((50,90), '11.08.2026', fontsize=10, fontname='sample')
        rect = page.search_for('11.08.2026')[0] + (-1,-1,1,1)
        window.set_mode('Metni değiştir')
        QTimer.singleShot(100, lambda: fill_dialog('18.09.2026'))
        window.edit_selection(rect)
        assert '18.09.2026' in window.editor.doc[0].get_text(), errors
        window.set_mode('Yazı stili al')
        window.edit_selection(rect)
        QTimer.singleShot(100, lambda: fill_dialog('Yeni metin'))
        added = fitz.Rect(50,180,160,200)
        window.edit_selection(added)
        assert 'Yeni metin' in window.editor.doc[0].get_text().replace('\u00a0',' '), errors
        window.move_selected_text(added, added+(120,80,120,80))
        hits = window.editor.doc[0].search_for('Yeni')
        assert len(hits)==1 and hits[0].x0>=169, errors
        window.editor.doc[0].insert_text((50,340),'Original',fontsize=9)
        narrow=window.editor.doc[0].search_for('Original')[0]
        def retry_multiline():
            dialog=QApplication.activeModalWidget()
            assert isinstance(dialog,ReplaceTextDialog)
            dialog.text.setPlainText('Sayın\nHAMDİ DOKGÖZ')
            dialog.apply()
            assert not dialog.result() and dialog.text.toPlainText()=='Sayın\nHAMDİ DOKGÖZ'
            dialog.area_width.setValue(50)
            dialog.area_height.setValue(15)
            dialog.grab().save(str(Path(output).with_suffix('.dialog.png')))
            dialog.apply()
            if not dialog.result():
                errors.append(dialog.error.text());dialog.reject()
        window.set_mode('Metni değiştir')
        QTimer.singleShot(100,retry_multiline)
        window.edit_selection(narrow)
        assert 'HAMDİ DOKGÖZ' in window.editor.doc[0].get_text(),errors
        from image_edit import ImageSizeDialog
        pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,80,40))
        pix.clear_with(100)
        window.editor.doc[0].insert_image(fitz.Rect(50,400,210,480),stream=pix.tobytes('png'))
        def size_image():
            dialog=QApplication.activeModalWidget()
            assert isinstance(dialog,ImageSizeDialog)
            dialog.fields['width'].setValue(84.67)
            dialog.apply()
            if not dialog.result():
                errors.append(dialog.error.text());dialog.reject()
        window.set_mode('Resmi boyutlandır')
        QTimer.singleShot(100,size_image)
        from PySide6.QtCore import Qt,QEvent,QPointF
        from PySide6.QtGui import QMouseEvent
        window.render()
        at=window.canvas.mapFromScene(100*window.canvas.factor,440*window.canvas.factor)
        for kind,buttons in [(QEvent.Type.MouseButtonPress,Qt.MouseButton.LeftButton),
                             (QEvent.Type.MouseButtonRelease,Qt.MouseButton.NoButton)]:
            event=QMouseEvent(kind,QPointF(at),QPointF(window.canvas.viewport().mapToGlobal(at)),
                             Qt.MouseButton.LeftButton,buttons,Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(window.canvas.viewport(),event)
        assert abs(fitz.Rect(window.editor.doc[0].get_image_info()[0]['bbox']).width-240)<0.1
        from PySide6.QtGui import QKeyEvent
        window.set_mode('Metni taşı')
        selection=window.editor.doc[0].search_for('18.09.2026')[0]+(-1,-1,1,1)
        window.edit_selection(selection)
        canvas=window.canvas
        start=canvas.mapFromScene(canvas.move_region.center())
        delta=canvas.sceneRect().center().x()-canvas.alignment_region.center().x()
        end=canvas.mapFromScene(canvas.move_region.center()+QPointF(delta,70))
        unchanged=window.editor.doc.tobytes(no_new_id=True)
        for kind,pos in [(QEvent.Type.MouseButtonPress,start),(QEvent.Type.MouseMove,end)]:
            event=QMouseEvent(kind,QPointF(pos),QPointF(canvas.viewport().mapToGlobal(pos)),
                Qt.MouseButton.LeftButton if kind==QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(canvas.viewport(),event)
        assert canvas.moving and any(matched for _,_,matched in canvas.guide_lines)
        window.grab().save(str(Path(output).with_suffix('.guides.png')))
        QApplication.sendEvent(canvas,QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Escape,Qt.KeyboardModifier.NoModifier))
        assert not canvas.guide_lines and window.editor.doc.tobytes(no_new_id=True)==unchanged
        assert not errors, errors
        window.editor.doc.save(str(Path(output).with_suffix('.pdf')))
        window.grab().save(str(Path(output).with_suffix('.png')))
        Path(output).write_text(json.dumps({'passed':True,'checks':['replace dialog','add dialog','font sampling','drag handler','text retained','image resize dialog','multiline retry with larger area','alignment guides and Escape']},ensure_ascii=False),encoding='utf-8')
    finally:
        QMessageBox.warning = original_warning
        window.editor.dirty = False
        window.close()
