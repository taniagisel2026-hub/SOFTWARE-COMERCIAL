@echo off
title Medina SST — Panel Comercial
cd /d "%~dp0"

REM Evita que el proceso se caiga al imprimir emojis/acentos en la consola
set PYTHONUTF8=1

echo.
echo  ============================================
echo   Medina SST Empresarial SAS
echo   Panel Comercial v1.0.0
echo  ============================================
echo.
echo  Iniciando scheduler automatico (correos)...
start "Medina SST Scheduler" /min python src\scheduler\auto_scheduler.py

echo  Iniciando panel web...
echo  El navegador se abrira automaticamente en:
echo  http://localhost:8501
echo.
echo  IMPORTANTE: No cierre esta ventana.
echo  Para cerrar el software cierre esta ventana.
echo.

:loop
streamlit run app.py --server.port 8501
echo.
echo  El panel se cerro inesperadamente.
echo  Reiniciando en 5 segundos... (Ctrl+C para cancelar)
timeout /t 5 /nobreak > nul
goto loop
