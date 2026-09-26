"""Resize an independently placed PDF image without replacing shared image data."""
import re
import pymupdf as fitz
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QCheckBox, QDialogButtonBox)

NUMBER = rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
PLACEMENT = re.compile(rb'\bq\s+(' + rb'\s+'.join([NUMBER]*6) + rb')\s+cm\s+/([^\s/]+)\s+Do\s+Q\b')


def image_placements(page):
    data = b'\n'.join(page.parent.xref_stream(x) for x in page.get_contents())
    names = {entry[7].encode() for entry in page.get_images(full=True)}
    result = []
    for match in PLACEMENT.finditer(data):
        if match[2] not in names:
            continue
        matrix = fitz.Matrix(*map(float, match[1].split()))
        rect = fitz.Rect(0,0,1,1) * matrix * page.transformation_matrix
        result.append(dict(start=match.start(1),end=match.end(1),matrix=matrix,rect=rect))
    return data, result


def selected_image(page, selection):
    _, placements = image_placements(page)
    center = (selection.tl + selection.br)/2
    candidates = [item for item in placements if item['rect'].contains(center)]
    if not candidates:
        raise ValueError('Eklediğiniz resmin ortasına tıklayın. Belgeye gömülü karmaşık resim grupları bu araçla boyutlandırılamaz.')
    return candidates[-1]


def resize_image(page, placement, destination):
    destination = fitz.Rect(destination)
    bounds = page.rect * page.derotation_matrix
    if destination.is_empty or not bounds.contains(destination):
        raise ValueError('Resim sayfa sınırları içinde olmalı. Boyutu veya konumunu azaltın.')
    data, placements = image_placements(page)
    current = next((p for p in placements if p['start']==placement['start']), None)
    if current is None or current['rect'] != placement['rect']:
        raise ValueError('Resim değişti. Resmi yeniden seçin.')
    source = current['rect']
    sx,sy = destination.width/source.width,destination.height/source.height
    transform = fitz.Matrix(sx,0,0,sy,destination.x0-source.x0*sx,destination.y0-source.y0*sy)
    matrix = current['matrix'] * page.transformation_matrix * transform * ~page.transformation_matrix
    encoded = ' '.join(f'{n:.8f}' for n in matrix).encode()
    updated = data[:current['start']] + encoded + data[current['end']:]
    # A new content stream isolates this page even if the old stream was shared.
    xref = page.parent.get_new_xref()
    page.parent.update_object(xref, '<<>>')
    page.parent.update_stream(xref, updated)
    page.set_contents(xref)


class ImageSizeDialog(QDialog):
    def __init__(self,parent,rect,apply_size):
        super().__init__(parent)
        self.setWindowTitle('Resmi boyutlandır')
        self.setMinimumWidth(410)
        self.apply_size = apply_size
        self.ratio = rect.width/rect.height
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Resmin boyutunu ve sayfadaki konumunu ayarlayın.'))
        form = QFormLayout()
        self.fields = {}
        for key,title,value in [('x','Soldan',rect.x0),('y','Üstten',rect.y0),('width','Genişlik',rect.width),('height','Yükseklik',rect.height)]:
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setRange(0 if key in ('x','y') else 0.1, 5000)
            spin.setSuffix(' mm')
            spin.setValue(value*25.4/72)
            self.fields[key] = spin
            form.addRow(title,spin)
        layout.addLayout(form)
        self.lock = QCheckBox('En-boy oranını koru')
        self.lock.setChecked(True)
        layout.addWidget(self.lock)
        self.fields['width'].valueChanged.connect(lambda v:self.sync('height',v/self.ratio))
        self.fields['height'].valueChanged.connect(lambda v:self.sync('width',v*self.ratio))
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:#ba2636')
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Uygula')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Vazgeç')
        buttons.accepted.connect(self.apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def sync(self,key,value):
        if self.lock.isChecked():
            self.fields[key].blockSignals(True)
            self.fields[key].setValue(value)
            self.fields[key].blockSignals(False)

    def apply(self):
        values = {k:spin.value()*72/25.4 for k,spin in self.fields.items()}
        rect = fitz.Rect(values['x'],values['y'],values['x']+values['width'],values['y']+values['height'])
        try:
            self.apply_size(rect)
        except Exception as exc:
            self.error.setText(str(exc))
            return
        self.accept()
