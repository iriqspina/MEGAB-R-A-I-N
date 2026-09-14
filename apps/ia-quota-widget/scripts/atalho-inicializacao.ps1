<#
Cria (ou atualiza) o atalho do Cotas IA na pasta de inicializacao do
Windows, pra abrir junto com o sistema. Idempotente: nunca duplica.

Para tirar depois: Win+R -> shell:startup -> apague "Cotas IA.lnk".
#>
param(
    [string]$InstallDir = (Split-Path -Parent $PSScriptRoot),
    [string]$ShortcutName = "Cotas IA"
)

$ErrorActionPreference = 'Stop'

$startupDir = [Environment]::GetFolderPath('Startup')
$target = Join-Path $InstallDir 'launch.vbs'
$icon = Join-Path $InstallDir 'assets\cotas-ia.ico'

if (-not (Test-Path $target)) {
    throw "launch.vbs nao encontrado em $target"
}

$shortcutPath = Join-Path $StartupDir "$ShortcutName.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $InstallDir
if (Test-Path $icon) { $shortcut.IconLocation = "$icon,0" }
$shortcut.Description = "Cotas IA - abre junto com o Windows"
$shortcut.Save()
[Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null

Write-Output "Inicializacao: $shortcutPath"
