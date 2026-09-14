Dim fso, shell, dir
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run """" & dir & "\.venv\Scripts\pythonw.exe"" """ & dir & "\widget.py""", 0, False
