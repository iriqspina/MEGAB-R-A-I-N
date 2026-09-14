param(
  [ValidateSet('Flash', 'Full')]
  [string]$Tier = 'Flash',
  [string]$Workspace = (Get-Location).Path,
  [switch]$Check,
  [switch]$AskBeforeChanges,
  [string]$Prompt
)

$ErrorActionPreference = 'Stop'
$profileDir = Join-Path $env:USERPROFILE '.claude-zai'
$credentialFile = Join-Path $env:USERPROFILE '.config\zai\cli-key.dpapi'
$model = if ($Tier -eq 'Flash') { 'glm-5.3-flash[1m]' } else { 'glm-5.3[1m]' }

if (-not (Test-Path -LiteralPath (Join-Path $profileDir 'settings.json'))) {
  throw 'Perfil Claude GLM ausente; execute initialize-profiles.ps1.'
}
if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
  throw "Workspace não encontrado: $Workspace"
}
if ($Check) {
  Write-Output "Claude GLM: modelo=$model; perfil=$profileDir; workspace=$Workspace; chave armazenada=$(Test-Path -LiteralPath $credentialFile)"
  return
}
if (-not (Test-Path -LiteralPath $credentialFile)) {
  throw 'Chave CLI Z.ai ainda não armazenada.'
}

$encrypted = (Get-Content -LiteralPath $credentialFile -Raw).Trim()
$secure = ConvertTo-SecureString -String $encrypted
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$oldConfig = $env:CLAUDE_CONFIG_DIR
$oldToken = $env:ANTHROPIC_AUTH_TOKEN
$oldBase = $env:ANTHROPIC_BASE_URL
try {
  $env:CLAUDE_CONFIG_DIR = $profileDir
  $env:ANTHROPIC_AUTH_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  $env:ANTHROPIC_BASE_URL = 'https://api.z.ai/api/anthropic'
  Push-Location -LiteralPath $Workspace
  try {
    $arguments = @('--model', $model)
    if (-not $AskBeforeChanges) { $arguments += '--dangerously-skip-permissions' }
    if ($Prompt) { $arguments += @('--print', $Prompt) }
    & claude @arguments
  }
  finally { Pop-Location }
}
finally {
  $env:CLAUDE_CONFIG_DIR = $oldConfig
  $env:ANTHROPIC_AUTH_TOKEN = $oldToken
  $env:ANTHROPIC_BASE_URL = $oldBase
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  $encrypted = $null
}
