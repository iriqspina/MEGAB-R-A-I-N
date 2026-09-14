<#
Roda UMA VEZ, na pasta de destino onde o app efetivamente vai morar (nao
no worktree do Traycer, que e' descartavel). Cria o .venv do zero, instala
PySide6 travado em 6.11.2, roda a suite de teste e falha alto se nao
passar, e cria o atalho "Cotas IA" na Area de Trabalho de verdade.

Por que recriar o .venv em vez de copiar: o venv do Windows grava caminho
absoluto em pyvenv.cfg e nos .exe de Scripts\ (python.exe, pip.exe);
movido de pasta ele quebra o pip e os console scripts. Recriar custa
~1 minuto e nao deixa essa armadilha. O .venv fica de fora do git de
qualquer forma (.gitignore).
#>
param(
    [string]$InstallDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Set-Location $InstallDir

Write-Output "== Instalando em: $InstallDir =="

if (Test-Path (Join-Path $InstallDir '.venv')) {
    Write-Output "-- .venv ja existe, removendo pra recriar limpo --"
    Remove-Item (Join-Path $InstallDir '.venv') -Recurse -Force
}

Write-Output "-- Criando .venv --"
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "python -m venv falhou (codigo $LASTEXITCODE)" }

$py = Join-Path $InstallDir '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "venv nao criou $py" }

Write-Output "-- Instalando dependencias (PySide6==6.11.2, pytest) --"
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet "PySide6==6.11.2" pytest
if ($LASTEXITCODE -ne 0) { throw "pip install falhou (codigo $LASTEXITCODE)" }

Write-Output "-- Rodando suite de testes --"
& $py -m pytest tests/ -q
if ($LASTEXITCODE -ne 0) {
    throw "Suite de testes falhou (codigo $LASTEXITCODE) -- instalacao interrompida, nada de atalho com app quebrado"
}

Write-Output "-- Gerando icone (se ainda nao existir) --"
if (-not (Test-Path (Join-Path $InstallDir 'assets\cotas-ia.ico'))) {
    & $py scripts\generate_icon.py
    if ($LASTEXITCODE -ne 0) { throw "geracao do icone falhou (codigo $LASTEXITCODE)" }
}

Write-Output "-- Criando atalho na Area de Trabalho --"
& (Join-Path $InstallDir 'scripts\criar-atalho.ps1') -InstallDir $InstallDir

Write-Output "== Instalacao concluida em $InstallDir =="
