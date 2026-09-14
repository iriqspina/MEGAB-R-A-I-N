param(
  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[a-fA-F0-9]{32}$')]
  [string]$ExpectedKeyId,
  [switch]$Replace
)

$ErrorActionPreference = 'Stop'
$credentialDir = Join-Path $env:USERPROFILE '.config\zai'
$credentialFile = Join-Path $credentialDir 'cli-key.dpapi'

$existingCredential = Test-Path -LiteralPath $credentialFile
if ($existingCredential -and -not $Replace) {
  throw "Já existe uma chave armazenada; preservar sem sobrescrever: $credentialFile"
}
if ($existingCredential -and $Replace) {
  $existingAcl = Get-Acl -LiteralPath $credentialFile
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
  if ($existingAcl.Owner -ne $currentIdentity.Name -or $existingAcl.Access.Count -ne 1) {
    throw 'ACL da chave existente é inesperada; não sobrescrever automaticamente.'
  }
}

$plain = $null
try {
  $plain = (Get-Clipboard -Raw).Trim()
  if ($plain -notmatch '^([a-fA-F0-9]{32})\.([^\s]{12,})$') {
    throw 'A área de transferência não contém uma chave Z.ai no formato esperado.'
  }
  if ($Matches[1] -ine $ExpectedKeyId) {
    throw 'O ID da chave copiada não coincide com a chave recém-criada no painel.'
  }

  New-Item -ItemType Directory -Path $credentialDir -Force | Out-Null
  $secure = ConvertTo-SecureString -String $plain -AsPlainText -Force
  $encrypted = ConvertFrom-SecureString -SecureString $secure
  Set-Content -LiteralPath $credentialFile -Value $encrypted -Encoding ascii

  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  if (-not $existingCredential) {
    $acl = New-Object Security.AccessControl.FileSecurity
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity.User, 'FullControl', 'Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $credentialFile -AclObject $acl
  }

  Write-Output "Chave armazenada com DPAPI para $($identity.Name), sem texto puro no arquivo: $credentialFile"
}
finally {
  $plain = $null
  Set-Clipboard -Value ''
}
