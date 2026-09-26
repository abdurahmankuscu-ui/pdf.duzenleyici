"""Dialogs for pattern redaction and certificate signatures."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QListWidget, QListWidgetItem, QDialogButtonBox, QFileDialog, QMessageBox)
import redaction
import signing

HIT_ROLE = Qt.ItemDataRole.UserRole


def _buttons(dialog, ok_text):
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Vazgeç')
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class RedactionDialog(QDialog):
    """Preview every finding; nothing is removed until the user confirms."""
    def __init__(self, parent, hits):
        super().__init__(parent)
        self.setWindowTitle('Hassas verileri karart')
        self.resize(620, 520)
        layout = QVBoxLayout(self)
        info = QLabel(f'{len(hits)} bulgu. TCKN ve IBAN değerleri kontrol basamağıyla doğrulandı. '
                      'Karartılmayacakların işaretini kaldırın. Karartma kaydedildiğinde kalıcıdır; kayıttan önce Ctrl+Z ile geri alınabilir.')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.list = QListWidget()
        for hit in hits:
            item = QListWidgetItem(f"Sayfa {hit['page']+1} · {hit['kind']} · {hit['text']}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(HIT_ROLE, hit)
            self.list.addItem(item)
        layout.addWidget(self.list)
        layout.addWidget(_buttons(self, 'Seçilenleri karart'))

    def selected(self):
        return [self.list.item(i).data(HIT_ROLE) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]


class SignDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Dijital imza (sertifikalı)')
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        note = QLabel('Kişisel .pfx/.p12 sertifikanızla PAdES imzası oluşturulur ve yeni bir dosyaya kaydedilir. '
                      'İmzalı dosyada yapılacak sonraki düzenlemeler imzayı geçersiz kılar. '
                      'Sertifika parolası saklanmaz.')
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        row = QHBoxLayout()
        self.pfx = QLineEdit()
        browse = QPushButton('Seç…')
        browse.clicked.connect(self.browse)
        row.addWidget(self.pfx)
        row.addWidget(browse)
        form.addRow('Sertifika dosyası', row)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Sertifika parolası', self.password)
        self.reason = QLineEdit('Onaylıyorum')
        form.addRow('Neden', self.reason)
        self.location = QLineEdit()
        form.addRow('Yer', self.location)
        layout.addLayout(form)
        layout.addWidget(_buttons(self, 'İmzala'))

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Sertifika seç', '', 'Sertifika (*.pfx *.p12)')
        if path:
            self.pfx.setText(path)

    def values(self):
        return dict(pfx=self.pfx.text().strip(), pfx_password=self.password.text(),
                    reason=self.reason.text().strip(), location=self.location.text().strip())


class SecurityMixin:
    def auto_redact(self):
        hits = redaction.find_sensitive(self.editor.doc)
        if not hits:
            QMessageBox.information(self, 'Hassas veri', 'TCKN, IBAN, e-posta veya telefon bulunamadı.\n'
                                    'Taranmış belgelerde önce OCR uygulayın.')
            return
        dialog = RedactionDialog(self, hits)
        if not dialog.exec():
            return
        chosen = dialog.selected()
        if chosen:
            self.change(lambda doc: redaction.redact_hits(doc, chosen))
            self.statusBar().showMessage(f'{len(chosen)} alan karartıldı. Kalıcı olması için kaydedin; Ctrl+Z ile geri alabilirsiniz.')

    def digital_sign(self, page, rect):
        dialog = SignDialog(self)
        if not dialog.exec():
            return
        values = dialog.values()
        if not values['pfx'] or not Path(values['pfx']).is_file():
            raise ValueError('Sertifika dosyası seçin (.pfx veya .p12).')
        output = self.output_path('İmzalı PDF kaydet')
        if not output:
            return
        # Protected documents are signed with their protection intact.
        password = self.editor.password
        import pymupdf as fitz
        options = dict(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password) if password else {}
        data = self.editor.doc.tobytes(garbage=4, deflate=True, **options)
        self.background('Dijital imza', lambda: signing.sign_pdf(
            data, output, values['pfx'], values['pfx_password'], page=page, rect=rect,
            reason=values['reason'], location=values['location'], password=password))
        self.set_mode('Gezin')
        answer = QMessageBox.question(self, 'İmza tamamlandı',
            f'İmzalı dosya kaydedildi:\n{output}\n\nİmzalı dosya açılsın mı? (Düzenleme yapmadan inceleyin.)')
        if answer == QMessageBox.StandardButton.Yes:
            self.open(output)

    def verify_document_signatures(self):
        path = self.editor.path if self.editor.path and self.editor.signed and not self.editor.dirty else None
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, 'İmzası doğrulanacak PDF', '', 'PDF (*.pdf)')
        if not path:
            return
        # The file on disk is checked: the in-memory copy is already re-serialized.
        data = Path(path).read_bytes()
        password = self.editor.password if self.editor.path and Path(path) == Path(self.editor.path) else None
        self.background('İmzalar doğrulanıyor', lambda: signing.verify_signatures(data, password),
                        lambda results: self.result_text('İmza doğrulama — ' + Path(path).name,
                                                         signing.verification_report(results)))
