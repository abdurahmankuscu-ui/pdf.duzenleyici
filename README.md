# PDF Stüdyo

Türkçe Windows masaüstü PDF düzenleyici — çalışan ilk sürüm (0.1).

## Başlatma

`Baslat.cmd` dosyasına çift tıklayın. Güncel paket `dist/current/PDF Studyo/PDF Studyo.exe` yolundadır.
Taşımak için `PDF Studyo` klasörünü içindeki `_internal` klasörüyle birlikte kopyalayın.
Kaynak koddan çalıştırma: `.venv\Scripts\python.exe app.py`.

## Kullanım

1. **PDF aç** ile dosya seçin veya pencereye sürükleyin.
2. Soldan sayfayı seçin. Üstten aracı seçip sayfa üzerinde sürükleyerek alan çizin.
3. **Metin ekle**, **Metni değiştir**, **İçeriği sil**, **Resim ekle** seçilen alana uygulanır.
4. `Ctrl+Z` geri alır, `Ctrl+Y` yineler. **Farklı kaydet** özgün dosyanızı korur.
5. Görsellerde talep edilen diğer özellikler üstteki kategorili menülerdedir.

Parolalı açılan PDF, kaydet ve farklı kaydet işlemlerinde aynı parolayla (AES-256) yazılır.
Parolayı kaldırmak için **PDF güvenliği > Parolasız kaydet** kullanın; işlem onay ister.
İçerik silme, beyaz kutu çizmenin yanında PDF içeriğine redaksiyon uygular. Seçilen alanla
kesişen notlar, bağlantılar ve form alanları da silinir. Belge bilgileri (yazar, başlık, XMP),
JavaScript ve ekli dosyalar için **PDF güvenliği > Gizli verileri temizle** kullanın; OCR metin katmanı korunur.
Metin değiştirme, mevcut yazının boyutunu ve temel stilini algılar. Düzenleme penceresinde
yazı boyutu değiştirilebilir; alana sığdırma gerekirse en az 6 puntoya kadar küçültür.
Çok uzun metin sığmazsa özgün metin ve girdiğiniz taslak korunur. Değişiklik `Ctrl+Z` ile geri alınabilir.
Seçili metin değiştirilirken resim ve çizimler korunur; özgün fontun birebir eşleşmesi garanti edilmez.

## Özellik durumu

| Özellik | Durum / kapsam |
|---|---|
| Metin, resim, not, vurgu, dikdörtgen | Yerel, çalışıyor |
| İçerik silme ve metin değiştirme | Alan seçerek; geri alınabilir |
| Birleştirme, ayırma, sayfa ayıklama | Yerel; seçilen sayfalar tek yeni PDF olur |
| Sayfa silme, taşıma, döndürme, kırpma | Yerel |
| Küçültme | Kayıpsız veya resimleri 1600 piksel/JPEG %70'e düşüren dengeli mod |
| PDF onarma | Motorun okuyabildiği bozuk yapıları yeniden yazar; tüm bozuk dosyalar kurtarılamaz |
| OCR | Türkçe + İngilizce dil verisi pakete dahil; 200 DPI görüntü ve aranabilir metin çıktısı |
| JPG/PNG → PDF; PDF → JPG/PNG | Yerel |
| Word/Excel/PowerPoint → PDF | Microsoft Office masaüstü otomasyonu; bu bilgisayarda örneklerle test edildi |
| HTML → PDF | Qt'nin desteklediği temel HTML/CSS; JavaScript yok |
| PDF → Word | Düzenlenebilir metin ve resimler; yaklaşık düzen |
| PDF → Excel | Algılanan tablolar; tablo yoksa satır metinleri |
| PDF → PowerPoint | Her sayfa bir slayt görüntüsüdür; içindeki yazılar bağımsız düzenlenemez |
| PDF → Markdown / TXT | Sayfa metinleri |
| Sayfa numarası, filigran | Tüm sayfalara uygulanır |
| PDF formları | Metin alanı oluşturma ve doldurma; tüm form türleri henüz desteklenmez |
| Parola / kilit açma | AES-256; kilit açmak için mevcut parola gerekir |
| İmza | Görsel imza ekleme; sertifikalı e-imza değildir |
| PDF karşılaştırma | Sayfa bazlı metin farkları ve 72 DPI görsel fark tespiti |
| PDF/A | Ghostscript + veraPDF: PDF/A-2b doğrulaması geçerse kaydedilir; XML raporu PDF'nin yanında oluşur |
| Tarayıcıdan PDF | WIA cihaz denetimi; cihaz yoksa fotoğraftan PDF alternatifi. Fiziksel tarayıcıyla test edilmedi |
| AI özet / çeviri | Varsayılan kapalı; menüden etkinleştirilirse yerel model kullanılır |

OCR, etkileşimli form ve bağlantıları görüntüye dönüştürür. Dijital imzalı belgelerin düzenlenmesi
mevcut imza geçerliliğini etkileyebilir. OCR ve dönüşüm işlemleri farklı çıktı dosyasına kaydedilmelidir.
PDF/A çıktılarını uygulama veraPDF ile otomatik doğrular. Doğrulama başarısızsa hedef PDF değiştirilmez.

## İsteğe bağlı bağımlılıklar

- PDF/A: [Ghostscript](https://www.ghostscript.com/releases/) 10.08.0 ve [veraPDF](https://software.verapdf.org/) 1.30.2 bu bilgisayarda kuruldu. Java da gerekir.
- AI isteğe bağlıdır ve varsayılan olarak kapalıdır. `Yapay zekâ > Yerel AI etkin` ile açılır.
  Etkinleştirildiğinde [Ollama](https://ollama.com/) 0.34.2 ve `qwen3:4b-instruct` modeli kullanılır. API `127.0.0.1:11434` üzerinde yalnızca AI aracı seçilince başlar.
  Program belge metnini sadece yerel API'ye gönderir. Uzun belgeler sayfa referanslı, en fazla 6.000 karakterlik parçalarda işlenir.
  Çeviri çıktı düzenini yeniden oluşturmaz; sonuç metni PDF veya TXT olarak kaydedilir.
- Tarama: Windows WIA uyumlu tarayıcı/sürücü.

Entegrasyonlar kullanıcı klasöründe `%LOCALAPPDATA%\PDFStudyo` altında tutulur.
Uygulamanın `dist` klasörünü başka bilgisayara taşımak bu motorları taşımaz.
`Yardım > Entegrasyon durumu` kurulumları, yerel modelleri ve tarayıcıları denetler.
AI kapatıldığında uygulamanın kurduğu Ollama ve model süreçleri durdurulur. AI etkin bırakılırsa,
Ollama kullanılmadığında model 5 dakika sonra bellekten çıkar; servis arka planda kalır.
AI'ın kapalı olması kurulu model dosyalarını silmez. Yeni model otomatik indirilmez.
Otomatik başlatılan serviste bulut özellikleri kapalıdır ve yalnızca localhost dinlenir.
Tarama testi için cihazı USB/ağ üzerinden bağlayın, üreticinin WIA sürücüsünü kurun ve durum denetimini yenileyin.
Telefon fotoğraflarını `PDF'e dönüştür > JPG / PNG → PDF` ile kullanabilirsiniz.

## Geliştirme ve doğrulama

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File build.ps1
```

Office entegrasyon testlerini çalıştırmak için `$env:TEST_OFFICE='1'` ayarlayın.
`--smoke-test ekran.png` parametresi paketlenmiş uygulamayı açar, örnek sayfayı çizip ekran çıktısını kaydeder ve kapatır.
`--verify-integrations klasor` paket içinden PDF/A ve motor keşfini kontrol eder, `result.json` raporunu yazar.
Gerçek PDF/A testleri: `$env:TEST_PDFA='1'`; gerçek AI testleri: `$env:TEST_AI='1'`.
`tools/pull_local_model.py` varsayılan modeli indirir; normal uygulama kullanımı model indirme işlemi başlatmaz.

Tasarım: `engine.py` PDF işlemleri ve atomik kayıt; `app.py` Qt düzenleyici;
`advanced.py` dönüşümler ve dış motorlar; `tool_ui.py` araç menüleri ve arka plan işleri.
PDF'ler kayıt anına kadar bellekte tutulur. Geri alma geçmişi yaklaşık 128 MB ile sınırlıdır
(tek büyük işlem bundan fazla olabilir). Büyük belgeler için sonraki sürümde disk tabanlı geçmiş gerekir.

## Yeni çalışma alanı — sürüm 2.0

Yeni paket `dist/v2.0/PDF Studyo/PDF Studyo.exe` konumundadır. `Baslat.cmd` bu sürümü açar.
Belgenizi kaydedip eski pencereyi kapattıktan sonra başlatın. Pencere başlığında **PDF Stüdyo 2.0** görünür.
Solda düzenleme araçları, sağda sayfa önizlemeleri bulunur. Dönüşüm, güvenlik ve yapay zekâ seçeneklerine üstteki **Tüm araçlar** menüsünden erişilir. **Sayfa işlemleri** sağ altta, **Farklı kaydet** üstteki üç nokta menüsündedir. Yakınlaştırmanın yanındaki çerçeve simgesi belgeyi görünüm genişliğine sığdırır. Açılış ekranında PDF açma, yeni belge, resimden PDF ve tarama kısayolları vardır.

## Metin düzenleme — sürüm 1.2

Bu metin özellikleri 2.0 sürümünde de korunmuştur.

- **Metni değiştir:** Yazıyı çevreleyen alanı seçin. Açılan pencerede metni, boyutu ve otomatik sığdırmayı düzenleyin. Hata olursa taslağınız pencerede kalır.
- **Yazı stili al:** PDF'deki örnek yazıyı seçin; ardından yeni yazı için alan çizin. Font, boyut ve renk örnekten alınır.
- **Metni taşı:** Yazının tamamını çevreleyen alanı seçin; kutunun içinden tutup sürükleyin. Özgün PDF yazısı, fontu ve rengi korunarak taşınır. Ctrl+Z ile geri alınır.

Yeni/değiştirilen yazıda gömülü font kullanılabiliyorsa korunur. Font eksikse veya yeni harfleri içermiyorsa benzer font kullanılır; her PDF için birebir eşleşme garanti edilemez. Birden fazla biçim içeren seçimlerde baskın biçim esas alınır. Otomatik sığdırma gerekirse yazı boyutunu azaltır.

`--verify-text rapor.json` paket içindeki gerçek metin pencereleriyle sentetik belgede ekleme, değiştirme, stil örnekleme ve taşıma denetimi yapar; JSON, PDF ve PNG çıktıları üretir.

## Bağımlılık lisansları

PyMuPDF ve isteğe bağlı Ghostscript AGPL/ticari lisans seçenekleri taşır; dağıtım modeli buna göre seçilmelidir.
Qt/PySide6 LGPL/GPL/ticari lisans seçeneklerine sahiptir. Kaynak kod ve bağımlılık lisansları korunmalıdır.
Türkçe OCR verisi `tesseract-ocr/tessdata_fast` projesinden (Apache-2.0), İngilizce veri yerel Tesseract kurulumundan alınmıştır.
Bu ilk sürüm, ticari PDF paketlerinin bütün özelliklerinin ve belge uyumluluğunun tamamlandığı anlamına gelmez.

## Resim boyutlandırma — 2.1

Resim ekledikten sonra resmin ortasına tıklayın veya soldan **Resmi boyutlandır** aracını seçin. Genişlik, yükseklik ve konumu milimetre olarak ayarlayın. En-boy oranı varsayılan olarak korunur. Uygula ile değişiklik kayda hazır hale gelir; Ctrl+Z ile geri alınır. Mevcut dosyalardaki karmaşık resim grupları desteklenmeyebilir; uygulamayla bağımsız olarak eklenen resimler desteklenir. Yeni paket: `dist/v2.1/PDF Studyo/PDF Studyo.exe`.

## Metin alanı — 2.2

Metni değiştir penceresinde **Yazı alanı — genişlik / yükseklik** ayarları bulunur. Bir satırlık alana iki satır yazarken yüksekliği artırın. Uzun isimler için genişliği artırın. Taslağınız korunur; aynı pencereden yeniden Uygula seçilebilir. Alan yalnızca sağa ve aşağı genişler. Büyütülen alanın altındaki komşu yazılar silinmez; üst üste gelmemesine dikkat ederek düzenleyin. Dar alanlarda HTML kutusu yerine font ölçüleriyle yerleştirme yapılır. Yeni paket `dist/v2.2/PDF Studyo/PDF Studyo.exe`.

## Taşıma kılavuzları — 2.3

**Metni taşı** ile yazıyı seçip kutunun içinden sürüklediğinizde yatay ve dikey kılavuzlar görünür. Sayfa merkezi, kenarları ve diğer metinlerin kenar/merkez hizaları referans alınır. Yakın hizalar turkuaz çizgiyle belirtilir; otomatik yapıştırma yapılmaz. Çizgiler yalnızca ekranda görünür, PDF’ye kaydedilmez. Esc taşıma hareketini iptal eder. Yeni paket: `dist/v2.3/PDF Studyo/PDF Studyo.exe`.

## Sürüm 2.4 — yeni özellikler

Yeni paket: `dist/v2.4/PDF Studyo/PDF Studyo.exe` (`build.ps1` ile oluşturulur). Sürüm numarası tek yerde, `version.py` içinde tutulur.

**Güvenlik** (Tüm araçlar > PDF güvenliği)
- **Hassas verileri bul ve karart:** TCKN ve IBAN (kontrol basamağı doğrulanır), e-posta ve cep telefonu numaraları bulunur. Bulgular listelenir; işaretini kaldırdıklarınız korunur. Taranmış belgelerde önce OCR uygulayın.
- **Dijital imza (sertifikalı):** Sayfada imza alanını çizin, `.pfx/.p12` sertifikanızı ve parolasını girin. PAdES imzası **yeni bir dosyaya** yazılır. Sertifika parolası saklanmaz. Parolalı belgeler parolasıyla birlikte imzalanır.
- **İmzaları doğrula:** Bütünlük, imza kapsamı ve imzalayan bilgisi gösterilir. Sertifika güveni Windows kök sertifikalarıyla, çevrimdışı denetlenir; iptal (CRL/OCSP) denetimi yapılmaz.
- İmzalı bir belgeyi normal kaydetmek imzaları geçersiz kılar; uygulama kaydetmeden önce uyarır.

**Düzenleme**
- Soldaki araçlara **Serbest çizim, Çizgi, Ok, Daire** ve **Bağlantı ekle** eklendi. Bağlantılar yalnızca `https://`, `http://`, `mailto:` veya sayfa numarası olabilir; program çalıştıran veya yerel dosya açan bağlantılar reddedilir.
- **Yorumlar** düğmesi yorum panelini açar: sayfaya git, düzenle, sil.
- **Yer imleri** (Sayfa araçları): başlık, düzey ve sayfa düzenlenir.
- **Form alanları:** metin, onay kutusu, açılır liste, liste, radyo düğmesi; tüm türler doldurulabilir. **Formu düzleştir** alanları sabit içeriğe çevirir.
- **Sayfa listesi:** sürükle-bırak ile sıralama; Ctrl/Shift ile çoklu seçip döndürme, silme ve ayıklama.

**İş akışı**
- **Üstbilgi / altbilgi / Bates** (Sayfa araçları): `{n}`, `{toplam}`, `{bates}`, `{tarih}` alanları; 6 konum; sayfa aralığı. Döndürülmüş sayfalarda da yazı okuyucuya düz görünür.
- **Toplu işlem (klasör):** Birden çok PDF'e küçültme, OCR, filigran veya damga uygulanır. Özgün dosyalar değişmez; sonuçlar ayrı klasöre yazılır, aynı adlı dosyaların üzerine yazılmaz. Parolalı dosyalar atlanır ve raporda belirtilir.
- **Son açılanlar:** `•••` menüsünde.
- **Otomatik kurtarma:** Kaydedilmemiş değişiklikler 2 dakikada bir `%LOCALAPPDATA%\PDFStudyo\recovery` klasörüne yazılır. Beklenmedik kapanıştan sonra açılışta geri yükleme önerilir. Parolalı belgelerin kurtarma kopyası aynı parolayla şifrelenir; parola diske yazılmaz.

**Dağıtım**
- **Görünüm > Tema:** Sistem, Açık, Koyu. Seçim hatırlanır.
- **Yardım > Güncellemeleri denetle:** Yalnızca siz seçtiğinizde, GitHub'daki [proje sürümlerini](https://github.com/abdurahmankuscu-ui/pdf.duzenleyici/releases) denetler. Hiçbir dosyayı kendisi indirmez veya çalıştırmaz; yalnızca bu projenin sürüm sayfasını tarayıcıda açar. Denetimin çalışması için GitHub'da `v2.4` gibi etiketli bir Release yayınlanmalıdır.
- **Kurulum paketi:** `installer.iss` (Inno Setup 6). Inno Setup kuruluysa `build.ps1` betiği `dist/installer/PDF-Studyo-<sürüm>-Kurulum.exe` dosyasını da üretir. Kurulum yönetici izni istemez, kullanıcı klasörüne kurar. İsteğe bağlı olarak PDF'ler için "Birlikte aç" kaydı ekler; varsayılan PDF uygulamanızı değiştirmez.
