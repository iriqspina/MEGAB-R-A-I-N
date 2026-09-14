param(
  [ValidateSet('Flash', 'Full')]
  [string]$Tier = 'Flash',
  [string]$Workspace = (Get-Location).Path,
  [switch]$Check,
  [string]$Prompt
)

$ErrorActionPreference = 'Stop'
$profileDir = Join-Path $env:USERPROFILE '.opencode-zai'
$configFile = Join-Path $profileDir 'opencode.json'
$credentialFile = Join-Path $env:USERPROFILE '.config\zai\cli-key.dpapi'
$model = if ($Tier -eq 'Flash') { 'zai-coding/glm-5.3-flash' } else { 'zai-coding/glm-5.3' }

if (-not (Test-Path -LiteralPath $configFile)) {
  throw 'Perfil OpenCode GLM ausente; execute initialize-opencode.ps1.'
}
if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
  throw "Workspace não encontrado: $Workspace"
}
if ($Check) {
  Write-Output "OpenCode GLM: modelo=$model; perfil=$profileDir; workspace=$Workspace; chave armazenada=$(Test-Path -LiteralPath $credentialFile)"
  return
}
if (-not (Test-Path -LiteralPath $credentialFile)) {
  throw 'Chave CLI Z.ai ainda não armazenada.'
}

$encrypted = (Get-Content -LiteralPath $credentialFile -Raw).Trim()
$secure = ConvertTo-SecureString -String $encrypted
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$oldConfig = $env:OPENCODE_CONFIG
$oldConfigDir = $env:OPENCODE_CONFIG_DIR
$oldKey = $env:ZAI_API_KEY
try {
  $env:OPENCODE_CONFIG = $configFile
  $env:OPENCODE_CONFIG_DIR = $profileDir
  $env:ZAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  Push-Location -LiteralPath $Workspace
  try {
    if ($Prompt) {
      & opencode run --model $model --auto ("`n" + $Prompt)
    }
    else {
      & opencode --auto
    }
    if ($LASTEXITCODE -ne 0) { throw "OpenCode GLM terminou com código $LASTEXITCODE" }
  }
  finally { Pop-Location }
}
finally {
  $env:OPENCODE_CONFIG = $oldConfig
  $env:OPENCODE_CONFIG_DIR = $oldConfigDir
  $env:ZAI_API_KEY = $oldKey
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  $encrypted = $null
}
