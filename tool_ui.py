from pathlib import Path
import tempfile
import pymupdf as fitz
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QTextDocument, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QProgressDialog, QFileDialog, QInputDialog, QMessageBox, QLineEdit)
import advanced
import integrations
from engine import add_text, atomic_write


class Job(QThread):
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.result.emit(self.operation())
        except Exception as exc:
            self.failed.emit(str(exc))


class ToolsMixin:
    def setup_tools(self):
        menus = [
            ('PDF düzenle', [('PDF birleştir', self.merge, True), ('PDF ayır / sayfaları ayıkla', self.split, True),
                ('Sayfaları kaldır', self.remove_pages, True), ('PDF düzenle', lambda: self.set_mode('Metin ekle'), True),
                ("PDF’e tara", self.scan, False), ('Toplu işlem (klasör)', self.batch_dialog, False), ('Yazdır', self.print_pdf, True)]),
            ("PDF’i iyileştir", [('PDF küçültme', self.compress, True), ("PDF’i onar", self.repair, False), ('OCR PDF', self.ocr, True)]),
            ("PDF’e dönüştür", [('JPG / PNG → PDF', self.from_images, False), ('Word → PDF', lambda: self.from_office('Word'), False),
                ('PowerPoint → PDF', lambda: self.from_office('PowerPoint'), False), ('Excel → PDF', lambda: self.from_office('Excel'), False),
                ('HTML → PDF', self.from_html, False)]),
            ("PDF’ten dönüştür", [('PDF → JPG', self.to_jpg, True), ('PDF → Word', lambda: self.convert('Word'), True),
                ('PDF → PowerPoint', lambda: self.convert('PowerPoint'), True), ('PDF → Excel', lambda: self.convert('Excel'), True),
                ('PDF → PDF/A', self.to_pdfa, True), ('PDF → Markdown', lambda: self.convert('Markdown'), True)]),
            ('Sayfa araçları', [("PDF’i döndür", self.rotate, True), ('Sayfa numarası ekle', self.numbers, True),
                ('Üstbilgi / altbilgi / Bates', self.stamp_dialog, True),
                ('Filigran ekle', self.watermark, True), ('PDF kırpma', lambda: self.set_mode('Kırp'), True),
                ('PDF formları: doldur', self.form, True), ('PDF formları: alan ekle', lambda: self.set_mode('Form alanı'), True),
                ('PDF formları: düzleştir', self.flatten_document_forms, True), ('Yer imleri', self.edit_bookmarks, True),
                ('Bağlantı ekle', lambda: self.set_mode('Bağlantı ekle'), True)]),
            ('PDF güvenliği', [('PDF kilidini aç', self.unlock, False), ("PDF’i koru", self.protect, True),
                ('PDF imzala (görsel)', lambda: self.set_mode('İmza ekle'), True),
                ('Hassas içeriği kalıcı kaldır', lambda: self.set_mode('İçeriği sil'), True),
                ('Hassas verileri bul ve karart', self.auto_redact, True),
                ('Dijital imza (sertifikalı)', lambda: self.set_mode('Dijital imza'), True),
                ('İmzaları doğrula', self.verify_document_signatures, False),
                ('Gizli verileri temizle', self.sanitize_document, True), ('Parolasız kaydet', self.save_without_password, True),
                ('PDF karşılaştırma', self.compare_pdf, True)]),
            ('Yapay zekâ', [('Yapay zekâ özetleyici', lambda: self.ai(False), True), ('PDF çevir', lambda: self.ai(True), True)]),
        ]
        for title, entries in menus:
            menu = self.tools_menu.addMenu(title)
            if title == 'Yapay zekâ':
                self.ai_switch = self.action(menu, 'Yerel AI etkin (isteğe bağlı)', self.toggle_ai, needs=False)
                self.ai_switch.setCheckable(True)
                self.ai_switch.setChecked(integrations.ai_enabled())
                menu.addSeparator()
            for label, fn, needs in entries:
                self.action(menu, label, fn, needs=needs)
        help_menu = self.tools_menu.addMenu('Yardım')
        self.action(help_menu, 'Özellikler ve gereksinimler', self.about, needs=False)
        self.action(help_menu, 'Entegrasyon durumu', self.integration_status, needs=False)

    def background(self, title, operation, done=None):
        dialog = QProgressDialog(title + '…', '', 0, 0, self)
        dialog.setWindowTitle('PDF Stüdyo')
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        job = Job(operation, dialog)
        result = []
        errors = []
        job.result.connect(result.append)
        job.failed.connect(errors.append)
        job.finished.connect(dialog.accept)
        job.start()
        dialog.exec()
        job.wait()
        if errors:
            raise RuntimeError(errors[0])
        if done:
            done(result[0] if result else None)
        else:
            self.statusBar().showMessage(title + ' tamamlandı.')

    def result_text(self, title, text):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(850, 650)
        layout = QVBoxLayout(dialog)
        edit = QTextEdit()
        edit.setPlainText(text)
        layout.addWidget(edit)
        buttons = QHBoxLayout()
        save = QPushButton('Metin olarak kaydet')
        def save_text():
            path, _ = QFileDialog.getSaveFileName(dialog, title, 'sonuc.txt', 'Metin (*.txt);;Markdown (*.md)')
            if path:
                Path(path).write_text(edit.toPlainText(), encoding='utf-8')
        save.clicked.connect(self.guarded(save_text))
        buttons.addWidget(save)
        pdf = QPushButton('PDF olarak kaydet')
        def save_pdf():
            path, _ = QFileDialog.getSaveFileName(dialog, title, 'sonuc.pdf', 'PDF (*.pdf)')
            if path:
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                edit.document().print_(printer)
        pdf.clicked.connect(self.guarded(save_pdf))
        buttons.addWidget(pdf)
        close = QPushButton('Kapat')
        close.clicked.connect(dialog.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dialog.exec()

    def from_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Resimleri seç (dosya adı sırasıyla)', '', 'Resimler (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)')
        if paths:
            output = self.output_path('Resimlerden PDF oluştur')
            if output:
                self.background('Resimlerden PDF oluşturma', lambda: advanced.images_pdf(sorted(paths), output))

    def from_office(self, kind):
        filters = {'Word': 'Word (*.doc *.docx *.odt *.rtf)', 'Excel': 'Excel (*.xls *.xlsx *.ods)', 'PowerPoint': 'Sunum (*.ppt *.pptx *.odp)'}
        source, _ = QFileDialog.getOpenFileName(self, kind + ' dosyası', '', filters[kind])
        if source:
            output = self.output_path(kind + ' → PDF')
            if output:
                self.background(kind + ' → PDF', lambda: advanced.office_pdf(source, output, kind))

    def from_html(self):
        source, _ = QFileDialog.getOpenFileName(self, 'Yerel HTML dosyası', '', 'HTML (*.html *.htm)')
        if not source:
            return
        output = self.output_path('HTML → PDF')
        if output:
            document = QTextDocument()
            document.setBaseUrl(QUrl.fromLocalFile(str(Path(source).parent) + '/'))
            document.setHtml(Path(source).read_text(encoding='utf-8', errors='replace'))
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            printer.setOutputFileName(output)
            document.print_(printer)
            self.statusBar().showMessage('HTML PDF olarak kaydedildi. Temel HTML/CSS desteklenir; JavaScript çalıştırılmaz.')

    def convert(self, kind):
        extensions = {'Word': 'docx', 'Excel': 'xlsx', 'PowerPoint': 'pptx', 'Markdown': 'md'}
        descriptions = {'Word': 'Düzenlenebilir metin ve resimler aktarılır; sayfa düzeni birebir korunmaz.',
                        'Excel': 'Algılanan tablolar hücrelere aktarılır. Tablo yoksa metinler satırlara aktarılır.',
                        'PowerPoint': 'Her PDF sayfası slayta resim olarak aktarılır; slayt içindeki metin ayrı düzenlenemez.',
                        'Markdown': 'Sayfa başlıkları ve okunabilir metin aktarılır.'}
        ext = extensions[kind]
        output, _ = QFileDialog.getSaveFileName(self, descriptions[kind], 'belge.' + ext, f'{kind} (*.{ext})')
        if output:
            data = self.editor.doc.tobytes()
            fn = {'Word': advanced.pdf_word, 'Excel': advanced.pdf_excel, 'PowerPoint': advanced.pdf_pptx, 'Markdown': advanced.pdf_markdown}[kind]
            self.background('PDF → ' + kind, lambda: fn(data, output))

    def to_jpg(self):
        folder = QFileDialog.getExistingDirectory(self, 'JPG sayfaları için klasör seçin')
        if folder:
            data = self.editor.doc.tobytes()
            def operation():
                # A unique child folder prevents overwriting existing page images.
                output = Path(tempfile.mkdtemp(prefix='PDF-Sayfalar-', dir=folder))
                with fitz.open(stream=data, filetype='pdf') as doc:
                    for n, page in enumerate(doc):
                        page.get_pixmap(dpi=150).save(str(output / f'sayfa-{n+1:04}.jpg'), jpg_quality=90)
                return output
            self.background('JPG aktarımı', operation, lambda p: self.statusBar().showMessage(f'JPG dosyaları: {p}'))

    def numbers(self):
        self.stamp_dialog('{n}', 'Alt orta')

    def watermark(self):
        text, ok = QInputDialog.getText(self, 'Filigran', 'Tüm sayfalara eklenecek metin:')
        if ok and text:
            def operation(doc):
                import html
                for page in doc:
                    r = page.rect * page.derotation_matrix
                    page.insert_htmlbox(fitz.Rect(r.x0+30, r.y0+r.height/2-50, r.x1-30, r.y0+r.height/2+50),
                        '<div style="text-align:center">' + html.escape(text) + '</div>',
                        css='* {font-family:sans-serif;font-size:40pt;color:#777777}', opacity=0.25)
            self.change(operation)

    def remove_pages(self):
        from engine import page_range
        value, ok = QInputDialog.getText(self, 'Sayfaları kaldır', 'Kaldırılacak sayfalar (ör. 1-3,5):')
        if ok:
            removed = page_range(value, len(self.editor.doc))
            if len(removed) == len(self.editor.doc):
                raise ValueError('En az bir sayfa kalmalı.')
            self.change(lambda doc: doc.delete_pages(removed))

    def repair(self):
        source, _ = QFileDialog.getOpenFileName(self, 'Onarılacak PDF', '', 'PDF (*.pdf)')
        if source:
            output = self.output_path('Onarılmış PDF kopyası')
            if output:
                def operation():
                    with fitz.open(source) as doc:
                        if doc.needs_pass:
                            raise ValueError('Önce parola ile kilidi açın.')
                        atomic_write(output, doc.tobytes(garbage=4, clean=True, deflate=True))
                self.background('PDF yapısını onarma', operation)

    def ocr(self):
        language, ok = QInputDialog.getItem(self, 'OCR dili', 'Dil:', ['tur+eng', 'tur', 'eng'], editable=True)
        if ok:
            output = self.output_path('Aranabilir OCR kopyası')
            if output:
                data = self.editor.doc.tobytes()
                self.background('OCR (sayfalar 200 DPI görüntü + metin katmanına dönüştürülür)', lambda: advanced.ocr_pdf(data, output, language))

    def unlock(self):
        source, _ = QFileDialog.getOpenFileName(self, 'Parolası bilinen PDF', '', 'PDF (*.pdf)')
        if not source:
            return
        password, ok = QInputDialog.getText(self, 'PDF kilidini aç', 'Mevcut parola:', QLineEdit.EchoMode.Password)
        if ok:
            with fitz.open(source) as doc:
                if doc.needs_pass and not doc.authenticate(password):
                    raise ValueError('Parola hatalı.')
                output = self.output_path('Parolasız kopya')
                if output:
                    atomic_write(output, doc.tobytes(encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True))
                    self.statusBar().showMessage('Parolasız kopya kaydedildi.')

    def sanitize_document(self):
        from engine import sanitize
        answer = QMessageBox.question(self, 'Gizli verileri temizle',
            'Belge bilgileri (yazar, başlık, XMP), JavaScript, ekli/gömülü dosyalar ve sayfa önizlemeleri kaldırılacak.\n'
            'Görünen içerik, formlar, bağlantılar ve OCR metin katmanı korunur. Ctrl+Z ile geri alabilirsiniz.\n\nDevam edilsin mi?')
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.change(sanitize)
        self.statusBar().showMessage('Gizli veriler temizlendi. Kalıcı olması için kaydedin.')

    def save_without_password(self):
        answer = QMessageBox.question(self, 'Parolasız kaydet',
            'Belge parola koruması OLMADAN kaydedilecek. Dosyayı açan herkes içeriği görebilir.\n\nDevam edilsin mi?')
        if answer != QMessageBox.StandardButton.Yes:
            return
        path = self.output_path('Parolasız kaydet')
        if path:
            self.editor.save(path, '')
            self.refresh(False)
            self.statusBar().showMessage(f'Parolasız kaydedildi: {path}')

    def compare_pdf(self):
        other, _ = QFileDialog.getOpenFileName(self, 'Karşılaştırılacak PDF', '', 'PDF (*.pdf)')
        if other:
            data = self.editor.doc.tobytes()
            self.background('PDF karşılaştırma', lambda: advanced.compare(data, other), lambda text: self.result_text('Karşılaştırma raporu', text))

    def ai(self, translate):
        if not integrations.ai_enabled():
            QMessageBox.information(self, 'AI kapalı', 'Özetleme ve çeviri şu anda kapalı.\nKullanmak için Yapay zekâ > Yerel AI etkin seçeneğini işaretleyin.\nDiğer PDF araçları AI olmadan çalışır.')
            return
        found = []
        self.background('Yerel AI motoru hazırlanıyor', advanced.ollama_models, found.extend)
        models = found
        if not models:
            raise ValueError('Ollama’da yerel bir model yükleyin.')
        model, ok = QInputDialog.getItem(self, 'Yerel yapay zekâ', 'Model:', models, editable=False)
        if not ok:
            return
        if translate:
            language, ok = QInputDialog.getText(self, 'PDF çevir', 'Hedef dil:', text='Türkçe')
            if not ok or not language:
                return
            instruction = f'Belge metnini {language} diline çevir. Sayfa işaretlerini koru. Yalnızca çeviriyi yaz.'
        else:
            instruction = 'Belge parçasını Türkçe özetle. Ana noktaları ve sayfa referanslarını belirt. Bilgi uydurma.'
        data = self.editor.doc.tobytes()
        title = 'Çeviri' if translate else 'Yapay zekâ özeti'
        self.background(title, lambda: advanced.ai_document(data, model, instruction),
            lambda text: self.result_text(title + ' — Yapay zekâ çıktısını kontrol edin', text))

    def toggle_ai(self):
        enabled = self.ai_switch.isChecked()
        try:
            if enabled and not integrations.find_ollama():
                raise RuntimeError('Yerel AI kurulu değil. Herhangi bir model otomatik indirilmeyecek.')
            integrations.set_ai_enabled(enabled)
        finally:
            self.ai_switch.setChecked(integrations.ai_enabled())
        self.statusBar().showMessage('AI etkin; bir AI aracı seçtiğinizde motor başlar.' if enabled else 'AI kapalı. Yerel motor durduruldu; PDF araçlarını kullanabilirsiniz.')

    def scan(self):
        devices = integrations.scanner_devices()
        if not devices:
            dialog = QMessageBox(self)
            dialog.setWindowTitle('Tarayıcı bulunamadı')
            dialog.setText('Bağlı WIA tarayıcısı bulunamadı.\n\nTarayıcıyı bağlayın, açın ve üreticinin WIA sürücüsünü kurun.\nAlternatif olarak telefondan çekilmiş belge fotoğraflarını PDF’ye dönüştürebilirsiniz.')
            pictures = dialog.addButton('Fotoğraf / resimden PDF', QMessageBox.ButtonRole.ActionRole)
            dialog.addButton('Kapat', QMessageBox.ButtonRole.RejectRole)
            dialog.exec()
            if dialog.clickedButton() == pictures:
                self.from_images()
            return
        output = self.output_path('Taramayı PDF kaydet')
        if output:
            if advanced.scan_image(output):
                self.statusBar().showMessage('Tarama PDF olarak kaydedildi.')

    def to_pdfa(self):
        output = self.output_path('PDF/A-2 kopyası')
        if output:
            data = self.editor.doc.tobytes()
            self.background('PDF/A dönüşümü', lambda: advanced.pdfa(data, output),
                lambda _: QMessageBox.information(self, 'PDF/A doğrulandı', 'PDF/A-2b çıktısı veraPDF uygunluk kontrolünden geçti.\nDoğrulama raporu PDF’nin yanında .validation.xml olarak kaydedildi.'))

    def integration_status(self):
        self.background('Entegrasyonlar denetleniyor', integrations.status_text,
                        lambda text: self.result_text('Entegrasyon durumu', text))

    def print_pdf(self):
        from PySide6.QtGui import QPainter
        from PySide6.QtCore import QRectF
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setMinMax(1, len(self.editor.doc))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        painter = QPainter(printer)
        if not painter.isActive():
            raise RuntimeError('Yazıcı başlatılamadı.')
        try:
            first = max(1, printer.fromPage()) - 1
            last = printer.toPage() or len(self.editor.doc)
            for i in range(first, last):
                if i > first:
                    printer.newPage()
                pix = self.pixmap(self.editor.doc[i].get_pixmap(dpi=150))
                area = printer.pageRect(QPrinter.Unit.DevicePixel)
                ratio = min(area.width()/pix.width(), area.height()/pix.height())
                w, h = pix.width()*ratio, pix.height()*ratio
                painter.drawPixmap(QRectF((area.width()-w)/2, (area.height()-h)/2, w, h), pix, QRectF(pix.rect()))
        finally:
            painter.end()

    def about(self):
        from version import VERSION
        self.result_text('PDF Stüdyo — Özellikler', f'''PDF STÜDYO {VERSION} · Windows masaüstü

Yerel: metin/resim ekleme, alan silme, metin değiştirme, not, vurgulama, şekil,
birleştirme, ayırma, sayfa silme/taşıma/döndürme/kırpma, numara, filigran,
form metin alanı oluşturma/doldurma, görsel imza, AES-256 parola, bilinen parolayla
kilit açma, metin/görsel karşılaştırma, kayıpsız küçültme, yapısal onarım,
JPG/PNG ↔ PDF, temel HTML → PDF, PDF → Word/Excel/PowerPoint/Markdown, yazdırma.

2.4 ile: hassas veri bulup karartma, sertifikalı dijital imza ve imza doğrulama,
serbest çizim/çizgi/ok/daire, yorum paneli, yer imleri, güvenli bağlantılar,
onay kutusu/liste/radyo form alanları ve düzleştirme, sayfa sürükle-bırak ve
çoklu seçim, üstbilgi/altbilgi/Bates, toplu işlem, son açılanlar, otomatik
kurtarma, koyu tema, güncelleme denetimi.

OCR: Tesseract dil verileri gerekir. Çıktı 200 DPI görüntü ve aranabilir metin içerir.
Office → PDF: Etkin Microsoft Word/Excel/PowerPoint masaüstü sürümü gerekir.
PDF/A: Ghostscript + veraPDF kullanılır. Doğrulamadan geçmeyen çıktı kaydedilmez.
Tarama: WIA uyumlu tarayıcı ve sürücü gerekir.
Yapay zekâ isteğe bağlıdır ve varsayılan olarak kapalıdır. Etkinleştirildiğinde
Ollama ve yerel model kullanılır; motor yalnızca AI aracı seçilince başlar.
Belge yalnızca bu bilgisayardaki yerel AI servisine gönderilir.

PDF → Word düzeni yaklaşık olarak aktarılır. Excel yalnızca algılanan tablo/metni
aktarır. PowerPoint sayfa görüntülerinden oluşur. Temel HTML/CSS desteklenir.
Görsel imza, sertifikalı veya nitelikli elektronik imza değildir.
Metin değiştirme mevcut yazı boyutunu ve temel stilini algılar; gerektiğinde
6 puntoya kadar küçülterek alana sığdırır. Özgün font birebir eşleşmeyebilir.
Sığmayan metin taslak olarak pencerede kalır; özgün içerik korunur.
Taranmış yazılar doğrudan metin nesnesi değildir.
OCR çıktısı formları, bağlantıları ve mevcut imzaları etkileşimli olarak korumaz.
PDF üzerinde değişiklik mevcut dijital imzaların geçerliliğini etkileyebilir.
Geri alma geçmişi bellekle sınırlıdır; uygulama kapanınca silinir.

Kısayollar: Ctrl+O aç · Ctrl+N yeni · Ctrl+S kaydet · Ctrl+Shift+S farklı kaydet
Ctrl+Z geri al · Ctrl+Y yinele. Düzenleme aracını seçip sayfada alan çizin.
Parolalı açılan PDF aynı parolayla kaydedilir; kaldırmak için Parolasız kaydet kullanın.
Hassas içeriği kaldırma, alandaki notları, bağlantıları ve form alanlarını da siler.
Belge bilgileri ve ekler için PDF güvenliği > Gizli verileri temizle kullanın.
''')
