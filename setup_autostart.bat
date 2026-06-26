@echo off
echo.
echo  Registrando inicio automatico con Windows...
echo  (Se necesita ejecutar como Administrador)
echo.

set "VBS=%~dp0start_oculto.vbs"
set "TAREA=Medina SST Panel Comercial"

schtasks /create /tn "%TAREA%" /tr "wscript.exe \"%VBS%\"" /sc onlogon /rl highest /f

if %errorlevel% == 0 (
    echo.
    echo  Listo. El software iniciara automaticamente
    echo  cada vez que enciendas o reinicies el computador.
    echo.
    echo  Para desactivar el inicio automatico ejecuta:
    echo  setup_desactivar_autostart.bat
) else (
    echo.
    echo  Error. Haz clic derecho en este archivo y
    echo  selecciona "Ejecutar como administrador".
)
echo.
pause
