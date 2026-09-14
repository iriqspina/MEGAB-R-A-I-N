param(
  [string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
$pwsh = (Get-Command pwsh.exe -ErrorAction Stop).Source
$menu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Z.ai GLM'
New-Item -ItemType Directory -Path $menu -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell

$entries = @(
  @{ Name = 'Claude (GLM Flash - Z.ai)'; Script = 'start-claude-glm.ps1'; Tier = 'Flash' },
  @{ Name = 'Codex (GLM-5.3 - Z.ai)'; Script = 'start-codex-glm.ps1' },
  @{ Name = 'OpenCode (GLM Flash - Z.ai)'; Script = 'start-opencode-glm.ps1'; Tier = 'Flash' },
  @{ Name = 'OpenCode (GLM-5.3 - Z.ai)'; Script = 'start-opencode-glm.ps1'; Tier = 'Full' }
)

foreach ($entry in $entries) {
  $script = Join-Path $PSScriptRoot $entry.Script
  if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "Launcher ausente: $script"
  }
  $link = Join-Path $menu ($entry.Name + '.lnk')
  $shortcut = $shell.CreateShortcut($link)
  if (Test-Path -LiteralPath $link) {
    if ($shortcut.TargetPath -ne $pwsh -or -not $shortcut.Arguments.Contains($script)) {
      throw "Atalho existente não pertence a este instalador; preservar: $link"
    }
  }
  $shortcut.TargetPath = $pwsh
  $shortcut.Arguments = if ($entry.Tier) {
    '-NoExit -File "{0}" -Workspace "{1}" -Tier {2}' -f $script, $Workspace, $entry.Tier
  }
  else {
    '-NoExit -File "{0}" -Workspace "{1}"' -f $script, $Workspace
  }
  $shortcut.WorkingDirectory = $Workspace
  $shortcut.Description = 'Cliente GLM com perfil Z.ai isolado; chave carregada do DPAPI no processo.'
  $shortcut.Save()
}

Write-Output "Atalhos GLM criados em $menu"
