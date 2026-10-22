param([string]$EvidencePath)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
if(-not $EvidencePath){$EvidencePath=Join-Path $taskRoot 'evidence\261021_cotas-agendamento'}
$EvidencePath=[IO.Path]::GetFullPath($EvidencePath)
if(-not $EvidencePath.StartsWith($taskRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Evidence must stay in this project'}
New-Item -ItemType Directory -Path $EvidencePath -Force | Out-Null
$taskName='MegaBrain - Cotas IA - 09h e 21h'
$taskPath='\MegaBrain\'
$zone=Get-TimeZone
if($zone.Id -ne 'E. South America Standard Time'){throw 'Timezone differs from Sao Paulo; schedule not installed'}
$python=Join-Path $taskRoot 'apps\ia-quota-widget\.venv\Scripts\pythonw.exe'
$script=Join-Path $taskRoot 'bin\mb-atualizar-cotas.py'
if(-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $script)){throw 'Collector runtime unavailable'}
$old=Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
if($old){Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName | Set-Content -LiteralPath (Join-Path $EvidencePath 'task-before.xml') -Encoding Unicode}
$action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$script+'"') -WorkingDirectory $taskRoot
$triggers=@((New-ScheduledTaskTrigger -Daily -At '09:00'),(New-ScheduledTaskTrigger -Daily -At '21:00'))
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -MultipleInstances IgnoreNew -Hidden
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$task=New-ScheduledTask -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Description 'Leitura das cotas e resets por API/adaptadores existentes. Sem IA, sem navegador, sem resgatar resets; 09h e21hBRT.'
Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -InputObject $task -Force | Out-Null
Export-ScheduledTask -TaskPath $taskPath -TaskName $taskName | Set-Content -LiteralPath (Join-Path $EvidencePath 'task-installed.xml') -Encoding Unicode
$dataDir=Join-Path $taskRoot 'apps\ia-quota-widget\app\data'
$config=[ordered]@{schema_version=1;kind='windows_task_scheduler';task_name=$taskName;task_path=$taskPath;status='ACTIVE';timezone='America/Sao_Paulo';daily_times=@('09:00','21:00');interval_hours=12;uses_ai=$false;scope=@('codex','claude','zai');installed_at=(Get-Date).ToString('o');limits='PC ligado e sessao Windows disponivel; StartWhenAvailable; navegador historico nao e atualizado por esta rotina.'}
$temp=Join-Path $dataDir 'quota_refresh.json.tmp'
$config | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $temp -Encoding utf8
Move-Item -LiteralPath $temp -Destination (Join-Path $dataDir 'quota_refresh.json') -Force
$config | ConvertTo-Json -Depth 5
