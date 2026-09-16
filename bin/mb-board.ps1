# mb-board.ps1 - motor do quadro vivo de agentes (Agent Flow)
# Uso: powershell -File mb-board.ps1            -> abre (server + janela proprio) e
#                                                  para o server quando a janela fechar
#       powershell -File mb-board.ps1 -Parar    -> apenas para o server
param([switch]$Parar, [switch]$SomenteDedup)
$ErrorActionPreference = 'SilentlyContinue'
$root = 'S:\projetos multi i.a'
$port = 3001
$dist = "$env:LOCALAPPDATA\npm-cache\_npx\23b47ad77b53d45f\node_modules\agent-flow-app\dist\app.js"

function Test-Server {
  $c = New-Object Net.Sockets.TcpClient
  try { $c.Connect('127.0.0.1', $port); return $c.Connected } catch { return $false } finally { $c.Close() }
}
function Stop-Board {
  $conns = netstat -ano | Select-String ":$port\s+.*LISTENING"
  foreach ($c in $conns) {
    $procId = ($c -split '\s+')[-1]
    # só mata se o dono da porta for node (evita atingir outro serviço na 3001)
    if ($procId -match '^\d+$') {
      $nome = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
      if ($nome -eq 'node') { taskkill /PID $procId /F | Out-Null }
      else { Write-Host "porta $port ocupada por '$nome' (não-node): não matou" }
    }
  }
}
# o app duplica os hooks a cada relancamento (bug do filtro barra normal x contrabarra)
# e o dedup antigo tinha bug de escopo ($mudou local vs $script:mudou — nunca gravava).
# Dedup novo: normaliza barra/caixa/espacos e mantem 1 comando agent-flow por evento,
# com backup do arquivo antes de gravar. Cobre claude (settings.json) e zcode (config.json).
function Repair-Hooks {
  $alvos = @(
    "$env:USERPROFILE\.claude\settings.json",
    "$env:USERPROFILE\.zcode\cli\config.json"
  )
  foreach ($p in $alvos) {
    if (-not (Test-Path $p)) { continue }
    $json = Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json
    $mudou = $false
    foreach ($raiz in @('hooks')) {
      if (-not $json.PSObject.Properties[$raiz]) { continue }
      $eventos = $json.$raiz.events
      if (-not $eventos) { $eventos = $json.$raiz }
      foreach ($ev in $eventos.PSObject.Properties.Name) {
        $blocos = $eventos.$ev
        $vistos = @{}
        foreach ($b in $blocos) {
          $keep = @()
          foreach ($hk in $b.hooks) {
            if ($hk.command -match 'agent-flow') {
              $chave = ($hk.command -replace '\\', '/').ToLower() -replace '\s+', ''
              if ($vistos.ContainsKey($chave)) { $mudou = $true; continue }
              $vistos[$chave] = $true
            }
            $keep += $hk
          }
          $b.hooks = $keep
        }
      }
    }
    if ($mudou) {
      Copy-Item -Force $p "$p.bak-board"
      $json | ConvertTo-Json -Depth 30 | Set-Content $p -Encoding UTF8
      Write-Host "dedup aplicado em $p"
    }
  }
}
# poda da descoberta (decisao 5): remove <hash>-<porta>.json SOMENTE se o conteudo
# tem port+pid+workspace E a porta testada esta morta. hook.js/settings/lixo ficam.
function Prune-Discovery {
  $dir = "$env:USERPROFILE\.claude\agent-flow"
  if (-not (Test-Path $dir)) { return }
  Get-ChildItem $dir -Filter '*.json' | Where-Object { $_.Name -ne 'workspaces.json' } | ForEach-Object {
    try { $d = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return }
    if ($null -eq $d.port -or $null -eq $d.pid -or -not $d.workspace) { return }
    if ($_.Name -notmatch '^[0-9a-f]+-\d+\.json$') { return }
    $c = New-Object Net.Sockets.TcpClient
    try { $viva = $c.Connect('127.0.0.1', [int]$d.port); $viva = $true } catch { $viva = $false } finally { $c.Close() }
    if (-not $viva) { Remove-Item $_.FullName -Force; Write-Host "poda: $($_.Name) (porta $($d.port) morta)" }
  }
}

if ($Parar) { Stop-Board; exit }
if ($SomenteDedup) { Repair-Hooks; Prune-Discovery; exit }

if (-not (Test-Server)) {
  Prune-Discovery
  if (Test-Path $dist) {
    Start-Process -WindowStyle Hidden -FilePath 'node.exe' -ArgumentList "`"$dist`"" -WorkingDirectory $root
  } else {
    Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList "/c cd /d `"$root`" && npx -y agent-flow-app"
  }
  for ($i = 0; $i -lt 45; $i++) { if (Test-Server) { break }; Start-Sleep -Seconds 1 }
  Start-Sleep -Seconds 2
  Repair-Hooks
}

# janela propria do board (Chrome se houver, senao Edge)
$chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($chrome) { Start-Process $chrome -ArgumentList '--app=http://localhost:3001' }
else { Start-Process 'http://localhost:3001' }

# enquanto a janela do board existir, o server vive; fechou a janela, para o server
# vigia por JANELA (EnumWindows), nao por processo: o Chrome do board e' o mesmo
# processo do Chrome normal do usuario, e MainWindowTitle so mostra a janela em foco —
# quando o foco cai numa janela comum, o watchdog lia o titulo da aba errada ("Mac
# mini…") e matava o server com o board aberto (bug real, 260915)
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class MbWin {
  delegate bool Cb(IntPtr h, IntPtr lp);
  [DllImport("user32.dll")] static extern bool EnumWindows(Cb cb, IntPtr lp);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder sb, int max);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  static bool _achou;
  static bool Proc(IntPtr h, IntPtr lp) {
    if (IsWindowVisible(h)) {
      var sb = new StringBuilder(256);
      GetWindowText(h, sb, 256);
      if (sb.ToString().IndexOf("Agent Flow", StringComparison.OrdinalIgnoreCase) >= 0) _achou = true;
    }
    return true;
  }
  public static bool TemJanela() { _achou = false; EnumWindows(Proc, IntPtr.Zero); return _achou; }
}
'@
Start-Sleep -Seconds 5
while ([MbWin]::TemJanela()) { Start-Sleep -Seconds 3 }
Stop-Board
