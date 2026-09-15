' Lança o widget "Agentes IA" com pythonw (sem console).
' Usa o venv do Cotas IA (PySide6 6.11.2 + QtWebEngine já instalados).
Dim fso, shell, dir, aqui, pythonw
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
aqui = fso.GetParentFolderName(dir) ' raiz de apps/
pythonw = aqui & "\ia-quota-widget\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonw) Then
  MsgBox "pythonw não encontrado em " & pythonw & ". Instale o venv do Cotas IA primeiro.", 16, "Agentes IA"
Else
  shell.Run """" & pythonw & """ """ & dir & "\agentes_ia_widget.py""", 0, False
End If
