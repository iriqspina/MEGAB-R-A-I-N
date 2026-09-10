param([string]$InstallDir = (Split-Path -Parent $PSScriptRoot), [string]$DesktopDir = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
$target = Join-Path $InstallDir 'launch.vbs'; $icon = Join-Path $InstallDir 'assets\megabrain-cerebro-rosa.ico'
if (!(Test-Path $target) -or !(Test-Path $icon)) { throw 'Launcher ou icone ausente.' }
$link = Join-Path $DesktopDir 'MEGABRAIN - Visao pessoal.lnk'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath=$target; $shortcut.WorkingDirectory=$InstallDir; $shortcut.IconLocation="$icon,0"; $shortcut.Description='MEGABRAIN: visao pessoal de projetos, novidades e proximos passos'; $shortcut.Save(); [Runtime.InteropServices.Marshal]::ReleaseComObject($shell)|Out-Null
Write-Output $link
