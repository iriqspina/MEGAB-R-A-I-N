$ErrorActionPreference = 'Stop'
$profileDir = Join-Path $env:USERPROFILE '.opencode-zai'
$configFile = Join-Path $profileDir 'opencode.json'
if (Test-Path -LiteralPath $configFile) {
  throw "Perfil OpenCode GLM já existe; preservar sem sobrescrever: $configFile"
}
New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
$config = @'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "zai-coding/glm-5.3-flash",
  "subagent_depth": 2,
  "permission": "allow",
  "share": "disabled",
  "provider": {
    "zai-coding": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Z.AI Coding Plan",
      "options": {
        "baseURL": "https://api.z.ai/api/coding/paas/v4",
        "apiKey": "{env:ZAI_API_KEY}"
      },
      "models": {
        "glm-5.3-flash": {"name": "GLM-5.3-Flash"},
        "glm-5.3": {"name": "GLM-5.3"}
      }
    }
  }
}
'@
$config | ConvertFrom-Json | Out-Null
Set-Content -LiteralPath $configFile -Value $config -Encoding utf8
Write-Output "Perfil OpenCode GLM criado sem segredo: $configFile"
