@echo off
echo.
echo  Desactivando inicio automatico con Windows...
echo.

schtasks /delete /tn "Medina SST Panel Comercial" /f

if %errorlevel% == 0 (
    echo  Listo. El software ya no iniciara automaticamente.
) else (
    echo  No se encontro la tarea registrada.
)
echo.
pause
