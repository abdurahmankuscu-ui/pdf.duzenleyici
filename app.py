import sys
from pathlib import Path
if any(flag in sys.argv for flag in ('--smoke-test', '--verify-integrations', '--verify-text', '--verify-features')):
    import traceback
    def smoke_exception(exc_type, exc_value, exc_traceback):
        Path('smoke-error.log').write_text(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)), encoding='utf-8')
        sys.exit(1)
    sys.excepthook = smoke_exception
import pymupdf as fitz
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSize
from PySide6.QtGui import QAction, QColor, QImage, QPixmap, QPen, QIcon, QKeySequence, QFontDatabase, QFont, QPainterPath
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QFileDialog, QInputDialog, QMessageBox, QToolBar, QSpinBox, QSplitter, QColorDialog,
    QLineEdit, QAbstractItemView)
from engine import Editor, add_text, erase, extract, page_range, replacement_style, replace_text, move_text
from text_dialog import ReplaceTextDialog
from tool_ui import ToolsMixin
from version import VERSION
from security_ui import SecurityMixin
from editing_ui import EditingMixin
from workflow_ui import WorkflowMixin


class Canvas(QGraphicsView):
    selected = Signal(object)
    moved = Signal(object, object)
    # Freehand points and line endpoints, already in unscaled page coordinates.
    stroked = Signal(object)
    dragged = Signal(object, object)

    def __init__(self):
        super().__init__()
        font_path = Path('C:/Windows/Fonts/segoeui.ttf')
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
            QApplication.instance().setFont(QFont('Segoe UI', 10))
        self.setScene(QGraphicsScene(self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.mode = 'Gezin'
        self.origin = None
        self.box = None
        self.factor = 1.4
        self.move_region = None
        self.moving = False
        self.guide_targets = ([], [])
        self.alignment_region = None
        self.guide_lines = []

    def clear_drag(self):
        self.origin = None
        self.box = None
        self.moving = False
        self.guide_lines = []
        self.viewport().update()

    def update_guides(self, rect):
        bounds = self.sceneRect()
        # Lines follow the actual text bounds, independent of selection padding.
        delta = rect.topLeft() - self.move_region.topLeft()
        aligned = self.alignment_region.translated(delta) if self.alignment_region is not None else rect
        xs = [aligned.left(), aligned.center().x(), aligned.right()]
        ys = [aligned.top(), aligned.center().y(), aligned.bottom()]
        self.guide_lines = [('x',v,False) for v in (xs[0],xs[2],bounds.center().x())]
        self.guide_lines += [('y',v,False) for v in (ys[0],ys[2],bounds.center().y())]
        # Screen-space tolerance stays usable at every zoom level.
        for axis, anchors, targets in [('x',xs,self.guide_targets[0]),('y',ys,self.guide_targets[1])]:
            matches = {round(t,3) for t in targets if any(abs(t-a)<=5 for a in anchors)}
            self.guide_lines.extend((axis,t,True) for t in sorted(matches))
        self.viewport().update()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if not self.moving:
            return
        bounds = self.sceneRect()
        painter.save()
        painter.setClipRect(bounds)
        for axis,value,matched in self.guide_lines:
            pen=QPen(QColor('#087f72' if matched else '#8faab8'),1.5 if matched else 1)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.DashLine if matched else Qt.PenStyle.DotLine)
            painter.setPen(pen)
            if axis=='x':
                painter.drawLine(QPointF(value,bounds.top()),QPointF(value,bounds.bottom()))
            else:
                painter.drawLine(QPointF(bounds.left(),value),QPointF(bounds.right(),value))
        painter.restore()

    def mousePressEvent(self, event):
        if self.mode in ('Serbest çizim', 'Çizgi', 'Ok') and event.button() == Qt.MouseButton.LeftButton:
            self.origin = self.mapToScene(event.position().toPoint())
            self.points = [self.origin]
            pen = QPen(QColor('#087f72'), 2)
            pen.setCosmetic(True)
            self.box = self.scene().addPath(QPainterPath(self.origin), pen)
        elif self.mode != 'Gezin' and event.button() == Qt.MouseButton.LeftButton:
            self.origin = self.mapToScene(event.position().toPoint())
            self.moving = self.mode == 'Metni taşı' and self.move_region is not None and self.move_region.contains(self.origin)
            box = self.move_region if self.moving else QRectF(self.origin, self.origin)
            self.box = self.scene().addRect(box, QPen(QColor('#087f72'), 2))
            if self.moving:
                self.update_guides(box)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.origin is not None and self.mode in ('Serbest çizim', 'Çizgi', 'Ok'):
            point = self.mapToScene(event.position().toPoint())
            self.points = self.points + [point] if self.mode == 'Serbest çizim' else [self.origin, point]
            path = QPainterPath(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
            self.box.setPath(path)
        elif self.origin is not None:
            point = self.mapToScene(event.position().toPoint())
            self.box.setRect(self.move_region.translated(point-self.origin) if self.moving else QRectF(self.origin, point).normalized())
            if self.moving:
                self.update_guides(self.box.rect())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.origin is not None and self.mode in ('Serbest çizim', 'Çizgi', 'Ok'):
            end = self.mapToScene(event.position().toPoint())
            points = self.points if self.mode == 'Serbest çizim' else [self.origin, end]
            if self.mode == 'Serbest çizim' and points[-1] != end:
                points = points + [end]
            self.scene().removeItem(self.box)
            self.origin = self.box = None
            page_points = [fitz.Point(p.x()/self.factor, p.y()/self.factor) for p in points]
            if self.mode == 'Serbest çizim':
                self.stroked.emit(page_points)
            else:
                self.dragged.emit(page_points[0], page_points[-1])
        elif self.origin is not None:
            rect = self.box.rect() if self.moving else self.box.rect().intersected(self.sceneRect())
            self.scene().removeItem(self.box)
            self.guide_lines = []
            self.viewport().update()
            self.origin = self.box = None
            if self.mode == 'Resmi boyutlandır':
                point = self.mapToScene(event.position().toPoint())
                x,y = point.x()/self.factor,point.y()/self.factor
                self.selected.emit(fitz.Rect(x,y,x,y))
                return
            if self.moving:
                old = self.move_region
                self.moving = False
                def pdf(r):
                    return fitz.Rect(r.left()/self.factor, r.top()/self.factor, r.right()/self.factor, r.bottom()/self.factor)
                self.moved.emit(pdf(old), pdf(rect))
                return
            if rect.width() > 4 and rect.height() > 4:
                self.selected.emit(fitz.Rect(rect.left()/self.factor, rect.top()/self.factor,
                                            rect.right()/self.factor, rect.bottom()/self.factor))
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape and self.origin is not None:
            if self.box is not None:
                self.scene().removeItem(self.box)
            self.clear_drag()
            event.accept()
            return
        super().keyPressEvent(event)


class Window(SecurityMixin, EditingMixin, WorkflowMixin, ToolsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.editor = Editor()
        self.page = 0
        self.color = '#172033'
        self.text_style = None
        self.resize(1380, 900)
        self.setMinimumSize(1000, 660)
        self.setAcceptDrops(True)
        self.actions = []
        self.build_ui()
        self.setup_tools()
        self.setup_editing()
        self.setup_workflow()
        self.refresh()

    def guarded(self, fn):
        def call(*_):
            try:
                fn()
            except Exception as e:
                QMessageBox.warning(self, 'İşlem tamamlanamadı', str(e))
        return call

    def action(self, bar, text, fn, shortcut=None, needs=True):
        a = QAction(text, self)
        a.triggered.connect(self.guarded(fn))
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        bar.addAction(a)
        if needs:
            self.actions.append(a)
        return a

    def build_ui(self):
        from workspace_ui import build_workspace
        build_workspace(self, Canvas)

    def set_mode(self, mode):
        if self.canvas.box is not None:
            self.canvas.scene().removeItem(self.canvas.box)
        self.canvas.clear_drag()
        self.canvas.move_region = None
        self.canvas.mode = mode
        self.mode_label.setText(mode)
        for name, action in self.mode_actions.items():
            action.setChecked(name == mode)
        self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if mode == 'Gezin' else QGraphicsView.DragMode.NoDrag)
        if mode in ('Serbest çizim', 'Çizgi', 'Ok'):
            self.statusBar().showMessage(f'{mode}: Sayfa üzerinde fareyi basılı tutup çizin. Renk için Renk düğmesini kullanın.')
            return
        self.statusBar().showMessage('Resmi boyutlandır: Resmin ortasına tıklayın.' if mode == 'Resmi boyutlandır' else ('Sayfayı sürükleyerek gezinin.' if mode == 'Gezin' else f'{mode}: Sayfa üzerinde sürükleyerek bir alan seçin.'))

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.color), self)
        if color.isValid():
            self.color = color.name()

    def fit_width(self):
        if self.editor.doc is not None:
            width = self.editor.doc[self.page].rect.width
            self.zoom.setValue(max(30, min(300, int((self.canvas.viewport().width()-40)*100/(1.4*width)))))

    def unsaved(self):
        if not self.editor.dirty:
            return True
        answer = QMessageBox.question(self, 'Kaydedilmemiş değişiklikler', 'Değişiklikler kaydedilsin mi?',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        if answer == QMessageBox.StandardButton.Discard:
            self.discard_recovery()
            return True
        return False

    def new(self):
        if self.unsaved():
            self.editor.new()
            self.page = 0
            self.refresh()

    def open(self, path=None):
        if not self.unsaved():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, 'PDF aç', '', 'PDF (*.pdf)')
        if not path:
            return
        with fitz.open(path) as check:
            encrypted = check.needs_pass
        password = ''
        if encrypted:
            password, ok = QInputDialog.getText(self, 'Korumalı PDF', 'Parola:', QLineEdit.EchoMode.Password)
            if not ok:
                return
        self.editor.open(path, password)
        self.session.add_recent(path)
        self.page = 0
        self.refresh()
        if self.editor.signed:
            self.statusBar().showMessage('Belge dijital imzalı. Doğrulamak için PDF güvenliği > İmzaları doğrula. Kaydetmek imzaları geçersiz kılar.')
        elif encrypted:
            self.statusBar().showMessage('Parolalı PDF açıldı. Kayıtlarda aynı parola korunur; kaldırmak için PDF güvenliği > Parolasız kaydet.')

    def output_path(self, title='PDF kaydet'):
        suggested = str(Path(self.editor.path).with_stem(Path(self.editor.path).stem + '-duzenlenmis')) if self.editor.path else 'Belge.pdf'
        path, _ = QFileDialog.getSaveFileName(self, title, suggested, 'PDF (*.pdf)')
        return path

    def save(self, different=False):
        if not self.editor.doc:
            return False
        if self.editor.signed:
            answer = QMessageBox.question(self, 'İmzalı belge',
                'Bu belgede dijital imza var. Kaydetmek belgeyi yeniden yazar ve mevcut imzaları GEÇERSİZ kılar.\n\n'
                'Yine de kaydedilsin mi?')
            if answer != QMessageBox.StandardButton.Yes:
                return False
        path = self.output_path() if different or not self.editor.path else self.editor.path
        if not path:
            return False
        # The recovery slot follows the current path, so drop it before a Save As.
        self.discard_recovery()
        self.editor.save(path)
        self.session.add_recent(path)
        self.refresh(False)
        self.statusBar().showMessage(f'Kaydedildi: {path}')
        return True

    def refresh(self, thumbs=True):
        doc = self.editor.doc
        for action in self.actions:
            action.setEnabled(doc is not None)
        self.undo_action.setEnabled(bool(self.editor.undo_stack))
        self.redo_action.setEnabled(bool(self.editor.redo_stack))
        title = Path(self.editor.path).name if self.editor.path else 'Yeni belge'
        self.setWindowTitle(f'{"● " if self.editor.dirty else ""}{title} — PDF Stüdyo {VERSION}')
        self.workspace_stack.setCurrentIndex(0 if doc is None else 1)
        if doc is None:
            self.info.setText('Çalışma alanı')
            self.canvas.scene().clear()
            self.statusBar().showMessage('Başlamak için bir PDF açın veya dosyanızı pencereye sürükleyin.')
            return
        self.page = min(self.page, len(doc) - 1)
        self.info.setText(f'   {title}   /   {len(doc)} sayfa')
        if thumbs:
            self.thumbs.blockSignals(True)
            self.thumbs.clear()
            for i in range(len(doc)):
                item = QListWidgetItem(f'Sayfa {i+1}')
                # Original index lets drag-and-drop compute the new page order.
                item.setData(Qt.ItemDataRole.UserRole, i)
                # Avoid rendering the entire document eagerly.
                if abs(i - self.page) < 12:
                    pix = doc[i].get_pixmap(matrix=fitz.Matrix(0.18, 0.18), alpha=False)
                    item.setIcon(QIcon(self.pixmap(pix)))
                self.thumbs.addItem(item)
            self.thumbs.setCurrentRow(self.page)
            self.thumbs.blockSignals(False)
        self.render()
        self.refresh_comments()

    @staticmethod
    def pixmap(pix):
        return QPixmap.fromImage(QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy())

    def render(self):
        if self.editor.doc is None:
            return
        page = self.editor.doc[self.page]
        self.canvas.factor = min(1.4 * self.zoom.value()/100, 5000/max(page.rect.width, page.rect.height))
        pix = page.get_pixmap(matrix=fitz.Matrix(self.canvas.factor, self.canvas.factor), alpha=False)
        self.canvas.clear_drag()
        self.canvas.scene().clear()
        self.canvas.move_region = None
        self.canvas.scene().addPixmap(self.pixmap(pix))
        self.canvas.setSceneRect(QRectF(0, 0, pix.width, pix.height))

    def select_page(self, row):
        if row >= 0 and self.editor.doc:
            self.page = row
            self.render()

    def change(self, fn):
        self.editor.change(fn)
        self.refresh()

    def edit_selection(self, rect):
        def run():
            nonlocal rect
            if self.editor.doc is None:
                return
            page = self.editor.doc[self.page]
            rect = rect * page.derotation_matrix
            mode = self.canvas.mode
            color = tuple(QColor(self.color).getRgbF()[:3])
            if mode == 'Metni taşı':
                if not page.get_textbox(rect).strip():
                    raise ValueError('Taşınacak yazının tamamını seçin.')
                display = rect * page.rotation_matrix
                f = self.canvas.factor
                self.canvas.move_region = QRectF(display.x0*f, display.y0*f, display.width*f, display.height*f)
                xs=[0,page.rect.width*f/2,page.rect.width*f]
                ys=[0,page.rect.height*f/2,page.rect.height*f]
                selected_bounds=None
                for block in page.get_text('dict',flags=fitz.TEXTFLAGS_TEXT)['blocks']:
                    for line in block.get('lines',[]):
                        for span in line['spans']:
                            span_rect=fitz.Rect(span['bbox'])
                            if not (span_rect & rect).is_empty:
                                clipped=span_rect & rect
                                selected_bounds=clipped if selected_bounds is None else selected_bounds | clipped
                                continue
                            target=span_rect * page.rotation_matrix
                            xs.extend([target.x0*f,(target.x0+target.x1)*f/2,target.x1*f])
                            ys.extend([target.y0*f,(target.y0+target.y1)*f/2,target.y1*f])
                self.canvas.guide_targets=(sorted(set(xs)),sorted(set(ys)))
                aligned=(selected_bounds or rect) * page.rotation_matrix
                self.canvas.alignment_region=QRectF(aligned.x0*f,aligned.y0*f,aligned.width*f,aligned.height*f)
                self.canvas.scene().addRect(self.canvas.move_region, QPen(QColor('#087f72'), 2))
                self.statusBar().showMessage('Kutunun içinden sürükleyin. Turkuaz kılavuz: hizalama yakın. Esc: vazgeç · Ctrl+Z: geri al.')
            elif mode == 'Resmi boyutlandır':
                from image_edit import selected_image, resize_image, ImageSizeDialog
                placement = selected_image(page, rect)
                def apply_size(destination):
                    self.editor.change(lambda doc:resize_image(doc[self.page],placement,destination))
                dialog = ImageSizeDialog(self,placement['rect'],apply_size)
                if dialog.exec():
                    self.refresh()
                    self.statusBar().showMessage('Resim boyutlandırıldı. Ctrl+Z ile geri alabilirsiniz.')
            elif mode == 'Dijital imza':
                self.digital_sign(self.page, rect)
            elif mode == 'Yazı stili al':
                self.text_style = replacement_style(page, rect)
                self.size.setValue(round(self.text_style['size']))
                self.color = self.text_style['color']
                self.set_mode('Metin ekle')
                self.statusBar().showMessage(f"Yazı stili alındı: {self.text_style['font_name']}. Şimdi yeni metin için alan seçin.")
            elif mode == 'Metni değiştir':
                style = replacement_style(page, rect)
                old = page.get_textbox(rect)
                def apply_replacement(value, size, auto_fit):
                    used = []
                    self.editor.change(lambda doc: used.append(replace_text(doc[self.page], rect, value,
                        size=size, auto_fit=auto_fit, style=style, output_rect=dialog.output_rect())))
                    return used[0]
                dialog = ReplaceTextDialog(self, old, style['size'], apply_replacement)
                dialog.configure_area(rect,page.rect * page.derotation_matrix)
                dialog.set_font_info(style)
                if dialog.exec():
                    self.refresh()
                    self.statusBar().showMessage(f'Metin değiştirildi. Kullanılan yazı boyutu: {dialog.used_size:.1f} pt. Ctrl+Z ile geri alabilirsiniz.')
            elif mode == 'Metin ekle':
                style = dict(self.text_style or {})
                initial_size = style.pop('size', self.size.value())
                style.setdefault('color', self.color)
                def apply_added(value, size, auto_fit):
                    if not value.strip():
                        raise ValueError('Eklenecek metni yazın.')
                    used = []
                    self.editor.change(lambda doc: used.append(add_text(doc[self.page], rect, value,
                        size, auto_fit=auto_fit, compact=True, **style)))
                    return used[0]
                dialog = ReplaceTextDialog(self, '', initial_size, apply_added)
                dialog.setWindowTitle('Metin ekle')
                dialog.set_font_info(style)
                if dialog.exec():
                    self.refresh()
                    self.statusBar().showMessage('Metin eklendi. Yerini değiştirmek için Metni taşı aracını kullanın.')
            elif mode == 'Not ekle':
                value, ok = QInputDialog.getMultiLineText(self, mode, 'Metin:', '')
                if not ok or not value:
                    return
                def operation(doc):
                    p = doc[self.page]
                    if mode == 'Not ekle':
                        p.add_text_annot(rect.tl, value)
                    else:
                        add_text(p, rect, value, self.size.value(), self.color)
                self.change(operation)
            elif mode == 'İçeriği sil':
                self.change(lambda doc: erase(doc[self.page], rect))
            elif mode in ('Resim ekle', 'İmza ekle'):
                path, _ = QFileDialog.getOpenFileName(self, 'Resim seç', '', 'Resimler (*.png *.jpg *.jpeg *.bmp)')
                if path:
                    self.change(lambda doc: doc[self.page].insert_image(rect, filename=path, keep_proportion=True))
                    self.set_mode('Resmi boyutlandır')
                    self.statusBar().showMessage('Resim eklendi. Boyutunu değiştirmek için resmin ortasına tıklayın.')
            elif mode == 'Vurgula':
                self.change(lambda doc: doc[self.page].add_highlight_annot(rect))
            elif mode == 'Dikdörtgen':
                self.change(lambda doc: doc[self.page].draw_rect(rect, color=color, width=2))
            elif mode == 'Kırp':
                self.change(lambda doc: doc[self.page].set_cropbox(rect + (page.cropbox_position.x, page.cropbox_position.y, page.cropbox_position.x, page.cropbox_position.y)))
            elif mode == 'Form alanı':
                self.add_form_field(rect)
            elif mode == 'Daire':
                self.draw_circle(rect)
            elif mode == 'Bağlantı ekle':
                self.add_link_at(rect)
        self.guarded(run)()

    def move_selected_text(self, source, destination):
        def run():
            page = self.editor.doc[self.page]
            source_rect = source * page.derotation_matrix
            target_rect = destination * page.derotation_matrix
            self.change(lambda doc: move_text(doc[self.page], source_rect, target_rect))
            self.statusBar().showMessage('Metin özgün yazı biçimi korunarak taşındı. Ctrl+Z ile geri alabilirsiniz.')
        self.guarded(run)()

    def undo(self, redo=False):
        self.editor.undo(redo)
        self.refresh()

    def merge(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Sona eklenecek PDF dosyaları', '', 'PDF (*.pdf)')
        if not paths:
            return
        def operation(doc):
            for path in paths:
                with fitz.open(path) as other:
                    if other.needs_pass:
                        raise ValueError('Birleştirme için parolalı PDF dosyasını önce açıp parolasız kopyasını kaydedin.')
                    doc.insert_pdf(other)
        self.change(operation)

    def split(self):
        value, ok = QInputDialog.getText(self, 'Sayfaları çıkar', 'Ayrı PDF olarak kaydedilecek sayfalar (ör. 1-3,5):',
            text=','.join(str(i + 1) for i in self.selected_pages()))
        if ok:
            indices = page_range(value, len(self.editor.doc))
            path = self.output_path('Seçili sayfaları kaydet')
            if path:
                if self.editor.path and Path(path).resolve() == Path(self.editor.path).resolve():
                    raise ValueError('Çıkarma işlemi için farklı bir dosya adı seçin.')
                extract(self.editor.doc, indices, path)
                self.statusBar().showMessage(f'{len(indices)} sayfa ayrı PDF olarak kaydedildi.')

    def compress(self):
        import advanced
        mode, ok = QInputDialog.getItem(self, 'PDF küçültme', 'Sıkıştırma yöntemi:',
            ['Kayıpsız — metin ve resim kalitesi korunur', 'Dengeli — resimler küçültülür (1600 piksel, JPEG %70)'], editable=False)
        if not ok:
            return
        path = self.output_path('Sıkıştırılmış kopya')
        if path:
            data = self.editor.doc.tobytes()
            self.background('PDF küçültme', lambda: advanced.compress_pdf(data, path, mode.startswith('Dengeli')),
                lambda sizes: QMessageBox.information(self, 'Sıkıştırma tamamlandı',
                    f'Bellekteki belge: {sizes[0]/1024:.0f} KB\nÇıktı: {sizes[1]/1024:.0f} KB\nKazanç: %{100*(1-sizes[1]/sizes[0]):.1f}\n\nZaten sıkıştırılmış PDF’lerde boyut azalmayabilir.'))

    def rotate(self):
        import pages
        selected = self.selected_pages()
        self.change(lambda doc: pages.rotate_pages(doc, selected))

    def delete_page(self):
        import pages
        selected = self.selected_pages()
        self.change(lambda doc: pages.delete_pages(doc, selected))

    def blank(self):
        self.change(lambda doc: doc.new_page(pno=self.page + 1))

    def move(self, direction):
        target = self.page + direction
        if 0 <= target < len(self.editor.doc):
            indices = list(range(len(self.editor.doc)))
            indices[self.page], indices[target] = indices[target], indices[self.page]
            self.editor.change(lambda doc: doc.select(indices))
            self.page = target
            self.refresh()

    def export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Sayfayı PNG aktar', f'sayfa-{self.page+1}.png', 'PNG (*.png)')
        if path:
            self.editor.doc[self.page].get_pixmap(matrix=fitz.Matrix(2, 2)).save(path)

    def export_text(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Metni dışa aktar', 'belge.txt', 'Metin (*.txt)')
        if path:
            Path(path).write_text('\n\n'.join(p.get_text() for p in self.editor.doc), encoding='utf-8')

    def protect(self):
        password, ok = QInputDialog.getText(self, 'Parolalı kopya', 'Yeni açılış parolası:', QLineEdit.EchoMode.Password)
        if ok and password:
            path = self.output_path('AES-256 parolalı kopya kaydet')
            if path:
                from engine import atomic_write
                atomic_write(path, self.editor.doc.tobytes(garbage=4, deflate=True,
                    encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password))
                self.statusBar().showMessage('Parolalı kopya kaydedildi.')

    def find(self):
        query = self.search.text().strip()
        if not query or self.editor.doc is None:
            return
        for offset in range(len(self.editor.doc)):
            i = (self.page + offset) % len(self.editor.doc)
            hits = self.editor.doc[i].search_for(query)
            if hits:
                self.page = i
                self.thumbs.setCurrentRow(i)
                self.render()
                for r in hits:
                    r = r * self.editor.doc[i].rotation_matrix
                    f = self.canvas.factor
                    self.canvas.scene().addRect(QRectF(r.x0*f, r.y0*f, r.width*f, r.height*f), QPen(QColor('#e1a700')), QColor(255, 222, 0, 80))
                self.statusBar().showMessage(f'Sayfa {i+1}: {len(hits)} eşleşme. Arama işaretleri belgeye kaydedilmez.')
                return
        self.statusBar().showMessage('Metin bulunamadı. Taranmış belgeler OCR gerektirebilir.')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile().lower().endswith('.pdf'):
                self.guarded(lambda: self.open(url.toLocalFile()))()
                break

    def closeEvent(self, event):
        try:
            if self.unsaved():
                self.discard_recovery()
                event.accept()
            else:
                event.ignore()
        except Exception as exc:
            QMessageBox.warning(self, 'Kaydedilemedi', str(exc))
            event.ignore()


if __name__ == '__main__':
    if '--verify-features' in sys.argv:
        from verification import verify_features
        results = verify_features(sys.argv[2])
        sys.exit(0 if all(r.get('ok') for r in results.values()) else 1)
    if '--verify-integrations' in sys.argv:
        from verification import verify_package
        results = verify_package(sys.argv[2])
        ai_state = results.get('ai', {})
        sys.exit(0 if results.get('pdfa', {}).get('compliant') and (ai_state.get('models') or ai_state.get('state') == 'disabled') else 1)
    app = QApplication(sys.argv)
    app.setApplicationName('PDF Stüdyo')
    window = Window()
    window.show()
    if len(sys.argv) > 1 and sys.argv[1] == '--verify-text':
        from PySide6.QtCore import QTimer
        from text_verification import verify_text
        QTimer.singleShot(300, lambda: verify_text(window, sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == '--smoke-test':
        from PySide6.QtCore import QTimer
        def smoke():
            window.new()
            window.change(lambda d: add_text(d[0], fitz.Rect(45, 60, 550, 150), 'PDF Stüdyo — Türkçe test', 22))
            window.grab().save(sys.argv[2] if len(sys.argv) > 2 else 'smoke.png')
            window.editor.dirty = False
            window.close()
        QTimer.singleShot(300, smoke)
    elif len(sys.argv) > 1:
        window.guarded(lambda: window.open(sys.argv[1]))()
    else:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, window.guarded(window.check_recovery))
    sys.exit(app.exec())
