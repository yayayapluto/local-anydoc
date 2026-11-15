@echo off
cd /d %~dp0
docker compose up -d
echo OCR: http://127.0.0.1:8001/health
