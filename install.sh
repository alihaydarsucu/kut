#!/bin/bash
set -e

THEME_DIR="/boot/grub/themes/technight"

echo "[1/5] Tema dizini oluşturuluyor..."
sudo mkdir -p "$THEME_DIR"

echo "[2/5] Tema dosyaları kopyalanıyor..."
sudo cp technight/* "$THEME_DIR/"

echo "[3/5] /etc/default/grub güncelleniyor..."
sudo sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' /etc/default/grub
sudo sed -i 's/^GRUB_DEFAULT=.*/GRUB_DEFAULT=0/' /etc/default/grub

# Advanced options ve Ubuntu advanced'i gizle
if ! grep -q "GRUB_DISABLE_SUBMENU" /etc/default/grub; then
    echo 'GRUB_DISABLE_SUBMENU=y' | sudo tee -a /etc/default/grub
fi

# Tema
if grep -q "^GRUB_THEME=" /etc/default/grub; then
    sudo sed -i "s|^GRUB_THEME=.*|GRUB_THEME=\"$THEME_DIR/theme.txt\"|" /etc/default/grub
else
    echo "GRUB_THEME=\"$THEME_DIR/theme.txt\"" | sudo tee -a /etc/default/grub
fi

sudo sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"/' /etc/default/grub

echo "[4/5] GRUB_DISABLE_OS_PROBER kontrol ediliyor..."
if ! grep -q "GRUB_DISABLE_OS_PROBER" /etc/default/grub; then
    echo 'GRUB_DISABLE_OS_PROBER=false' | sudo tee -a /etc/default/grub
fi

echo "[5/5] GRUB yenileniyor..."
sudo update-grub

echo ""
echo "✓ Kurulum tamamlandı! Bir sonraki açılışta aktif olacak."
