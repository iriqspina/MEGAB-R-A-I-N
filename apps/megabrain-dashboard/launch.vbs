Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
appFolder = files.GetParentFolderName(WScript.ScriptFullName)
executable = files.BuildPath(appFolder, "bootstrap\MegaBrain.exe")
If files.FileExists(executable) Then
    shell.Run Chr(34) & executable & Chr(34), 1, False
Else
    MsgBox "O lancador do MegaBrain nao foi encontrado. Execute scripts\launcher-build.ps1 na pasta do aplicativo.", 16, "MegaBrain"
End If
