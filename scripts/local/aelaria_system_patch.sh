#!/bin/bash

echo "[AELARIA] Initiating System Patch..."

# 1. Фикс отвала Bluetooth (принудительное автопросыпание модуля)
echo "[1/4] Patching Bluetooth AutoEnable..."
sudo sed -i 's/.*AutoEnable.*/AutoEnable=true/' /etc/bluetooth/main.conf
sudo systemctl restart bluetooth

# 2. Установка OpenRazer и Input Remapper (для биндов Копировать/Вставить)
echo "[2/4] Installing input-remapper and OpenRazer modules..."
sudo add-apt-repository ppa:openrazer/stable -y
sudo apt update
sudo apt install openrazer-meta polychromatic input-remapper -y
# Добавление пользователя в группу для доступа к железу без рута
sudo gpasswd -a $USER plugdev

# 3. Фикс аварийного закрытия Chrome (Graceful Shutdown Hook)
echo "[3/4] Creating graceful shutdown hook for Chrome..."
mkdir -p ~/.config/systemd/user/
cat << 'EOF' > ~/.config/systemd/user/chrome-graceful-shutdown.service
[Unit]
Description=Graceful shutdown of Chrome to prevent restore tabs error
DefaultDependencies=no
Before=shutdown.target halt.target reboot.target

[Service]
Type=oneshot
# Отправляем мягкий сигнал SIGTERM (15) вместо жесткого SIGKILL
ExecStart=/usr/bin/pkill -15 -f "chrome"
TimeoutStartSec=5

[Install]
WantedBy=halt.target reboot.target shutdown.target
EOF

systemctl --user daemon-reload
systemctl --user enable chrome-graceful-shutdown.service
systemctl --user start input-remapper.service

echo "[AELARIA] Patch complete. Please trigger a final system reboot to apply kernel group changes (plugdev)."
