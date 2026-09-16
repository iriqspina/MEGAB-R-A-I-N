# abrir-area-ia.ps1 — Área de trabalho paralela do agente ("I.A.", 260916)
# Design: Marketeiro/pesquisa/260916_design-ambiente-paralelo-agente.md (conta nova, high)
# O que faz: sobe o CHROME DEDICADO DO AGENTE com perfil isolado e ponte CDP
# própria (porta 9223), abrindo MINIMIZADO pra não roubar o foco do dono.
# NUNCA usa a instância/perfil pessoal do dono. Idempotente: se já está no ar,
# reutiliza. Estado em %LOCALAPPDATA%\ZCode\IA\state.json (sem segredos).
# Desktop virtual "I.A.": criado UMA VEZ pelo dono (Win+Ctrl+D) — o script só
# lembra no estado; nunca alterna o desktop do dono automaticamente.
param([switch]$Parar)

$ErrorActionPreference = 'Stop'
$raiz = Join-Path $env:LOCALAPPDATA 'ZCode\IA'
$perfil = Join-Path $raiz 'Chrome'
$state = Join-Path $raiz 'state.json'
$porta = 9223
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'

if ($Parar) {
  Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
    Where-Object { $_.CommandLine -like "*$perfil*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Write-Output 'Area I.A. parada.'
  exit 0
}

if (-not (Test-Path $chrome)) { $chrome = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe' }
if (-not (Test-Path $chrome)) { Write-Output 'Chrome nao encontrado.'; exit 1 }
New-Item -ItemType Directory -Force -Path $perfil | Out-Null

$no_ar = $false
try {
  $r = Invoke-RestMethod "http://127.0.0.1:$porta/json/version" -TimeoutSec 2
  $no_ar = $true
} catch {}

if (-not $no_ar) {
  Start-Process $chrome -ArgumentList(
    "--user-data-dir=`"$perfil`"",
    "--remote-debugging-port=$porta",
    '--no-first-run', '--no-default-browser-check',
    '--start-minimized',                       # nao rouba o foco do dono
    '--window-name=ZCode-IA'                   # identifica a janela do agente
  )
  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try { $r = Invoke-RestMethod "http://127.0.0.1:$porta/json/version" -TimeoutSec 2; $no_ar = $true; break } catch {}
  }
}

[pscustomobject]@{
  browser_perfil   = $perfil
  cdp              = "http://127.0.0.1:$porta"
  no_ar            = $no_ar
  desktop_virtual  = 'I.A. (criar uma vez com Win+Ctrl+D e mover a janela pra la)'
  regras           = @('nunca usar o Chrome/perfil do dono',
                       'input so via CDP/UIA direcionado; nada de SendInput global',
                       'login Google: dono digita UMA vez nesta janela, com agente pausado')
} | ConvertTo-Json | Set-Content $state -Encoding UTF8

Write-Output "Area I.A. no ar: $no_ar (CDP http://127.0.0.1:$porta) - estado em $state"
