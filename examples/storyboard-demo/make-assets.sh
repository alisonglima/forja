#!/usr/bin/env sh
# Gera assets sinteticos (sem direitos autorais) para o exemplo. Rode de dentro da pasta do projeto: sh make-assets.sh
set -e
mkdir -p assets
ffmpeg -y -loglevel error -f lavfi -i "testsrc2=size=1280x720:rate=30:duration=6" -pix_fmt yuv420p assets/clip.mp4
ffmpeg -y -loglevel error -f lavfi -i "color=c=0x1d4ed8:s=900x300:d=1" -frames:v 1 assets/card.png
ffmpeg -y -loglevel error -f lavfi -i "sine=frequency=220:duration=12" -ar 48000 -ac 2 assets/trilha.wav
echo "assets gerados em $(pwd)/assets"
