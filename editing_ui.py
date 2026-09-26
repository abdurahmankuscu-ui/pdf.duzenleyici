"""Drawing, links, advanced form fields, bookmarks, comments panel and page selection."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialogButtonBox, QInputDialog, QMessageBox, QFrame, QListWidget,
    QListWidgetItem, QToolButton, QAbstractItemView, QSpinBox)
import pymupdf as fitz
import annotate
import forms
import outline
import pages

PAGE_ROLE = Qt.ItemDataRole.UserRole


class BookmarkDialog(QDialog):
    def __init__(self, parent, entries, page_count, current_page):
        super().__init__(parent)
        self.setWindowTitle('Yer imleri')
        self.resize(620, 460)
        self.page_count = page_count
        self.current_page = current_page
        layout = QVBoxLayout(self)
        info = QLabel('Düzey 1 ana başlıktır; alt başlıklar bir üst düzeyin altında yer alır.')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Düzey', 'Başlık', 'Sayfa'])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        for entry in entries:
            self.add_row(*entry)
        row = QHBoxLayout()
        for text, fn in [('Bu sayfayı ekle', lambda: self.add_row(1, 'Yeni yer imi', self.current_page)),
                         ('Sil', self.remove_row), ('Yukarı', lambda: self.shift(-1)), ('Aşağı', lambda: self.shift(1))]:
            button = QPushButton(text)
            button.clicked.connect(fn)
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Uygula')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Vazgeç')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_row(self, level, title, page):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, (value, maximum) in enumerate([(level, 9), (None, None), (page, self.page_count)]):
            if value is None:
                self.table.setItem(row, 1, QTableWidgetItem(title))
                continue
            spin = QSpinBox()
            spin.setRange(1, maximum)
            spin.setValue(value)
            self.table.setCellWidget(row, column, spin)

    def remove_row(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def shift(self, direction):
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or not 0 <= target < self.table.rowCount():
            return
        entries = self.entries()
        entries[row], entries[target] = entries[target], entries[row]
        self.table.setRowCount(0)
        for entry in entries:
            self.add_row(*entry)
        self.table.setCurrentCell(target, 1)

    def entries(self):
        return [(self.table.cellWidget(r, 0).value(), (self.table.item(r, 1) or QTableWidgetItem('')).text(),
                 self.table.cellWidget(r, 2).value()) for r in range(self.table.rowCount())]


class EditingMixin:
    def setup_editing(self):
        panel = QFrame()
        panel.setObjectName('pagePanel')
        panel.setFixedWidth(250)
        column = QVBoxLayout(panel)
        column.setContentsMargins(10, 18, 10, 10)
        heading = QLabel('YORUMLAR')
        heading.setObjectName('panelHeading')
        column.addWidget(heading)
        self.comments_list = QListWidget()
        self.comments_list.setWordWrap(True)
        self.comments_list.itemDoubleClicked.connect(lambda _: self.guarded(self.goto_comment)())
        column.addWidget(self.comments_list, 1)
        row = QHBoxLayout()
        for text, fn in [('Git', self.goto_comment), ('Düzenle', self.edit_comment), ('Sil', self.delete_comment)]:
            button = QPushButton(text)
            button.clicked.connect(self.guarded(fn))
            row.addWidget(button)
        column.addLayout(row)
        panel.hide()
        self.comments_panel = panel
        self.content_row.insertWidget(1, panel)
        toggle = QToolButton()
        toggle.setText('Yorumlar')
        toggle.setCheckable(True)
        toggle.toggled.connect(self.toggle_comments)
        self.comments_button = toggle
        self.docrow.insertWidget(1, toggle)
        self.thumbs.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.thumbs.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.thumbs.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.thumbs.setMovement(QListWidget.Movement.Snap)
        self.thumbs.model().rowsMoved.connect(lambda *_: self.guarded(self.pages_reordered)())
        self.canvas.stroked.connect(lambda points: self.guarded(lambda: self.draw_stroke(points))())
        self.canvas.dragged.connect(lambda a, b: self.guarded(lambda: self.draw_line(a, b))())

    def _rgb(self):
        return tuple(QColor(self.color).getRgbF()[:3])

    def _unrotate(self, point):
        return fitz.Point(point) * self.editor.doc[self.page].derotation_matrix

    def draw_stroke(self, points):
        points = [self._unrotate(p) for p in points]
        self.change(lambda doc: annotate.add_ink(doc[self.page], [points], color=self._rgb()))

    def draw_line(self, start, end):
        start, end = self._unrotate(start), self._unrotate(end)
        kind = self.canvas.mode
        self.change(lambda doc: annotate.add_shape(doc[self.page], kind, start, end, color=self._rgb()))

    def draw_circle(self, rect):
        self.change(lambda doc: annotate.add_shape(doc[self.page], 'Daire', rect.tl, rect.br, color=self._rgb()))

    def add_link_at(self, rect):
        value, ok = QInputDialog.getText(self, 'Bağlantı ekle',
            'Web adresi (https://…), e-posta (mailto:…) veya sayfa numarası:')
        if not ok or not value.strip():
            return
        target = int(value) if value.strip().isdigit() else value.strip()
        self.change(lambda doc: outline.add_link(doc[self.page], rect, target))
        self.statusBar().showMessage('Bağlantı eklendi.')

    def add_form_field(self, rect):
        kind, ok = QInputDialog.getItem(self, 'Yeni form alanı', 'Alan türü:', list(forms.FIELD_TYPES), editable=False)
        if not ok:
            return
        name, ok = QInputDialog.getText(self, 'Yeni form alanı',
            'Alan adı (radyo düğmelerinde aynı grup için aynı ad):')
        if not ok or not name.strip():
            return
        options = value = None
        if kind in ('Açılır liste', 'Liste'):
            text, ok = QInputDialog.getText(self, kind, 'Seçenekler (virgülle ayırın):')
            if not ok:
                return
            options = text.split(',')
        elif kind == 'Radyo düğmesi':
            value, ok = QInputDialog.getText(self, kind, 'Bu düğmenin değeri (ör. evet):')
            if not ok:
                return
        size = self.size.value()
        self.change(lambda doc: forms.add_field(doc[self.page], rect, kind, name, options=options,
                                                value=value, font_size=size))

    def form(self):
        page = self.editor.doc[self.page]
        widgets = list(page.widgets() or [])
        if not widgets:
            QMessageBox.information(self, 'Form alanları', 'Bu sayfada doldurulabilir alan yok. Form alanı aracıyla ekleyebilirsiniz.')
            return
        names = {v: k for k, v in forms.FIELD_TYPES.items()}
        labels = [f'{i+1}: {w.field_label or w.field_name} ({names.get(w.field_type, w.field_type_string)})'
                  for i, w in enumerate(widgets)]
        label, ok = QInputDialog.getItem(self, 'Form doldur', 'Alan:', labels, editable=False)
        if not ok:
            return
        widget = widgets[labels.index(label)]
        if widget.field_type in forms.CHOICE_TYPES:
            value, ok = QInputDialog.getItem(self, label, 'Değer:', list(widget.choice_values or []), editable=False)
        elif widget.field_type in (fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.PDF_WIDGET_TYPE_RADIOBUTTON):
            choice, ok = QInputDialog.getItem(self, label, 'Durum:', ['İşaretli', 'İşaretsiz'], editable=False)
            value = choice == 'İşaretli'
        else:
            value, ok = QInputDialog.getText(self, label, 'Değer:', text=str(widget.field_value or ''))
        if ok:
            xref = widget.xref
            self.change(lambda doc: forms.fill_field(doc[self.page], xref, value))

    def flatten_document_forms(self):
        answer = QMessageBox.question(self, 'Formu düzleştir',
            'Tüm form alanları sabit sayfa içeriğine dönüştürülecek ve artık düzenlenemeyecek. Devam edilsin mi?')
        if answer == QMessageBox.StandardButton.Yes:
            self.change(forms.flatten_forms)
            self.statusBar().showMessage('Form düzleştirildi. Ctrl+Z ile geri alabilirsiniz.')

    def edit_bookmarks(self):
        dialog = BookmarkDialog(self, outline.get_bookmarks(self.editor.doc), len(self.editor.doc), self.page + 1)
        if dialog.exec():
            entries = dialog.entries()
            self.change(lambda doc: outline.set_bookmarks(doc, entries))
            self.statusBar().showMessage(f'{len(entries)} yer imi kaydedildi.')

    def toggle_comments(self, visible):
        self.comments_panel.setVisible(visible)
        if self.comments_button.isChecked() != visible:
            self.comments_button.setChecked(visible)
        self.refresh_comments()

    def refresh_comments(self):
        if not hasattr(self, 'comments_list') or not self.comments_panel.isVisible():
            return
        row = self.comments_list.currentRow()
        self.comments_list.clear()
        for comment in annotate.list_comments(self.editor.doc) if self.editor.doc else []:
            item = QListWidgetItem(f"Sayfa {comment['page']+1} · {comment['type']}\n{comment['content']}")
            item.setData(PAGE_ROLE, comment)
            self.comments_list.addItem(item)
        # Keep the selection after an edit so the next action targets the same comment.
        self.comments_list.setCurrentRow(min(row, self.comments_list.count() - 1))

    def _comment(self):
        item = self.comments_list.currentItem()
        if item is None:
            raise ValueError('Önce listeden bir yorum seçin.')
        return item.data(PAGE_ROLE)

    def goto_comment(self):
        self.page = self._comment()['page']
        self.thumbs.setCurrentRow(self.page)
        self.render()

    def edit_comment(self):
        comment = self._comment()
        text, ok = QInputDialog.getMultiLineText(self, 'Yorumu düzenle', 'Yorum:', comment['content'])
        if ok:
            self.change(lambda doc: annotate.set_comment(doc, comment['page'], comment['xref'], text))

    def delete_comment(self):
        comment = self._comment()
        self.change(lambda doc: annotate.delete_comment(doc, comment['page'], comment['xref']))

    def selected_pages(self):
        rows = sorted(self.thumbs.row(item) for item in self.thumbs.selectedItems())
        return rows or [self.page]

    def pages_reordered(self):
        order = [self.thumbs.item(i).data(PAGE_ROLE) for i in range(self.thumbs.count())]
        if order == list(range(len(order))):
            return
        current = order.index(self.page)
        self.editor.change(lambda doc: pages.reorder(doc, order))
        self.page = current
        self.refresh()
