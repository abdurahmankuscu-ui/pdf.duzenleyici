# AI, PDF/A ve tarama — doğrulama sonucu

18 Eylül 2026 tarihinde bu bilgisayarda yapılan kurulum ve testler:

## AI: test edildi, varsayılan kapalı

- Ollama 0.34.2 ve Qwen3 4B Instruct yerel olarak kuruldu.
- NVIDIA RTX 2050, Vulkan üzerinden algılandı ve örnek özet/çeviri üretildi.
- İngilizce örnek PDF'deki `12 October 2026`, `8`, `24` ve `Deniz` bilgileri Türkçe çıktıda korundu.
- Model gerçek metinle sınandı; yine de AI çıktıları kullanıcı tarafından kontrol edilmelidir.
- İsteğe bağlı kullanım: **Yapay zekâ → Yerel AI etkin** seçeneğini açın, ardından özet veya çeviriyi seçin.
- AI kapalıyken motor çalıştırılmaz. AI menüden kapatıldığında uygulamanın motor ve model süreçleri durdurulur.
- AI etkinse araç seçildiğinde motor başlatılır. İlk kurulumdan sonra bu araç internet gerektirmez.
- Belgeler yalnızca `127.0.0.1:11434` yerel servisine gönderilir. Uygulamanın başlattığı serviste bulut özellikleri kapalıdır.

Örnek çeviri:

> Proje Atlas, 12 Ekim 2026 tarihinde başlar. Ekip, 8 kişi içerir.
> İlk teslimat, 24 PDF rapor içerir. Proje yöneticisi Deniz'dir.

## PDF/A: hazır

- Ghostscript 10.08.0 ve veraPDF 1.30.2 kuruldu.
- Türkçe PDF/A-2b örneği: **144 kural / 498 kontrol başarılı, 0 hata**.
- Standart bir PDF'nin PDF/A olarak reddedildiği ve başarısız doğrulamanın mevcut hedef dosyayı değiştirmediği test edildi.
- Kullanım: PDF açın → **PDF'ten dönüştür → PDF → PDF/A**.
- Her çıktı otomatik doğrulanır; yanında `.validation.xml` raporu kaydedilir.
- `.exe` paketinden de PDF/A üretimi ve doğrulaması başarıyla tekrarlandı.

## Tarama: cihaz bekleniyor

- Windows WIA denetiminde bağlı tarayıcı sayısı: **0**.
- Fiziksel cihazla görüntü alma henüz test edilmedi.
- WIA uyumlu tarayıcı/yazıcıyı bağlayın ve üreticinin sürücüsünü kurun.
- **Yardım → Entegrasyon durumu** ekranında cihaz göründükten sonra **PDF düzenle → PDF'e tara** aracını kullanın.
- Cihaz yoksa **PDF'e dönüştür → JPG / PNG → PDF** ile telefon fotoğraflarından PDF oluşturun.

## Kurulum konumu

Motorlar ve model `%LOCALAPPDATA%\PDFStudyo` altında tutulur. Windows sistem dizinlerine veya sistem PATH ayarına ekleme yapılmadı.
Program başka bilgisayara taşınırsa bu bileşenlerin o bilgisayarda da kurulması gerekir.

Testler: ilk tur 17 başarılı test; ardından gerçek AI özet/çeviri ve başarısız doğrulamada dosya koruma testleri de geçti.
Paketlenmiş uygulamanın entegrasyon doğrulaması çıkış kodu **0** ile tamamlandı.
