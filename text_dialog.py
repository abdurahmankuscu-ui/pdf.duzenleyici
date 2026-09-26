from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QDoubleSpinBox, QCheckBox, QDialogButtonBox)


class ReplaceTextDialog(QDialog):
    """Keep the user's draft visible when a replacement cannot be applied."""
    def __init__(self, parent, text, size, apply_text):
        super().__init__(parent)
        self.setWindowTitle('Metni değiştir')
        self.resize(660, 390)
        self.apply_text = apply_text
        self.used_size = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'Mevcut yazı boyutu: {size:.1f} pt. Yeni metni aşağıya yazın.'))
        self.font_info = QLabel()
        self.font_info.setWordWrap(True)
        layout.addWidget(self.font_info)
        self.text = QTextEdit()
        self.text.setAcceptRichText(False)
        self.text.setPlainText(text)
        layout.addWidget(self.text)
        options = QHBoxLayout()
        options.addWidget(QLabel('Yazı boyutu:'))
        self.size = QDoubleSpinBox()
        self.size.setRange(6, 120)
        self.size.setDecimals(1)
        self.size.setValue(size)
        self.size.setSuffix(' pt')
        options.addWidget(self.size)
        self.auto_fit = QCheckBox('Gerekirse alana sığdır (en az 6 pt)')
        self.auto_fit.setChecked(True)
        options.addWidget(self.auto_fit)
        layout.addLayout(options)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:#ba2636;')
        layout.addWidget(self.error)
        self.main_layout = layout
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Uygula')
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Vazgeç')
        self.buttons.accepted.connect(self.apply)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def configure_area(self, rect, bounds):
        import pymupdf as fitz
        self.resize(720,480)
        self.original_rect = fitz.Rect(rect)
        row = QHBoxLayout()
        row.addWidget(QLabel('Yazı alanı — genişlik:'))
        self.area_width = QDoubleSpinBox()
        self.area_height = QDoubleSpinBox()
        for spin,value,maximum in [(self.area_width,rect.width,bounds.x1-rect.x0),
                                   (self.area_height,rect.height,bounds.y1-rect.y0)]:
            spin.setDecimals(2)
            spin.setRange(0.1,maximum*25.4/72)
            spin.setSuffix(' mm')
            spin.setValue(value*25.4/72)
        row.addWidget(self.area_width)
        row.addWidget(QLabel('Yükseklik:'))
        row.addWidget(self.area_height)
        self.initial_area = (self.area_width.value(),self.area_height.value())
        self.main_layout.insertLayout(self.main_layout.count()-1,row)
        note=QLabel('Alan sağa ve aşağı büyür. Komşu yazıları kapatmadığını kontrol edin. Yalnızca başlangıçta seçtiğiniz eski metin silinir.')
        note.setWordWrap(True)
        self.main_layout.insertWidget(self.main_layout.count()-1,note)

    def output_rect(self):
        import pymupdf as fitz
        rect=fitz.Rect(self.original_rect)
        if (self.area_width.value(),self.area_height.value()) != self.initial_area:
            rect.x1=rect.x0+self.area_width.value()*72/25.4
            rect.y1=rect.y0+self.area_height.value()*72/25.4
        return rect

    def set_font_info(self, style):
        name = style.get('font_name')
        self.font_info.setText(f'Font: {name}. Desteklenen harflerde özgün font kullanılır; eksik harflerde benzer fonta geçilir.' if name else
            'PDF ile aynı font için önce “Yazı stili al” aracıyla örnek yazıyı seçin.')

    def apply(self):
        try:
            self.used_size = self.apply_text(self.text.toPlainText(), self.size.value(), self.auto_fit.isChecked())
        except Exception as exc:
            self.error.setText(str(exc))
            return
        self.accept()
