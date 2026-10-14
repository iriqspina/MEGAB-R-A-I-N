$ErrorActionPreference = 'Stop'
$launcherApp = Split-Path -Parent $PSScriptRoot
$launcherExecutable = Join-Path $launcherApp 'bootstrap/MegaBrain.exe'
$launcherRoot = Split-Path -Parent (Split-Path -Parent $launcherApp)
$launcherShortcut = Join-Path $launcherRoot '00_PARA-VOCE/MegaBrain Central.lnk'
if (Test-Path -LiteralPath $launcherShortcut) { throw 'O atalho já existe e foi preservado. Use MegaBrain.exe --verify para conferir.' }
$launcherResult = Start-Process -FilePath $launcherExecutable -ArgumentList '--create-shortcut' -WindowStyle Hidden -Wait -PassThru
if ($launcherResult.ExitCode -ne 0) { throw 'Não foi possível criar o atalho. Consulte bootstrap/launcher.log.' }
$launcherResult = Start-Process -FilePath $launcherExecutable -ArgumentList '--verify' -WindowStyle Hidden -Wait -PassThru
if ($launcherResult.ExitCode -ne 0) { throw 'Não foi possível verificar o atalho. Consulte bootstrap/launcher.log.' }
Get-Item -LiteralPath $launcherShortcut | Select-Object FullName, Length
