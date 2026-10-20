"""Page previews in the right-hand panel: rendered lazily for visible pages and
scaled to the panel width, which the user can drag to show large previews."""
from PySide6.QtCore import Qt, QSize, QTimer, QRect
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QImage, QPen
from PySide6.QtWidgets import QListWidgetItem
import pymupdf as fitz

PAGE_ROLE = Qt.ItemDataRole.UserRole
RENDERED_ROLE = Qt.ItemDataRole.UserRole + 1
DEFAULT_PANEL_WIDTH = 220
MIN_PANEL_WIDTH, MAX_PANEL_WIDTH = 150, 640
PANEL_PADDING = 64          # list padding, item margins and scroll bar
PAGE_RATIO = 1.414          # A4 box; other page shapes are centred inside it


class ThumbnailMixin:
    def setup_thumbnails(self):
        self.thumb_timer = QTimer(self)
        self.thumb_timer.setSingleShot(True)
        self.thumb_timer.setInterval(30)
        self.thumb_timer.timeout.connect(self.update_visible_thumbnails)
        self.thumbs.verticalScrollBar().valueChanged.connect(lambda _: self.thumb_timer.start())
        self.content_splitter.splitterMoved.connect(lambda *_: self._panel_resized())
        self.thumbs.setUniformItemSizes(True)
        width = self.session.preference('pages_panel_width', DEFAULT_PANEL_WIDTH)
        self.set_pages_panel_width(width if isinstance(width, int) else DEFAULT_PANEL_WIDTH, remember=False)

    def thumbnail_box(self):
        width = max(80, self.pages_panel.width() - PANEL_PADDING)
        return QSize(width, round(width * PAGE_RATIO))

    def set_pages_panel_width(self, width, remember=True):
        width = max(MIN_PANEL_WIDTH, min(MAX_PANEL_WIDTH, int(width)))
        sizes = self.content_splitter.sizes()
        index = self.content_splitter.indexOf(self.pages_panel)
        total = sum(sizes)
        if total > 0:
            sizes[0] = max(200, sizes[0] + sizes[index] - width)
            sizes[index] = width
            self.content_splitter.setSizes(sizes)
        self.pages_panel.resize(width, self.pages_panel.height())
        self._apply_thumbnail_size(width)
        if remember:
            self.session.set_preference('pages_panel_width', width)

    def _panel_resized(self):
        width = self.pages_panel.width()
        self._apply_thumbnail_size(width)
        self.session.set_preference('pages_panel_width', width)

    def _apply_thumbnail_size(self, panel_width):
        box = QSize(max(80, panel_width - PANEL_PADDING), round(max(80, panel_width - PANEL_PADDING) * PAGE_RATIO))
        if box == self.thumbs.iconSize():
            return
        self.thumbs.setIconSize(box)
        placeholder = self._placeholder(box)
        for row in range(self.thumbs.count()):
            item = self.thumbs.item(row)
            item.setIcon(placeholder)
            item.setData(RENDERED_ROLE, False)
        self.thumb_timer.start()

    def _placeholder(self, box):
        pixmap = QPixmap(box)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor('#d5dde5'), 1))
        painter.setBrush(QColor('#ffffff'))
        painter.drawRect(QRect(0, 0, box.width() - 1, box.height() - 1))
        painter.end()
        return self._icon(pixmap)

    @staticmethod
    def _icon(pixmap):
        # Same image for every mode: Qt otherwise tints the selected preview blue.
        icon = QIcon()
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Selected, QIcon.Mode.Active):
            icon.addPixmap(pixmap, mode)
        return icon

    def populate_thumbnails(self):
        doc = self.editor.doc
        self.thumbs.blockSignals(True)
        self.thumbs.clear()
        placeholder = self._placeholder(self.thumbs.iconSize())
        for i in range(len(doc)):
            item = QListWidgetItem(placeholder, f'Sayfa {i+1}')
            # Original index lets drag-and-drop compute the new page order.
            item.setData(PAGE_ROLE, i)
            item.setData(RENDERED_ROLE, False)
            self.thumbs.addItem(item)
        self.thumbs.setCurrentRow(self.page)
        self.thumbs.blockSignals(False)
        self.thumb_timer.start()

    def update_visible_thumbnails(self):
        if self.editor.doc is None or not self.thumbs.count():
            return
        # One extra screen above and below keeps scrolling smooth.
        area = self.thumbs.viewport().rect()
        area = area.adjusted(0, -area.height(), 0, area.height())
        for row in range(self.thumbs.count()):
            item = self.thumbs.item(row)
            if not item.data(RENDERED_ROLE) and self.thumbs.visualItemRect(item).intersects(area):
                self.render_thumbnail(row)

    def render_thumbnail(self, row):
        item = self.thumbs.item(row)
        page = self.editor.doc[row]
        box = self.thumbs.iconSize()
        ratio = self.thumbs.devicePixelRatioF() or 1
        scale = min(box.width() / page.rect.width, box.height() / page.rect.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale * ratio, scale * ratio), alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        canvas = QPixmap(QSize(round(box.width() * ratio), round(box.height() * ratio)))
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        x, y = (canvas.width() - image.width()) // 2, (canvas.height() - image.height()) // 2
        painter.drawImage(x, y, image)
        painter.setPen(QPen(QColor('#c9d3dd'), 1))
        painter.drawRect(QRect(x, y, image.width() - 1, image.height() - 1))
        painter.end()
        canvas.setDevicePixelRatio(ratio)
        item.setIcon(self._icon(canvas))
        item.setData(RENDERED_ROLE, True)
