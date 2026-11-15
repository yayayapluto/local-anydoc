@echo off
cd /d %~dp0web
echo Web: http://127.0.0.1:8080
py -3 serve.py
