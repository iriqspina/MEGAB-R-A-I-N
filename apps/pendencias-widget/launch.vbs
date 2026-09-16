' Lança o widget "Pendências" com pythonw (sem console).
' Prioriza o venv do Cotas IA (PySide6 já instalado); fallback: venv próprio.
Dim fso, shell, dir, aqui, pythonw
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
aqui = fso.GetParentFolderName(dir) ' raiz de apps/
pythonw = aqui & "\ia-quota-widget\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonw) Then pythonw = dir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonw) Then
  MsgBox "pythonw nao encontrado. Rode INSTALAR-E-ABRIR.cmd primeiro.", 16, "Pendencias"
Else
  shell.Run """" & pythonw & """ """ & dir & "\widget.py""", 0, False
End If
