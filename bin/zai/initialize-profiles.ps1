$ErrorActionPreference = 'Stop'

$claudeDir = Join-Path $env:USERPROFILE '.claude-zai'
$codexDir = Join-Path $env:USERPROFILE '.codex-zai'

$claudeSettings = @'
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5.3-flash[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.3[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.3[1m]",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "API_TIMEOUT_MS": "3000000"
  }
}
'@

$modelCatalog = @'
{
  "models": [
    {
      "slug": "glm-5.3",
      "display_name": "glm-5.3",
      "description": "Z.ai GLM Coding Plan",
      "default_reasoning_level": "max",
      "supported_reasoning_levels": [
        {"effort":"low","description":"Light reasoning"},
        {"effort":"high","description":"Enhanced reasoning"},
        {"effort":"max","description":"Deep reasoning"}
      ],
      "shell_type": "shell_command",
      "visibility": "list",
      "supported_in_api": true,
      "priority": 0,
      "base_instructions": "",
      "supports_reasoning_summaries": true,
      "default_reasoning_summary": "none",
      "support_verbosity": false,
      "apply_patch_tool_type": "freeform",
      "truncation_policy": {"mode":"bytes","limit":10000},
      "context_window": 1048576,
      "max_context_window": 1048576,
      "effective_context_window_percent": 95,
      "supports_parallel_tool_calls": true,
      "experimental_supported_tools": [],
      "input_modalities": ["text"]
    }
  ]
}
'@

$codexConfig = @'
model_provider = "ZAI"
model = "glm-5.3"
model_reasoning_effort = "max"
model_catalog_json = "__MODEL_CATALOG_JSON__"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[model_providers.ZAI]
name = "ZAI Coding Plan"
base_url = "https://api.z.ai/api/v1"
wire_api = "responses"
env_key = "ZAI_API_KEY"
requires_openai_auth = false
'@
$codexConfig = $codexConfig.Replace('__MODEL_CATALOG_JSON__', ((Join-Path $codexDir 'models.json') -replace '\\', '/'))

New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
New-Item -ItemType Directory -Path $codexDir -Force | Out-Null

$files = @(
  @{ Path = (Join-Path $claudeDir 'settings.json'); Content = $claudeSettings },
  @{ Path = (Join-Path $codexDir 'models.json'); Content = $modelCatalog },
  @{ Path = (Join-Path $codexDir 'config.toml'); Content = $codexConfig }
)
foreach ($file in $files) {
  if (Test-Path -LiteralPath $file.Path) {
    throw "Arquivo já existe; preservar sem sobrescrever: $($file.Path)"
  }
  Set-Content -LiteralPath $file.Path -Value $file.Content -Encoding utf8
}

Write-Output 'Perfis Z.ai criados sem chave. Claude e Codex originais não foram alterados.'
