<#
Cria (ou atualiza, se ja existir) o atalho "Cotas IA" apontando pro
launch.vbs de uma pasta de instalacao. Idempotente: rodar de novo so
reescreve o mesmo .lnk, nunca duplica.

Nao mexe em Startup, registro nem %APPDATA%. So cria um arquivo .lnk no
destino indicado.

Parametros pensados pra funcionar tanto na pasta atual (worktree, uso de
teste) quanto na pasta de instalacao definitiva depois da integracao —
por isso -InstallDir e -DesktopDir sao parametros, nao caminho fixo.
#>
param(
    [string]$InstallDir = (Split-Path -Parent $PSScriptRoot),
    [string]$DesktopDir = [Environment]::GetFolderPath('Desktop'),
    [string]$ShortcutName = "Cotas IA"
)

$ErrorActionPreference = 'Stop'

$target = Join-Path $InstallDir 'launch.vbs'
$icon = Join-Path $InstallDir 'assets\cotas-ia.ico'

if (-not (Test-Path $target)) {
    throw "launch.vbs nao encontrado em $target -- InstallDir esta certo?"
}
if (-not (Test-Path $icon)) {
    throw "icone nao encontrado em $icon -- rode scripts\generate_icon.py primeiro"
}
if (-not (Test-Path $DesktopDir)) {
    New-Item -ItemType Directory -Path $DesktopDir -Force | Out-Null
}

$shortcutPath = Join-Path $DesktopDir "$ShortcutName.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $InstallDir
$shortcut.IconLocation = "$icon,0"
$shortcut.Description = "Cotas IA - widget de uso de Codex, Claude e Gemini"
$shortcut.Save()
[Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null

Write-Output "Atalho criado/atualizado: $shortcutPath"
Write-Output "Alvo (TargetPath): $target"
Write-Output "Icone (IconLocation): $icon"
Write-Output "WorkingDirectory: $InstallDir"
