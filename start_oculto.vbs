' start_oculto.vbs — inicia el software sin mostrar ventana de terminal
' Windows Task Scheduler usa este archivo para arranque automatico
Dim WShell, ruta
Set WShell = CreateObject("WScript.Shell")
ruta = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WShell.Run "cmd /c """ & ruta & "\start.bat""", 0, False
Set WShell = Nothing
