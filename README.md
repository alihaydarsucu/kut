<p align="center">
  <img src="docs/assets/kut-logo.svg" width="480" alt="Kut — GRUB theme · info + OS">
</p>

<p align="center">
  Türkçe odaklı, gerçek makine bilgilerini önyükleme menüsünde gösteren GRUB teması.
</p>

Kut; seçili önyükleme hedefini, dağıtım simgelerini ve sistem bilgilerini tek
bir arayüzde birleştirir. Adı, eski Türkçedeki “kut” kavramından gelir.

## Öne çıkanlar

- 1080p için tasarlanmış, GRUB'un desteklediği alternatif çözünürlüklere de
  uyum sağlayan menü yerleşimi
- Dağıtım, çekirdek, RAM, ürün yazılımı, makine adı ve işlemci bilgisini
  kurulumda ve her <code>update-grub</code> çalışmasında yenileyen tema şablonu
- SMBIOS verilerini gösteren isteğe bağlı açılış öncesi telemetri ekranı
- Linux, Pardus, Windows, macOS ve diğer yaygın önyükleme girdileri için
  simge eşleştirmeleri
- Mevcut GRUB yapılandırması ve tema dosyaları için tarih damgalı yedek alan
  güvenli kurucu ve kaldırıcı

## Kurulum

Önce depoyu klonlayın, ardından kurucuyu yönetici yetkisiyle çalıştırın:

~~~bash
git clone <repository-url> kut
cd kut
sudo ./install.sh
~~~

Kurucu, mevcut yapılandırmayı
<code>/var/backups/kut-grub/&lt;tarih-saat&gt;</code> altında yedekler ve ardından GRUB
yapılandırmasını yeniler. Ayrıntılar için [kurulum rehberine](docs/installation.md)
bakın.

## Kaldırma

~~~bash
sudo ./uninstall.sh
~~~

Bu komut yalnızca Kut'a ait tema, kanca ve ayarları kaldırır; kaldırma öncesi
ayrı bir yedek oluşturur.

## Dokümantasyon

- [Kurulum ve yapılandırma](docs/installation.md)
- [Marka varlıkları](docs/brand.md)
- [Dokümantasyon dizini](docs/README.md)

## Önizleme

![Kut tema arka planı](kut/background.png)
