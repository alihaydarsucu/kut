# Kurulum ve yapılandırma

## Gereksinimler

- GRUB 2 ve dağıtımınızın GRUB yapılandırma aracı (<code>update-grub</code> veya
  <code>grub-mkconfig</code>)
- Kurulum için yönetici yetkisi
- EFI sistemlerde GRUB'un grafik modunda çalışabilmesi

## Kurulum

~~~bash
sudo ./install.sh
~~~

Kurucu aşağıdakileri yapar:

1. <code>/etc/default/grub</code>, mevcut Kut tema dizini ve Kut GRUB kancaları için
   <code>/var/backups/kut-grub/&lt;tarih-saat&gt;</code> altında yedek oluşturur.
2. Temayı <code>/boot/grub/themes/kut</code> altına yükler.
3. Tema etiketlerindeki dağıtım, çekirdek, RAM, ürün yazılımı, makine adı ve
   işlemci verilerini üretir.
4. <code>GRUB_THEME</code>, <code>GRUB_GFXMODE</code> ve gerekli Kut ayarlarını günceller.
5. <code>update-grub</code> ya da uygun olduğunda <code>grub-mkconfig</code> ile
   <code>grub.cfg</code> dosyasını yeniden oluşturur.

## Ayarlar

<code>/etc/default/grub</code> içinde aşağıdaki Kut ayarlarını değiştirebilirsiniz:

| Ayar | Varsayılan | Açıklama |
| --- | --- | --- |
| <code>KUT_TELEMETRY</code> | <code>1</code> | Açılış öncesi telemetri ekranını açar veya kapatır. |
| <code>KUT_TELEMETRY_DELAY</code> | <code>3</code> | Telemetri ekranının saniye cinsinden süresi; <code>1</code>–<code>10</code> aralığındadır. |

Değişikliklerden sonra yapılandırmayı yenileyin:

~~~bash
sudo update-grub
~~~

## Chroot veya kurulum ortamında test

<code>update-grub</code> çağrısını atlamak için:

~~~bash
sudo KUT_SKIP_UPDATE=1 ./install.sh
~~~

Bu seçenek dosyaları yerleştirir ve etiketleri üretir; GRUB yapılandırmasını
yenilemez. Hedef sistem açılmadan önce normal ortamda <code>sudo update-grub</code>
çalıştırılmalıdır.

## Kaldırma

~~~bash
sudo ./uninstall.sh
~~~

Kaldırıcı yalnızca Kut'a ait <code>GRUB_THEME</code>, telemetri ayarları, tema dizini ve
GRUB kancalarını temizler. Önce <code>/var/backups/kut-grub/&lt;tarih-saat&gt;</code> altında
bir yedek oluşturur; <code>GRUB_GFXMODE</code> ve <code>GRUB_TIMEOUT_STYLE</code>
ayarlarını korur.
