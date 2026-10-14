param([string]$Python = '', [switch]$NoLaunch, [switch]$SkipDependencies)
$ErrorActionPreference = 'Stop'
$installRoot = Split-Path -Parent $PSScriptRoot
$installApp = Join-Path $installRoot 'apps/megabrain-dashboard'
$installVenv = Join-Path $installRoot 'apps/ia-quota-widget/.venv'
$installInterpreter = Join-Path $installVenv 'Scripts/python.exe'
$installLauncher = Join-Path $installApp 'bootstrap/MegaBrain.exe'
if (-not (Test-Path -LiteralPath (Join-Path $installApp 'central_desktop.py'))) { throw 'Extraia o ZIP completo antes de instalar.' }
if (-not (Test-Path -LiteralPath (Join-Path $installApp 'web/dist/index.html'))) { throw 'A distribuicao esta sem o frontend compilado.' }
if (-not (Test-Path -LiteralPath $installInterpreter)) {
    $installArgs = @()
    if ($Python) { $installBootstrap = $Python }
    else {
        $installCommand = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($installCommand) { $installBootstrap = $installCommand.Source; $installArgs = @('-3') }
        else {
            $installCommand = Get-Command python.exe -ErrorAction SilentlyContinue
            if (-not $installCommand) { throw 'Instale Python 3.11 a 3.14 de https://www.python.org/downloads/windows/ e execute novamente.' }
            $installBootstrap = $installCommand.Source
        }
    }
    & $installBootstrap @installArgs -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,14), "Use Python 3.11 a 3.14"'
    if ($LASTEXITCODE -ne 0) { throw 'Versao do Python incompatível.' }
    & $installBootstrap @installArgs -m venv $installVenv
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o ambiente Python local.' }
}
if (-not $SkipDependencies) {
    & $installInterpreter -m pip install -r (Join-Path $installApp 'central-requirements.txt') -r (Join-Path $installRoot 'apps/ia-quota-widget/requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Falha nas dependencias. Verifique a conexao e rode novamente.' }
}
& $installInterpreter -c 'import fastapi, uvicorn, qrcode, PIL; from PySide6.QtWebEngineWidgets import QWebEngineView'
if ($LASTEXITCODE -ne 0) { throw 'Dependencias da central indisponiveis.' }
& (Join-Path $installApp 'scripts/launcher-build.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o lancador.' }
$installShortcut = Join-Path $installRoot '00_PARA-VOCE/MegaBrain Central.lnk'
if (-not (Test-Path -LiteralPath $installShortcut)) {
    $installShortcutProcess = Start-Process -FilePath $installLauncher -ArgumentList '--create-shortcut' -WindowStyle Hidden -Wait -PassThru
    if ($installShortcutProcess.ExitCode -ne 0) { throw 'Nao foi possivel criar o atalho.' }
}
$installVerify = Start-Process -FilePath $installLauncher -ArgumentList '--verify' -WindowStyle Hidden -Wait -PassThru
if ($installVerify.ExitCode -ne 0) { throw 'A verificacao do lancador falhou; veja bootstrap/launcher.log.' }
Write-Host 'MegaBrain instalado. Atalho em 00_PARA-VOCE/MegaBrain Central.lnk.'
if (-not $NoLaunch) {
    $installReport = Join-Path $installRoot '00_PARA-VOCE/261014_compartilhar-megabrain/261014_COMECE-AQUI.html'
    & $installInterpreter (Join-Path $installRoot 'bin/mb-abrir-entrega.py') $installReport
    if ($LASTEXITCODE -ne 0) { throw 'Instalado; a abertura do relatorio falhou.' }
}
