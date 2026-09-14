param(
  [string]$Workspace = (Get-Location).Path,
  [switch]$Check,
  [string]$Prompt
)

$ErrorActionPreference = 'Stop'
$profileDir = Join-Path $env:USERPROFILE '.codex-zai'
$credentialFile = Join-Path $env:USERPROFILE '.config\zai\cli-key.dpapi'

if (-not (Test-Path -LiteralPath (Join-Path $profileDir 'config.toml'))) {
  throw 'Perfil Codex GLM ausente; execute initialize-profiles.ps1.'
}
if (-not (Test-Path -LiteralPath $Workspace -PathType Container)) {
  throw "Workspace não encontrado: $Workspace"
}
if ($Check) {
  Write-Output "Codex GLM: modelo=glm-5.3; perfil=$profileDir; workspace=$Workspace; chave armazenada=$(Test-Path -LiteralPath $credentialFile)"
  return
}
if (-not (Test-Path -LiteralPath $credentialFile)) {
  throw 'Chave CLI Z.ai ainda não armazenada.'
}

$encrypted = (Get-Content -LiteralPath $credentialFile -Raw).Trim()
$secure = ConvertTo-SecureString -String $encrypted
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$oldHome = $env:CODEX_HOME
$oldKey = $env:ZAI_API_KEY
try {
  $env:CODEX_HOME = $profileDir
  $env:ZAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  Push-Location -LiteralPath $Workspace
  try {
    if ($Prompt) {
      $Prompt | & codex exec --skip-git-repo-check -
    }
    else {
      & codex
    }
    if ($LASTEXITCODE -ne 0) { throw "Codex GLM terminou com código $LASTEXITCODE" }
  }
  finally { Pop-Location }
}
finally {
  $env:CODEX_HOME = $oldHome
  $env:ZAI_API_KEY = $oldKey
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  $encrypted = $null
}
