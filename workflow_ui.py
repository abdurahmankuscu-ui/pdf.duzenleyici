"""Stamp dialog, batch processing, recent files and crash recovery."""
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QPushButton, QListWidget, QDialogButtonBox, QFileDialog, QMessageBox, QInputDialog,
    QMenu, QStackedWidget, QWidget, QLineEdit)
import integrations
import batch
import stamping
from engine import page_range
from session import Session

RECOVERY_INTERVAL_MS = 2 * 60 * 1000


def _buttons(dialog, ok_text):
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Vazgeç')
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class StampFields(QWidget):
    """Shared by the stamp dialog and the batch dialog's Damga operation."""
    def __init__(self, template='Sayfa {n} / {toplam}', position='Alt orta'):
        super().__init__()
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self.template = QLineEdit(template)
        form.addRow('Metin şablonu', self.template)
        hint = QLabel(stamping.PLACEHOLDERS)
        hint.setObjectName('muted')
        hint.setWordWrap(True)
        form.addRow('', hint)
        self.position = QComboBox()
        self.position.addItems(stamping.POSITIONS)
        self.position.setCurrentText(position)
        form.addRow('Konum', self.position)
        self.size = QSpinBox()
        self.size.setRange(4, 72)
        self.size.setValue(10)
        self.size.setSuffix(' pt')
        form.addRow('Yazı boyutu', self.size)
        self.start = QSpinBox()
        self.start.setRange(0, 10_000_000)
        self.start.setValue(1)
        form.addRow('Başlangıç numarası', self.start)
        self.prefix = QLineEdit()
        self.prefix.setPlaceholderText('ör. DAVA-')
        form.addRow('Bates öneki', self.prefix)
        self.digits = QSpinBox()
        self.digits.setRange(1, 12)
        self.digits.setValue(6)
        form.addRow('Bates basamak sayısı', self.digits)

    def options(self):
        return dict(template=self.template.text(), position=self.position.currentText(), size=self.size.value(),
                    start=self.start.value(), bates_prefix=self.prefix.text(), bates_digits=self.digits.value())


class StampDialog(QDialog):
    def __init__(self, parent, template='Sayfa {n} / {toplam}', position='Alt orta'):
        super().__init__(parent)
        self.setWindowTitle('Üstbilgi / altbilgi / Bates')
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        self.fields = StampFields(template, position)
        self.template, self.position = self.fields.template, self.fields.position
        layout.addWidget(self.fields)
        pages = QFormLayout()
        self.pages = QLineEdit()
        self.pages.setPlaceholderText('Boş bırakın: tüm sayfalar · ör. 1-3,5')
        pages.addRow('Sayfalar', self.pages)
        layout.addLayout(pages)
        layout.addWidget(_buttons(self, 'Uygula'))


class BatchDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Toplu işlem')
        self.resize(660, 720)
        layout = QVBoxLayout(self)
        note = QLabel('Seçilen PDF’lere aynı işlem uygulanır. Özgün dosyalar değiştirilmez; sonuçlar ayrı klasöre yazılır. '
                      'Parolalı dosyalar atlanır.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.files = QListWidget()
        self.files.setMinimumHeight(140)
        layout.addWidget(self.files, 1)
        row = QHBoxLayout()
        for text, fn in [('Dosya ekle', self.add_files), ('Klasör ekle', self.add_folder), ('Listeyi temizle', self.files.clear)]:
            button = QPushButton(text)
            button.clicked.connect(fn)
            row.addWidget(button)
        layout.addLayout(row)
        form = QFormLayout()
        self.operation = QComboBox()
        self.operation.addItems(batch.OPERATIONS)
        form.addRow('İşlem', self.operation)
        layout.addLayout(form)
        self.options = QStackedWidget()
        self.lossy = QCheckBox('Dengeli: resimleri küçült (1600 piksel, JPEG %70)')
        self.language = QComboBox()
        self.language.addItems(['tur+eng', 'tur', 'eng'])
        self.watermark = QLineEdit('TASLAK')
        self.stamp = StampFields()
        for widget in (self.lossy, self.language, self.watermark, self.stamp):
            self.options.addWidget(widget)
        self.operation.currentIndexChanged.connect(self.options.setCurrentIndex)
        layout.addWidget(self.options)
        out = QHBoxLayout()
        self.output = QLineEdit()
        self.output.setPlaceholderText('Çıktı klasörü')
        choose = QPushButton('Seç…')
        choose.clicked.connect(self.choose_output)
        out.addWidget(self.output)
        out.addWidget(choose)
        layout.addLayout(out)
        layout.addWidget(_buttons(self, 'Başlat'))

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'PDF dosyaları', '', 'PDF (*.pdf)')
        self.files.addItems(paths)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'PDF klasörü')
        if folder:
            self.files.addItems(sorted(str(p) for p in Path(folder).glob('*.pdf')))

    def choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, 'Çıktı klasörü')
        if folder:
            self.output.setText(folder)

    def values(self):
        operation = self.operation.currentText()
        options = {'Küçült': lambda: dict(lossy=self.lossy.isChecked()),
                   'OCR': lambda: dict(language=self.language.currentText()),
                   'Filigran': lambda: dict(text=self.watermark.text()),
                   'Damga': self.stamp.options}[operation]()
        return dict(files=[Path(self.files.item(i).text()) for i in range(self.files.count())],
                    output=Path(self.output.text()) if self.output.text().strip() else None,
                    operation=operation, options=options)


class WorkflowMixin:
    def setup_workflow(self):
        self.session = Session(integrations.APP_DATA)
        self.recent_menu = QMenu('Son açılanlar', self)
        self.recent_menu.aboutToShow.connect(self.rebuild_recent_menu)
        self.file_menu.insertMenu(self.file_menu.actions()[0], self.recent_menu)
        from theme import THEMES
        view = self.tools_menu.addMenu('Görünüm')
        self.theme_actions = {}
        for choice in THEMES:
            action = view.addAction(f'Tema: {choice}')
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, c=choice: self.set_theme(c))
            self.theme_actions[choice] = action
        help_menu = next(a.menu() for a in self.tools_menu.actions() if a.text() == 'Yardım')
        self.action(help_menu, 'Güncellemeleri denetle', self.check_updates, needs=False)
        self.apply_saved_theme()
        self.recovery_timer = QTimer(self)
        self.recovery_timer.timeout.connect(lambda: self.guarded(self.autosave_recovery)())
        self.recovery_timer.start(RECOVERY_INTERVAL_MS)

    def set_theme(self, choice):
        from theme import stylesheet
        self.setStyleSheet(stylesheet(choice))
        self.session.set_preference('theme', choice)
        for name, action in getattr(self, 'theme_actions', {}).items():
            action.setChecked(name == choice)

    def apply_saved_theme(self):
        from theme import stylesheet, THEMES
        choice = self.session.preference('theme', 'Açık')
        choice = choice if choice in THEMES else 'Açık'
        self.setStyleSheet(stylesheet(choice))
        for name, action in getattr(self, 'theme_actions', {}).items():
            action.setChecked(name == choice)

    def check_updates(self):
        import updater
        from version import VERSION
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        result = []
        self.background('Güncellemeler denetleniyor', lambda: updater.check_for_update(VERSION), result.append)
        info = result[0]
        if info['latest'] is None:
            QMessageBox.information(self, 'Güncelleme', f'Henüz yayınlanmış bir sürüm yok. Kullandığınız sürüm: {VERSION}')
            return
        if not info['newer']:
            QMessageBox.information(self, 'Güncelleme', f'En güncel sürümü kullanıyorsunuz ({VERSION}).')
            return
        answer = QMessageBox.question(self, 'Yeni sürüm var',
            f"Yeni sürüm: {info['latest']} (kullandığınız: {VERSION}).\n\n"
            'İndirme sayfası tarayıcıda açılsın mı? Dosyayı yalnızca bu proje sayfasından indirin.')
        if answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(info['url']))

    def stamp_dialog(self, template='Sayfa {n} / {toplam}', position='Alt orta'):
        dialog = StampDialog(self, template, position)
        if not dialog.exec():
            return
        options = dialog.fields.options()
        pages = page_range(dialog.pages.text(), len(self.editor.doc)) if dialog.pages.text().strip() else None
        color = self.color
        self.change(lambda doc: stamping.stamp_pages(doc, options.pop('template'), options.pop('position'),
                                                     pages=pages, color=color, **options))
        self.statusBar().showMessage('Damga eklendi. Ctrl+Z ile geri alabilirsiniz.')

    def batch_dialog(self):
        dialog = BatchDialog(self)
        if not dialog.exec():
            return
        values = dialog.values()
        if not values['files']:
            raise ValueError('En az bir PDF ekleyin.')
        if values['output'] is None:
            raise ValueError('Çıktı klasörünü seçin.')
        results = []
        self.background(f"Toplu işlem: {values['operation']} ({len(values['files'])} dosya)",
                        lambda: batch.run_batch(values['files'], values['output'], values['operation'], values['options']),
                        results.extend)
        self.result_text('Toplu işlem raporu', batch.report(results))

    def rebuild_recent_menu(self):
        self.recent_menu.clear()
        recent = self.session.recent()
        for path in recent:
            action = self.recent_menu.addAction(Path(path).name + '  —  ' + path)
            action.triggered.connect(lambda _=False, p=path: self.guarded(lambda: self.open(p))())
        if recent:
            self.recent_menu.addSeparator()
            self.recent_menu.addAction('Listeyi temizle').triggered.connect(self.session.clear_recent)
        else:
            self.recent_menu.addAction('Henüz dosya yok').setEnabled(False)

    def autosave_recovery(self):
        if self.editor.doc is not None and self.editor.dirty:
            self.session.save_recovery(self.editor)

    def discard_recovery(self):
        self.session.discard_recovery(self.editor)

    def check_recovery(self):
        """Offer documents left behind by a crash or power loss."""
        for entry in self.session.recoveries():
            name = Path(entry['original']).name if entry.get('original') else 'Kaydedilmemiş yeni belge'
            answer = QMessageBox.question(self, 'Kurtarılan belge',
                f'Beklenmedik kapanıştan önce kaydedilmemiş değişiklikler bulundu:\n{name}\n'
                f"Son otomatik kayıt: {entry['saved']}\n\nGeri yüklensin mi? (Hayır: kurtarma kopyası silinir)")
            if answer != QMessageBox.StandardButton.Yes:
                self.session.discard_recovery(slot=entry['id'])
                continue
            password = ''
            if entry.get('protected'):
                password, ok = QInputDialog.getText(self, 'Kurtarılan belge', 'Belge parolası:', QLineEdit.EchoMode.Password)
                if not ok:
                    continue
            self.editor.open(entry['file'], password)
            self.editor.path = entry.get('original')
            self.editor.dirty = True
            # Move the copy to the restored document's own slot at once, so a
            # second crash before the next autosave loses nothing.
            self.session.discard_recovery(slot=entry['id'])
            self.autosave_recovery()
            self.page = 0
            self.refresh()
            self.statusBar().showMessage('Belge geri yüklendi. Kalıcı olması için kaydedin.')
            return
