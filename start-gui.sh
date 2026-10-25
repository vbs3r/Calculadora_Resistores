#!/usr/bin/env bash
set -e

echo "Instalando dependencias..."
sudo apt-get update -y
sudo apt-get install -y xvfb x11vnc fluxbox websockify novnc

echo "Iniciando pantalla virtual..."
Xvfb :1 -screen 0 1280x800x24 &
export DISPLAY=:1
fluxbox &

echo "Iniciando servidor VNC..."
x11vnc -display :1 -nopw -forever -shared -rfbport 5900 &

echo "Iniciando noVNC en el puerto 6080..."
websockify --web=/usr/share/novnc 6080 localhost:5900 &

echo ""
echo "✅ Entorno listo. Ve a la pestaña 'Ports', haz público el puerto 6080 y abre el enlace."
